"""Pushes a built landing page site to a new private GitHub repo (named after the
business) and links that repo to a Netlify site, which deploys from it. There is
no CLI/direct deploy: every deploy comes from the repo. Tokens come from Railway variables:
    GITHUB_TOKEN        fine-grained token (Administration + Contents: read/write)
    NETLIFY_AUTH_TOKEN  Netlify personal access token
Optional: GITHUB_OWNER (default leadsfortradies), NETLIFY_ACCOUNT_SLUG,
NETLIFY_GITHUB_INSTALLATION_ID (found from existing Netlify sites if unset)."""

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


def repo_name_for(business_name):
    """'HS Build' -> 'hsbuild'."""
    return re.sub(r"[^a-z0-9]+", "", (business_name or "").lower())[:60] or "lftsite"


def _repo_exists(token, name):
    r = _api("GET", f"https://api.github.com/repos/{OWNER}/{name}", token, ok_codes=(404,))
    return r.get("_status") != 404


def push_repo(site_dir, repo_name, message, reuse=False):
    """Create <OWNER>/<repo_name> as a private repo and push site_dir to main.
    reuse=True (a rebuild of this project) pushes to the existing repo; otherwise a taken
    name gets a numeric suffix so another client's repo is never overwritten.
    Returns (repo_url, repo_path)."""
    token = os.environ["GITHUB_TOKEN"]
    name = repo_name
    if not reuse:
        n = 2
        while _repo_exists(token, name):
            name = f"{repo_name}{n}"
            n += 1
    made = _api("POST", f"https://api.github.com/orgs/{OWNER}/repos", token,
                {"name": name, "private": True, "auto_init": False}, ok_codes=(404, 422))
    if made.get("_status") == 404:  # owner is a personal account, not an org
        made = _api("POST", "https://api.github.com/user/repos", token,
                    {"name": name, "private": True, "auto_init": False}, ok_codes=(422,))
    url = f"https://x-access-token:{token}@github.com/{OWNER}/{name}.git"
    env = {**os.environ, "GIT_AUTHOR_NAME": "LFT Campaign Builder", "GIT_AUTHOR_EMAIL": "builder@leadsfortradies.co.nz",
           "GIT_COMMITTER_NAME": "LFT Campaign Builder", "GIT_COMMITTER_EMAIL": "builder@leadsfortradies.co.nz"}
    if not os.path.isdir(os.path.join(site_dir, ".git")):
        _run(["git", "init", "-q", "-b", "main"], cwd=site_dir, env=env)
    _run(["git", "add", "-A"], cwd=site_dir, env=env)
    subprocess.run(["git", "commit", "-q", "-m", message], cwd=site_dir, env=env, capture_output=True)
    _run(["git", "push", "-q", "--force", url, "main"], cwd=site_dir, env=env, secret=token)
    return f"https://github.com/{OWNER}/{name}", f"{OWNER}/{name}"


def _slug(name):
    return re.sub(r"[^a-z0-9-]+", "-", name.lower()).strip("-")[:50] or "lft-site"


def ensure_netlify_site(name, existing_id=None):
    """Returns {id, name, url}. Reuses existing_id on a rebuild."""
    token = os.environ["NETLIFY_AUTH_TOKEN"]
    if existing_id:
        s = _api("GET", f"https://api.netlify.com/api/v1/sites/{existing_id}", token)
        # Netlify reports the custom domain as the site's url once one is attached; links must stay on the netlify.app host.
        return {"id": s["id"], "name": s["name"], "url": f"https://{s['name']}.netlify.app"}
    acct = os.environ.get("NETLIFY_ACCOUNT_SLUG")
    base = f"https://api.netlify.com/api/v1/{acct}/sites" if acct else "https://api.netlify.com/api/v1/sites"
    for suffix in ("", "-lp", "-lp2", "-lp3"):
        r = _api("POST", base, token, {"name": _slug(name) + suffix}, ok_codes=(422, 409))
        if r.get("id"):
            return {"id": r["id"], "name": r["name"], "url": f"https://{r['name']}.netlify.app"}
    raise PublishError("Couldn't find a free Netlify site name.")


def _installation_id(token):
    """Netlify's GitHub app installation id: env var, else copied from an existing linked site."""
    env_id = os.environ.get("NETLIFY_GITHUB_INSTALLATION_ID")
    if env_id:
        return int(env_id)
    sites = _api("GET", "https://api.netlify.com/api/v1/sites?filter=all&per_page=100", token)
    for s in sites if isinstance(sites, list) else []:
        iid = (s.get("build_settings") or {}).get("installation_id")
        if iid and (s.get("build_settings") or {}).get("provider") == "github":
            return int(iid)
    raise PublishError("Couldn't find Netlify's GitHub connection. Link any one site to GitHub in Netlify once "
                       "(or set NETLIFY_GITHUB_INSTALLATION_ID), then press Retry.")


def link_repo(site_id, repo_path):
    """Link the GitHub repo to the Netlify site (deploy on every push to main) and start the first build."""
    token = os.environ["NETLIFY_AUTH_TOKEN"]
    cur = _api("GET", f"https://api.netlify.com/api/v1/sites/{site_id}", token)
    bs = cur.get("build_settings") or {}
    if not (bs.get("provider") == "github" and bs.get("repo_path") == repo_path and bs.get("repo_branch") == "main"):
        _api("PATCH", f"https://api.netlify.com/api/v1/sites/{site_id}", token, {"repo": {
            "provider": "github", "repo_path": repo_path, "repo_branch": "main", "dir": ".", "cmd": "",
            "private": True, "installation_id": _installation_id(token)}})
    # Linking doesn't always build; start one so the site is live without waiting for a push.
    return _api("POST", f"https://api.netlify.com/api/v1/sites/{site_id}/builds", token, {})


def set_custom_domain(site_id, domain):
    token = os.environ["NETLIFY_AUTH_TOKEN"]
    _api("PATCH", f"https://api.netlify.com/api/v1/sites/{site_id}", token, {"custom_domain": domain})
