"""Campaign Builder backend: serves the web app, takes approvals, runs jobs.

Run locally:  ALLOW_NO_AUTH=1 venv/bin/python -m uvicorn server.app:app --port 8787
"""

import json
import os
import shutil
import time
from contextlib import asynccontextmanager
from urllib.parse import parse_qs, urlparse

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse

from . import auth, config, db, jobs, projects_store
from .notify import notify

FAILED_LOGINS = {}  # ip -> (count, window_start)


def _seed_volume():
    """First boot on a fresh volume: copy projects.json + data/ out of the
    deployed repo so the app starts with the existing projects."""
    if config.WEB_DATA_ROOT == config.WEB_CODE_ROOT:
        return
    os.makedirs(config.WEB_DATA_ROOT, exist_ok=True)
    src_pj = os.path.join(config.WEB_CODE_ROOT, "projects.json")
    if not os.path.exists(config.PROJECTS_PATH) and os.path.exists(src_pj):
        shutil.copy(src_pj, config.PROJECTS_PATH)
    src_data = os.path.join(config.WEB_CODE_ROOT, "data")
    dst_data = os.path.join(config.WEB_DATA_ROOT, "data")
    if os.path.isdir(src_data) and not os.path.isdir(dst_data):
        shutil.copytree(src_data, dst_data)


@asynccontextmanager
async def lifespan(app):
    if not config.APP_PASSWORD and not config.ALLOW_NO_AUTH:
        raise RuntimeError("Set APP_PASSWORD (or ALLOW_NO_AUTH=1 for local dev only).")
    os.makedirs(config.APPROVALS_DIR, exist_ok=True)
    _seed_volume()
    db.conn()
    stop = jobs.start()
    yield
    stop.set()


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)


# ---------- auth ----------

OPEN_PATHS = {"/login", "/healthz"}


def _authed(request):
    if config.ALLOW_NO_AUTH and not config.APP_PASSWORD:
        return True
    return auth.valid_token(request.cookies.get(auth.COOKIE, ""))


@app.middleware("http")
async def gate(request: Request, call_next):
    if request.method == "POST" and request.url.path != "/login":
        # CSRF belt-and-braces on top of SameSite=Lax: same-origin only.
        origin = request.headers.get("origin")
        if origin and urlparse(origin).netloc != request.headers.get("host"):
            return JSONResponse({"error": "bad origin"}, status_code=403)
    if request.url.path not in OPEN_PATHS and not _authed(request):
        if request.url.path.startswith("/api/") or request.method != "GET":
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        return RedirectResponse("/login")
    resp = await call_next(request)
    resp.headers["Cache-Control"] = "no-store"
    return resp


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/login", response_class=HTMLResponse)
def login_page():
    return auth.LOGIN_PAGE.replace("{error}", "")


@app.post("/login")
async def login(request: Request):
    ip = request.client.host if request.client else "?"
    count, start = FAILED_LOGINS.get(ip, (0, time.time()))
    if time.time() - start > 900:
        count, start = 0, time.time()
    if count >= 8:
        return HTMLResponse(auth.LOGIN_PAGE.replace("{error}", '<p class="err">Too many attempts. Try again later.</p>'), status_code=429)
    form = parse_qs((await request.body()).decode())
    if auth.check_password(form.get("password", [""])[0]):
        FAILED_LOGINS.pop(ip, None)
        resp = RedirectResponse("/", status_code=303)
        resp.set_cookie(
            auth.COOKIE, auth.make_token(), max_age=config.SESSION_DAYS * 86400,
            httponly=True, samesite="lax",
            secure=request.headers.get("x-forwarded-proto", request.url.scheme) == "https",
        )
        return resp
    FAILED_LOGINS[ip] = (count + 1, start)
    time.sleep(1)
    return HTMLResponse(auth.LOGIN_PAGE.replace("{error}", '<p class="err">Wrong password.</p>'), status_code=401)


@app.post("/logout")
def logout():
    resp = RedirectResponse("/login", status_code=303)
    resp.delete_cookie(auth.COOKIE)
    return resp


# ---------- approvals / changes ----------

