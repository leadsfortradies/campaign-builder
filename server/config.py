"""Runtime configuration, all from environment variables.

Local dev defaults keep everything inside the repo so the existing web/
files keep working. On Railway, STATE_DIR and WEB_DATA_ROOT both point at
the mounted volume so project data survives redeploys.
"""

import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Front-end code (html/js/css) - always served from the deployed repo.
WEB_CODE_ROOT = os.path.join(REPO_ROOT, "web")

# Mutable project data: projects.json + data/<project>/... Defaults to the
# repo's web/ so local runs see exactly what the chat workflow sees.
WEB_DATA_ROOT = os.environ.get("WEB_DATA_ROOT", WEB_CODE_ROOT)

# SQLite db, approval records, logs.
STATE_DIR = os.environ.get("STATE_DIR", os.path.join(REPO_ROOT, ".state"))

PROJECTS_PATH = os.path.join(WEB_DATA_ROOT, "projects.json")
APPROVALS_DIR = os.path.join(STATE_DIR, "approvals")
DB_PATH = os.path.join(STATE_DIR, "app.db")

# Auth. APP_PASSWORD is required unless ALLOW_NO_AUTH=1 (local dev only).
APP_PASSWORD = os.environ.get("APP_PASSWORD", "")
SESSION_SECRET = os.environ.get("SESSION_SECRET", "")
ALLOW_NO_AUTH = os.environ.get("ALLOW_NO_AUTH") == "1"
SESSION_DAYS = 30

# Phone notifications via ntfy (https://ntfy.sh). The topic acts as a
# secret, so use a long random string. Unset = notifications disabled.
NTFY_SERVER = os.environ.get("NTFY_SERVER", "https://ntfy.sh")
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "")
# Public URL of the app, used to build the link inside notifications.
PUBLIC_URL = os.environ.get("PUBLIC_URL", "").rstrip("/")

# Models the app can use for its Claude calls. The selected one is stored in
# the db (settings table) and changed from the web app header.
MODELS = [
    {"id": "claude-fable-5-1", "label": "Fable 5.1", "note": "Most capable"},
    {"id": "claude-opus-5-5", "label": "Opus 5.5", "note": "Very capable"},
    {"id": "claude-sonnet-5-5", "label": "Sonnet 5.5", "note": "Balanced (default)"},
    {"id": "claude-haiku-5-5", "label": "Haiku 5.5", "note": "Fastest / cheapest"},
]
DEFAULT_MODEL = os.environ.get("DEFAULT_MODEL", "claude-sonnet-5-5")


# Claude API list prices in US$ per million tokens, used only for the cost
# tracker (estimates; Anthropic's invoice is the source of truth). Override or
# extend with MODEL_PRICES_JSON in Railway, e.g.
#   {"claude-sonnet-5-5": {"input": 3, "output": 15}}
MODEL_PRICES = {
    "claude-fable-5-1": {"input": 15.0, "output": 75.0},
    "claude-opus-5-5": {"input": 5.0, "output": 25.0},
    "claude-sonnet-5-5": {"input": 3.0, "output": 15.0},
    "claude-haiku-5-5": {"input": 1.0, "output": 5.0},
}
try:
    import json as _json
    MODEL_PRICES.update(_json.loads(os.environ.get("MODEL_PRICES_JSON", "{}")))
except ValueError:
    pass
