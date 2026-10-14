import os
import sys

from google.ads.googleads.client import GoogleAdsClient

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_PATH = os.path.join(PROJECT_ROOT, "google-ads.yaml")


def load_client() -> GoogleAdsClient:
    # Cloud: credentials come from environment variables (no yaml on the
    # server). Locally the yaml file is used as before.
    if os.environ.get("GOOGLE_ADS_REFRESH_TOKEN"):
        cfg = {
            "client_id": os.environ["GOOGLE_ADS_CLIENT_ID"],
            "client_secret": os.environ["GOOGLE_ADS_CLIENT_SECRET"],
            "refresh_token": os.environ["GOOGLE_ADS_REFRESH_TOKEN"],
            "use_proto_plus": True,
        }
        if os.environ.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID"):
            cfg["login_customer_id"] = os.environ["GOOGLE_ADS_LOGIN_CUSTOMER_ID"]
        if os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN"):
            cfg["developer_token"] = os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"]
        return GoogleAdsClient.load_from_dict(cfg)
    if not os.path.exists(CONFIG_PATH):
        sys.exit(
            f"Missing {CONFIG_PATH}\n"
            "Copy google-ads.yaml.example to google-ads.yaml and fill in your "
            "credentials first (see README.md)."
        )
    return GoogleAdsClient.load_from_storage(CONFIG_PATH)
