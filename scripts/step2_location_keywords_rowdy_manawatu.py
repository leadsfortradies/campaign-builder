"""
Step 2 for Rowdy Builders (Manawatu rebuild, 2026-10-13): "<service term>
<town>" phrases for each town in the account's service area, exact-phrase
volume per town via step2_location_keywords.run_location_research().
Manawatu is a region of separate towns, so suburb-style expansion is worth
running here (PROCESS.md Step 2).
"""

import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib.google_ads_config import load_client
from step2_location_keywords import run_location_research

CUSTOMER_ID = "3592240013"
OUT = "output/rowdy-builders-manawatu/step2_location_keywords.csv"

BASE_TERMS = [
    "deck builders", "deck builder", "decks", "decking", "deck contractors",
    "fence builders", "fence builder", "fencing", "fences", "fencing contractors", "fence company", "fencers",
    "pergola", "pergolas", "pergola builders",
    "pool fencing", "pool fence",
    "builders decks and fences",
]

# Town name as searched -> geo target constant for that town
LOCATIONS = {
    "palmerston north": "1011047",
    "palmy": "1011047",
    "manawatu": "9117711",
    "feilding": "9051263",
    "ashhurst": "9234396",
    "levin": "1011041",
    "marton": "9240393",
    "bulls": "9249517",
    "sanson": "9242815",
    "woodville": "9246287",
}


def main():
    client = load_client()
    results = run_location_research(client, CUSTOMER_ID, BASE_TERMS, LOCATIONS)
    with open(OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["location", "keyword", "avg_monthly_searches", "competition", "low_top_of_page_bid", "high_top_of_page_bid"])
        for r in results:
            w.writerow([r["location"], r["keyword"], r["avg_monthly_searches"], r["competition"],
                        round(r["low_top_of_page_bid"], 2), round(r["high_top_of_page_bid"], 2)])
    print(f"{len(results)} phrases, {sum(1 for r in results if r['avg_monthly_searches'] >= 10)} with 10+/mo -> {OUT}")


if __name__ == "__main__":
    main()
