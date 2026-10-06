import os
import sys

from google.ads.googleads.client import GoogleAdsClient

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_PATH = os.path.join(PROJECT_ROOT, "google-ads.yaml")


def load_client() -> GoogleAdsClient:
    if not os.path.exists(CONFIG_PATH):
        sys.exit(
            f"Missing {CONFIG_PATH}\n"
            "Copy google-ads.yaml.example to google-ads.yaml and fill in your "
            "credentials first (see README.md)."
        )
    return GoogleAdsClient.load_from_storage(CONFIG_PATH)
