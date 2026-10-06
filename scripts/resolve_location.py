"""
Looks up Google Ads geo target constant IDs for place names, e.g. towns,
cities, or regions. Needed because Keyword Planner requires a precise
location ID, not a free-text place name.

Usage:
    venv/bin/python scripts/resolve_location.py "Palmerston North" "Feilding" "Ashhurst"

Prints candidate matches (id, name, country, type) for each name - pick the
right one (usually target_type "City" or "Locality") and use its id with
keyword_research.py's --location flag.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib.google_ads_config import load_client
from lib.keyword_planner import resolve_locations


def parse_args():
    parser = argparse.ArgumentParser(description="Resolve place names to Google Ads geo target constant IDs")
    parser.add_argument("names", nargs="+", help="Place names to look up")
    parser.add_argument("--country", default="NZ", help="ISO country code to bias results (default: NZ)")
    args = parser.parse_args()
    return args


def main():
    args = parse_args()
    client = load_client()

    results = resolve_locations(client, args.names, country_code=args.country)

    if not results:
        print("No matches found.")
        return

    print(f"{'ID':<12}{'Name':<30}{'Country':<10}{'Type':<15}")
    for r in results:
        print(f"{r['id']:<12}{r['name']:<30}{r['country_code']:<10}{r['target_type']:<15}")


if __name__ == "__main__":
    main()