@app.post("/approve")
async def approve(request: Request):
    try:
        payload = await request.json()
    except ValueError:
        raise HTTPException(400, "Invalid JSON")
    project_id = str(payload.get("project_id", ""))
    step = str(payload.get("step", ""))
    if not project_id or not step:
        raise HTTPException(400, "project_id and step required")
    if not any(p["id"] == project_id for p in projects_store.load()):
        raise HTTPException(404, "Unknown project")

    ts = int(time.time())
    # Same file layout the chat workflow already reads, so both paths work.
    fname = f"{project_id}__{step}__{ts}.json"
    with open(os.path.join(config.APPROVALS_DIR, fname), "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    db.execute("INSERT INTO approvals (project_id, step, payload, created_at) VALUES (?,?,?,?)",
               (project_id, step, json.dumps(payload), time.time()))
    fields = {"status": "approved"}
    if payload.get("total_kept") is not None:
        fields["approved_count"] = payload["total_kept"]
    projects_store.update_step(project_id, step, **fields)
    db.log_event("approved", project_id, step, f"{payload.get('total_kept')} kept")

    nxt = projects_store.next_step(step)
    job_id = db.add_job(project_id, nxt, "run_step", {"after_approval_of": step}) if nxt else None
    return {"ok": True, "next_step": nxt, "job_id": job_id}


@app.post("/api/request-changes")
async def request_changes(request: Request):
    body = await request.json()
    project_id, step, note = body.get("project_id"), body.get("step"), (body.get("note") or "").strip()
    if not (project_id and step and note):
        raise HTTPException(400, "project_id, step and note required")
    db.execute("INSERT INTO change_requests (project_id, step, note, created_at) VALUES (?,?,?,?)",
               (project_id, step, note, time.time()))
    projects_store.update_step(project_id, step, status="changes_requested")
    db.log_event("changes_requested", project_id, step, note)
    job_id = db.add_job(project_id, step, "revise_step", {"note": note})
    return {"ok": True, "job_id": job_id}


# ---------- read API ----------

@app.get("/api/jobs")
def list_jobs(project_id: str = "", limit: int = 50):
    if project_id:
        rows = db.query("SELECT id,project_id,step,kind,status,model,error,created_at,finished_at FROM jobs "
                        "WHERE project_id=? ORDER BY id DESC LIMIT ?", (project_id, limit))
    else:
        rows = db.query("SELECT id,project_id,step,kind,status,model,error,created_at,finished_at FROM jobs "
                        "ORDER BY id DESC LIMIT ?", (limit,))
    return rows


@app.get("/api/jobs/{job_id}")
def get_job(job_id: int):
    rows = db.query("SELECT * FROM jobs WHERE id=?", (job_id,))
    if not rows:
        raise HTTPException(404)
    return rows[0]


@app.get("/api/settings")
def get_settings():
    return {"model": db.current_model(), "models": config.MODELS}


@app.post("/api/settings")
async def set_settings(request: Request):
    body = await request.json()
    model = body.get("model")
    if model not in {m["id"] for m in config.MODELS}:
        raise HTTPException(400, "Unknown model")
    db.set_setting("model", model)
    db.log_event("model_changed", detail=model)
    return {"ok": True, "model": model}


@app.post("/api/test-notify")
def test_notify():
    if not config.NTFY_TOPIC:
        raise HTTPException(400, "NTFY_TOPIC isn't set on the server")
    notify("Campaign Builder", "Test notification - phone alerts are working.", "/")
    return {"ok": True}


@app.post("/api/selftest")
def selftest():
    return {"job_id": db.add_job("_selftest", "step0", "selftest")}


# ---------- static ----------

def _safe_join(root, rel):
    full = os.path.realpath(os.path.join(root, rel))
    if full != os.path.realpath(root) and not full.startswith(os.path.realpath(root) + os.sep):
        raise HTTPException(404)
    return full


@app.get("/{path:path}")
def static(path: str):
    path = path or "index.html"
    # Mutable project data comes from the data root, everything else from the code.
    if path == "projects.json" or path.startswith("data/"):
        root = config.WEB_DATA_ROOT
    elif path.startswith("approvals"):
        raise HTTPException(404)
    else:
        root = config.WEB_CODE_ROOT
    full = _safe_join(root, path)
    if not os.path.isfile(full):
        raise HTTPException(404)
    return FileResponse(full)
