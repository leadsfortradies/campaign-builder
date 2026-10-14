import os

import yaml
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_PATH = os.path.join(PROJECT_ROOT, "gtm-credentials.yaml")

SCOPES = [
    "https://www.googleapis.com/auth/tagmanager.edit.containers",
    "https://www.googleapis.com/auth/tagmanager.publish",
]


def load_client():
    if not os.path.exists(CONFIG_PATH):
        raise SystemExit(
            f"Missing {CONFIG_PATH}\n"
            "Run scripts/generate_gtm_refresh_token.py first, then copy "
            "gtm-credentials.yaml.example to gtm-credentials.yaml and fill it in."
        )
    with open(CONFIG_PATH) as f:
        cfg = yaml.safe_load(f)

    creds = Credentials(
        token=None,
        refresh_token=cfg["refresh_token"],
        client_id=cfg["client_id"],
        client_secret=cfg["client_secret"],
        token_uri="https://oauth2.googleapis.com/token",
        scopes=SCOPES,
    )
    return build("tagmanager", "v2", credentials=creds)
