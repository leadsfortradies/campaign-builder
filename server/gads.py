"""Google Ads / Keyword Planner access for the step handlers, reusing the
existing scripts/lib code (credentials from env vars in the cloud, yaml locally)."""

import os
import sys

from . import config

sys.path.insert(0, os.path.join(config.REPO_ROOT, "scripts"))

NZ_GEO_ID = "2554"
# Account Keyword Planner runs as (same one the chat workflow used).
CUSTOMER_ID = os.environ.get("GOOGLE_ADS_CUSTOMER_ID", "9952256901")

_client = None


def client():
    global _client
    if _client is None:
        from lib.google_ads_config import load_client
        _client = load_client()
    return _client


def _norm(m):
    return {
        "keyword": m["keyword"],
        "avg_monthly_searches": int(m["avg_monthly_searches"] or 0),
        "competition": m["competition"],
        "low_bid": round(m["low_top_of_page_bid"], 2),
        "high_bid": round(m["high_top_of_page_bid"], 2),
    }


def keyword_ideas(seeds, location_ids, min_searches=10):
    """Idea expansion from seed keywords. The API takes max 20 seeds per call,
    so seeds are chunked and results merged (highest volume wins)."""
    from lib.keyword_planner import generate_keyword_ideas
    merged = {}
    for i in range(0, len(seeds), 20):
        for m in generate_keyword_ideas(client(), CUSTOMER_ID, keywords=seeds[i:i + 20],
                                        location_ids=location_ids,
                                        min_avg_monthly_searches=min_searches):
            row = _norm(m)
            key = row["keyword"].lower()
            if key not in merged or row["avg_monthly_searches"] > merged[key]["avg_monthly_searches"]:
                merged[key] = row
    return list(merged.values())


def historical_metrics(keywords, location_ids):
    """Exact-phrase volume for known keywords (batched)."""
    from lib.keyword_planner import get_keyword_historical_metrics
    out = []
    for i in range(0, len(keywords), 500):
        out += [_norm(m) for m in get_keyword_historical_metrics(
            client(), CUSTOMER_ID, keywords[i:i + 500], location_ids)]
    return out


def resolve_location(name):
    """Best geo target id for a NZ place name, or None."""
    from lib.keyword_planner import resolve_locations
    results = resolve_locations(client(), [name])
    nz = [r for r in results if r["country_code"] == "NZ"]
    return str(nz[0]["id"]) if nz else None
