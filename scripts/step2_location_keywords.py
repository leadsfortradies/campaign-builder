"""
Step 2: Location-Based Keywords (see PROCESS.md).

Takes the top generic keyword(s) per service and a set of specific
locations, builds "<term> <location>" phrases, and pulls real search volume
for each exact phrase via GenerateKeywordHistoricalMetrics (not idea
expansion - we already know the phrases we want).

Edit BASE_TERMS and LOCATIONS below per campaign, or import
run_location_research() from another script.

Usage:
    venv/bin/python scripts/step2_location_keywords.py --customer-id 9952256901 \
        --out output/test_deck_fence_auckland/step2_location_keywords.csv
"""

import argparse
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from google.ads.googleads.errors import GoogleAdsException
from lib.google_ads_config import load_client
from lib.keyword_planner import get_keyword_historical_metrics

BASE_TERMS = [
    "deck builder",
    "deck builders",
    "deck contractors",
    "deck installation",
    "fence company",
    "fence builder",
    "fencing contractors",
]

# name -> geo target constant id (resolved via scripts/resolve_location.py)
LOCATIONS = {
    "albany": "9122100",
    "takapuna": "9121859",
    "browns bay": "9121970",
    "henderson": "9121884",
    "new lynn": "9122048",
    "te atatu": "9122058",
    "auckland cbd": "9122070",
    "mount eden": "9121922",
    "ponsonby": "9118968",
    "botany": "9118957",
    "howick": "9121989",
    "pakuranga": "9121918",
    "manukau": "9121960",
    "papakura": "9051268",
    "pukekohe": "1011049",
    "manurewa": "9121942",
}


def run_location_research(client, customer_id, base_terms, locations, language_id="1000"):
    results = []
    for location_name, geo_id in locations.items():
        phrases = [f"{term} {location_name}" for term in base_terms]
        metrics = get_keyword_historical_metrics(
            client, customer_id, phrases, [geo_id], language_id
        )
        for m in metrics:
            m["location"] = location_name
            results.append(m)
    results.sort(key=lambda r: -r["avg_monthly_searches"])
    return results


def parse_args():
    parser = argparse.ArgumentParser(description="Step 2: location-based keyword volume")
    parser.add_argument("--customer-id", required=True)
    parser.add_argument("--language", default="1000")
    parser.add_argument("--out", default=None)
    return parser.parse_args()


def main():
    args = parse_args()
    client = load_client()

    try:
        results = run_location_research(client, args.customer_id, BASE_TERMS, LOCATIONS, args.language)
    except GoogleAdsException as ex:
        print(f"Request failed with status {ex.error.code().name}:")
        for error in ex.failure.errors:
            print(f"  {error.message}")
        sys.exit(1)

    print(f"{'Keyword':<40}{'Location':<16}{'Avg/mo':>8}{'Competition':>14}{'Bid range':>22}")
    for r in results:
        bid_range = f"${r['low_top_of_page_bid']:.2f}-${r['high_top_of_page_bid']:.2f}"
        print(f"{r['keyword']:<40}{r['location']:<16}{r['avg_monthly_searches']:>8}{r['competition']:>14}{bid_range:>22}")

    if args.out:
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        with open(args.out, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
            writer.writeheader()
            writer.writerows(results)
        print(f"\nSaved {len(results)} rows to {args.out}")


if __name__ == "__main__":
    main()
