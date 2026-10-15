"""Pushes a built landing page site to a new GitHub repo and deploys it to a
new Netlify site. Tokens come from Railway variables:
    GITHUB_TOKEN        fine-grained token (Administration + Contents: read/write)
    NETLIFY_AUTH_TOKEN  Netlify personal access token
Optional: GITHUB_OWNER (default leadsfortradies), NETLIFY_ACCOUNT_SLUG."""

import json
import os
import re
import subprocess
import urllib.error
import urllib.request

OWNER = os.environ.get("GITHUB_OWNER", "leadsfortradies")
TEMPLATE_REPO = os.environ.get("LP_TEMPLATE_REPO", "leadsfortradies/site-template")


class PublishError(RuntimeError):
    pass


def missing_tokens():
    return [v for v in ("GITHUB_TOKEN", "NETLIFY_AUTH_TOKEN") if not os.environ.get(v)]


def _run(cmd, cwd=None, env=None, secret=""):
    r = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        out = (r.stdout + r.stderr).strip()
        raise PublishError(out.replace(secret, "***")[-1500:] if secret else out[-1500:])
    return r.stdout


def _api(method, url, token, body=None, ok_codes=()):
    req = urllib.request.Request(url, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json",
                                          "Accept": "application/json", "User-Agent": "lft-campaign-builder"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        if exc.code in ok_codes:
            return {"_status": exc.code}
        raise PublishError(f"{method} {url} -> {exc.code}: {exc.read().decode()[:400]}") from None


def clone_template(dest):
    token = os.environ.get("GITHUB_TOKEN", "")
    url = f"https://x-access-token:{token}@github.com/{TEMPLATE_REPO}.git" if token else f"https://github.com/{TEMPLATE_REPO}.git"
    _run(["git", "clone", "--depth", "1", "-q", url, dest], secret=token)


def push_repo(site_dir, repo_name, message):
    """Create (or reuse) <OWNER>/<repo_name> as a private repo and push site_dir to main."""
    token = os.environ["GITHUB_TOKEN"]
    made = _api("POST", f"https://api.github.com/orgs/{OWNER}/repos", token,
                {"name": repo_name, "private": True, "auto_init": False}, ok_codes=(404, 422))
    if made.get("_status") == 404:  # owner is a personal account, not an org
        made = _api("POST", "https://api.github.com/user/repos", token,
                    {"name": repo_name, "private": True, "auto_init": False}, ok_codes=(422,))
    # 422 = already exists (a rebuild); reuse it.
    url = f"https://x-access-token:{token}@github.com/{OWNER}/{repo_name}.git"
    env = {**os.environ, "GIT_AUTHOR_NAME": "LFT Campaign Builder", "GIT_AUTHOR_EMAIL": "builder@leadsfortradies.co.nz",
           "GIT_COMMITTER_NAME": "LFT Campaign Builder", "GIT_COMMITTER_EMAIL": "builder@leadsfortradies.co.nz"}
    if not os.path.isdir(os.path.join(site_dir, ".git")):
        _run(["git", "init", "-q", "-b", "main"], cwd=site_dir, env=env)
    _run(["git", "add", "-A"], cwd=site_dir, env=env)
    subprocess.run(["git", "commit", "-q", "-m", message], cwd=site_dir, env=env, capture_output=True)
    _run(["git", "push", "-q", "--force", url, "main"], cwd=site_dir, env=env, secret=token)
    return f"https://github.com/{OWNER}/{repo_name}"


def _slug(name):
    return re.sub(r"[^a-z0-9-]+", "-", name.lower()).strip("-")[:50] or "lft-site"


def ensure_netlify_site(name, existing_id=None):
    """Returns {id, name, url}. Reuses existing_id on a rebuild."""
    token = os.environ["NETLIFY_AUTH_TOKEN"]
    if existing_id:
        s = _api("GET", f"https://api.netlify.com/api/v1/sites/{existing_id}", token)
        return {"id": s["id"], "name": s["name"], "url": s.get("ssl_url") or s.get("url")}
    acct = os.environ.get("NETLIFY_ACCOUNT_SLUG")
    base = f"https://api.netlify.com/api/v1/{acct}/sites" if acct else "https://api.netlify.com/api/v1/sites"
    for suffix in ("", "-lp", "-lp2", "-lp3"):
        r = _api("POST", base, token, {"name": _slug(name) + suffix}, ok_codes=(422, 409))
        if r.get("id"):
            return {"id": r["id"], "name": r["name"], "url": r.get("ssl_url") or r.get("url")}
    raise PublishError("Couldn't find a free Netlify site name.")


def deploy(site_dir, site_id):
    token = os.environ["NETLIFY_AUTH_TOKEN"]
    env = {**os.environ, "NETLIFY_AUTH_TOKEN": token, "NETLIFY_SITE_ID": site_id}
    out = _run(["netlify", "deploy", "--prod", "--dir", ".", "--functions", "netlify/functions",
                "--site", site_id, "--json"], cwd=site_dir, env=env, secret=token)
    try:
        return json.loads(out[out.index("{"):])
    except Exception:  # noqa: BLE001
        return {}


def set_custom_domain(site_id, domain):
    token = os.environ["NETLIFY_AUTH_TOKEN"]
    _api("PATCH", f"https://api.netlify.com/api/v1/sites/{site_id}", token, {"custom_domain": domain})
