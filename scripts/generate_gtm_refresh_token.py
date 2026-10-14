"""
One-time setup script: logs you into Google in a browser window and produces
a refresh token for the Tag Manager API (separate from the Google Ads one -
refresh tokens are scoped to what you approved).

Run it once:
    venv/bin/python scripts/generate_gtm_refresh_token.py

It reuses the same OAuth client (client_secret*.json) already in this
project's root folder. It will open your browser, ask you to log in with
the Google account that has edit access to the GTM account/container, and
ask you to approve access. When you approve, it prints a refresh token here
in the terminal - paste that into gtm-credentials.yaml (copy from
gtm-credentials.yaml.example) under refresh_token.
"""

import glob
import os

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/tagmanager.edit.containers",
    "https://www.googleapis.com/auth/tagmanager.publish",
]

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def find_client_secret_file():
    matches = glob.glob(os.path.join(PROJECT_ROOT, "client_secret*.json"))
    if not matches:
        raise FileNotFoundError(
            "Couldn't find a client_secret*.json file in the project folder. "
            "It should already be there from the Google Ads setup."
        )
    return matches[0]


def main():
    client_secret_file = find_client_secret_file()
    print(f"Using OAuth client: {os.path.basename(client_secret_file)}\n")

    flow = InstalledAppFlow.from_client_secrets_file(client_secret_file, scopes=SCOPES)
    credentials = flow.run_local_server(
        port=0,
        access_type="offline",
        prompt="consent",
    )

    print("\nSuccess! Your Tag Manager refresh token is:\n")
    print(credentials.refresh_token)
    print(
        "\nCopy that value into gtm-credentials.yaml under refresh_token "
        "(create it from gtm-credentials.yaml.example if you haven't already)."
    )


if __name__ == "__main__":
    main()
