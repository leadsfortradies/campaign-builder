"""
Keyword research via the Google Ads Keyword Planner API.

Usage:
    venv/bin/python scripts/keyword_research.py \
        --customer-id 1234567890 \
        --keywords "emergency plumber" "blocked drain" \
        --url "https://example.co.nz/plumbing" \
        --location 2554 \
        --language 1000 \
        --min-searches 10 \
        --out output/keywords.csv

--customer-id   the Google Ads account to run the search as (digits only,
                no dashes). This can be any account you have access to.
--keywords      one or more seed keywords (optional if --url is given)
--url           a page URL to pull seed ideas from (optional if --keywords given)
--location      one or more geo target constant IDs (default 2554 = New
                Zealand). Use scripts/resolve_location.py to look up IDs for
                specific towns/regions/cities.
--language      language constant ID (default 1000 = English)
--min-searches  drop keywords below this avg monthly search volume (default 0)
--out           optional CSV output path

At least one of --keywords / --url is required.
"""

import argparse
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from google.ads.googleads.errors import GoogleAdsException
from lib.google_ads_config import load_client
from lib.keyword_planner import generate_keyword_ideas


def parse_args():
    parser = argparse.ArgumentParser(description="Google Ads Keyword Planner research")
    parser.add_argument("--customer-id", required=True, help="Google Ads customer ID, digits only")
    parser.add_argument("--keywords", nargs="*", default=[], help="Seed keywords")
    parser.add_argument("--url", default=None, help="Seed page URL")
    parser.add_argument("--location", nargs="*", default=["2554"], help="Geo target constant ID(s) (default: New Zealand)")
    parser.add_argument("--language", default="1000", help="Language constant ID (default: English)")
    parser.add_argument("--min-searches", type=int, default=0, help="Minimum avg monthly searches to keep")
    parser.add_argument("--out", default=None, help="Optional CSV output path")
    args = parser.parse_args()

    if not args.keywords and not args.url:
        parser.error("Provide at least one of --keywords or --url")

    return args


def main():
    args = parse_args()
    client = load_client()

    try:
        results = generate_keyword_ideas(
            client,
            args.customer_id,
            keywords=args.keywords,
            url=args.url,
            location_ids=args.location,
            language_id=args.language,
            min_avg_monthly_searches=args.min_searches,
        )
    except GoogleAdsException as ex:
        print(f"Request failed with status {ex.error.code().name}:")
        for error in ex.failure.errors:
            print(f"  {error.message}")
        sys.exit(1)

    if not results:
        print("No keyword ideas returned.")
        return

    print(f"{'Keyword':<40}{'Avg monthly searches':>22}{'Competition':>14}{'Bid range (low-high)':>24}")
    for r in results:
        bid_range = f"${r['low_top_of_page_bid']:.2f}-${r['high_top_of_page_bid']:.2f}"
        print(f"{r['keyword']:<40}{r['avg_monthly_searches']:>22}{r['competition']:>14}{bid_range:>24}")

    if args.out:
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        with open(args.out, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
            writer.writeheader()
            writer.writerows(results)
        print(f"\nSaved {len(results)} rows to {args.out}")


if __name__ == "__main__":
    main()
