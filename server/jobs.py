"""Background job runner.

A job is one unit of work on a project step. The runner thread picks up
queued jobs one at a time and dispatches to a handler registered for
(kind). A handler is a function ``handler(ctx) -> None`` where ctx offers:

    ctx.job            the job row (dict)
    ctx.payload        parsed job payload
    ctx.model          model id to use for every Claude call in this job
    ctx.log(msg)       append a line to the job's log
    ctx.set_step(**f)  merge fields into projects.json for this step
    ctx.need_approval(msg)   mark the step ready for review + notify

Handlers for the real campaign steps are registered in server/steps/ as
they're built. A run_step job for a step with no handler is marked
"blocked" rather than failed, so the UI can show "not automated yet".
"""

import json
import os
import threading
import time
import traceback

from . import db, projects_store
from .notify import notify

HANDLERS = {}


class Blocked(Exception):
    """Raise from a handler when it can't continue without the user (e.g.
    missing business info). The job is marked blocked and the user notified."""


# Hard ceiling on Claude tokens per project, so a bug can't drain credit.
PROJECT_TOKEN_CAP = int(os.environ.get("PROJECT_TOKEN_CAP", "4000000"))
STEP_HANDLERS = {}




def register(kind):
    def deco(fn):
        HANDLERS[kind] = fn
        return fn
    return deco


def register_step(step):
    def deco(fn):
        STEP_HANDLERS[step] = fn
        return fn
    return deco


class Ctx:
    def __init__(self, job):
        self.job = job
        self.payload = json.loads(job["payload"] or "{}")
        self.project_id = job["project_id"]
        self.step = job["step"]
        # Model is read when the job starts, so a switch in the UI applies
        # to the next job, never mid-job. Handlers must use ctx.model for
        # every Claude call.
        self.model = db.current_model()
        self._lines = []

    def log(self, msg):
        self._lines.append(f"[{time.strftime('%H:%M:%S')}] {msg}")
        print(f"[job {self.job['id']} {self.project_id}/{self.step}] {msg}", flush=True)
        db.execute("UPDATE jobs SET log=? WHERE id=?", ("\n".join(self._lines), self.job["id"]))

    def add_usage(self, tin, tout):
        db.execute("UPDATE jobs SET input_tokens=input_tokens+?, output_tokens=output_tokens+? WHERE id=?",
                   (tin, tout, self.job["id"]))
        if self.project_id and not self.project_id.startswith("_"):
            db.record_usage(self.project_id, self.step, self.model, tin, tout, self.job["id"])
        used = db.query("SELECT COALESCE(SUM(input_tokens+output_tokens),0) AS t FROM jobs WHERE project_id=?",
                        (self.project_id,))[0]["t"]
        if used > PROJECT_TOKEN_CAP:
            raise Blocked(f"This campaign has used {used:,} Claude tokens, over the {PROJECT_TOKEN_CAP:,} cap. "
                          "Raise PROJECT_TOKEN_CAP in Railway to continue.")

    def queue_next(self, step):
        db.add_job(self.project_id, step, "run_step", {"after": self.step})

    def set_step(self, **fields):
        return projects_store.update_step(self.project_id, self.step, **fields)

    def need_approval(self, msg=""):
        self.set_step(status="needs_approval")
        notify(f"Ready for review: {self.project_id}", msg or f"{self.step} is ready for your approval.",
               f"/project.html?id={self.project_id}&step={self.step}")
        db.log_event("needs_approval", self.project_id, self.step, msg)


def _run(job):
    ctx = Ctx(job)
    db.execute("UPDATE jobs SET status='running', started_at=?, model=? WHERE id=?",
               (time.time(), ctx.model, job["id"]))
    try:
        if job["kind"] in HANDLERS:
            handler = HANDLERS[job["kind"]]
        elif job["kind"] in ("run_step", "revise_step") and job["step"] in STEP_HANDLERS:
            handler = STEP_HANDLERS[job["step"]]
        else:
            msg = f"Automation for {job['step']} isn't built yet - continue it in chat for now."
            db.execute("UPDATE jobs SET status='blocked', error=?, finished_at=? WHERE id=?",
                       (msg, time.time(), job["id"]))
            db.log_event("blocked", job["project_id"], job["step"], msg)
            notify(f"Needs you: {job['project_id']}", msg, f"/project.html?id={job['project_id']}")
            return
        if job["kind"] != "selftest":
            ctx.set_step(status="running")
        handler(ctx)
        db.execute("UPDATE jobs SET status='done', finished_at=? WHERE id=?", (time.time(), job["id"]))
    except Blocked as exc:
        db.execute("UPDATE jobs SET status='blocked', error=?, finished_at=? WHERE id=?",
                   (str(exc), time.time(), job["id"]))
        ctx.set_step(status="blocked")
        db.log_event("blocked", job["project_id"], job["step"], str(exc))
        notify(f"Needs you: {job['project_id']}", str(exc)[:300], f"/project.html?id={job['project_id']}")
    except BaseException as exc:  # noqa: BLE001 - incl. SystemExit from a library; must never kill the runner
        tb = traceback.format_exc()
        if job["kind"] != "selftest":
            ctx.set_step(status="failed")
        db.execute("UPDATE jobs SET status='failed', error=?, finished_at=? WHERE id=?",
                   (f"{exc}\n{tb}", time.time(), job["id"]))
        db.log_event("failed", job["project_id"], job["step"], str(exc))
        notify(f"Failed: {job['project_id']} {job['step']}", str(exc)[:200],
               f"/project.html?id={job['project_id']}&step={job['step']}")


def _loop(stop):
    # Any job left "running" from a crashed/restarted process goes back in the queue.
    db.execute("UPDATE jobs SET status='queued' WHERE status='running'")
    while not stop.is_set():
        rows = db.query("SELECT * FROM jobs WHERE status='queued' ORDER BY id LIMIT 1")
        if rows:
            try:
                _run(rows[0])
            except BaseException as exc:  # noqa: BLE001 - keep the runner alive no matter what
                print(f"[jobs] runner error on job {rows[0]['id']}: {exc!r}", flush=True)
                try:
                    db.execute("UPDATE jobs SET status='failed', error=?, finished_at=? WHERE id=?",
                               (f"runner error: {exc!r}", time.time(), rows[0]["id"]))
                except Exception:  # noqa: BLE001
                    time.sleep(2)
        else:
            stop.wait(2)


def start():
    stop = threading.Event()
    t = threading.Thread(target=_loop, args=(stop,), daemon=True, name="job-runner")
    t.start()
    return stop


@register("selftest")
def _selftest(ctx):
    """Exercises the runner end to end without touching any real step."""
    ctx.log("selftest started")
    time.sleep(1)
    ctx.log("selftest finished")
