"""
One-time setup script: logs you into Google in a browser window and produces
a refresh token for the Google Ads API.

Run it once:
    venv/bin/python scripts/generate_refresh_token.py

It will open your browser, ask you to log in with the Google account that
has access to your Google Ads manager/account, and ask you to approve
access. When you approve, it prints a refresh token here in the terminal -
paste that into google-ads.yaml under refresh_token.
"""

import glob
import os

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/adwords"]

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def find_client_secret_file():
    matches = glob.glob(os.path.join(PROJECT_ROOT, "client_secret*.json"))
    if not matches:
        raise FileNotFoundError(
            "Couldn't find a client_secret*.json file in the project folder. "
            "Download it from Google Cloud Console > APIs & Services > "
            "Credentials > your OAuth 2.0 Client ID (Desktop app), and drop "
            "it in this project's root folder."
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

    print("\nSuccess! Your refresh token is:\n")
    print(credentials.refresh_token)
    print(
        "\nCopy that value into google-ads.yaml under refresh_token "
        "(create google-ads.yaml from google-ads.yaml.example if you "
        "haven't already)."
    )


if __name__ == "__main__":
    main()
