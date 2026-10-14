"""
Step 6 extensions for Rowdy Builders (Manawatu rebuild, 2026-10-13), both
campaigns. Sitelink copy is shared across ad groups; each ad group's links
point at its own Step 5 landing page + a section anchor that exists on every
page of the new site (#quote, #reviews, #work, #why-us, #how-it-works,
#service-area). Text kept within Google's limits: link text 25, descriptions
25 (stricter than Google's 35, per PROCESS.md), callouts 25.

Usage:
    venv/bin/python scripts/build_step6_extensions_rowdy_manawatu.py
"""

import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib.webapp_export import write_step6_sitelinks_csv

PROJECT = "rowdy-builders-manawatu"
LABEL = "Rowdy Builders - Manawatu (rebuild)"
OUT_CSV = f"output/{PROJECT}/step6_sitelinks.csv"

SITELINKS = [
    ("Free On-Site Quote", "Written Within 48 Hours", "One Fixed Price", "quote"),
    ("5-Star Rated", "Real Customer Reviews", "Trusted By Palmy Locals", "reviews"),
    ("See Our Work", "100+ Projects Completed", "Browse Recent Jobs", "work"),
    ("Fully Insured", "10+ Years Experience", "Whoever Quotes, Builds", "why-us"),
    ("How It Works", "Quote, Build, Clean Up", "Old Materials Removed", "how-it-works"),
    ("Service Areas", "Palmy & Manawatū Wide", "Feilding To Levin", "service-area"),
]

CALLOUTS = [
    "Free On-Site Quotes",
    "Written Quote In 48 Hours",
    "Fixed Price In Writing",
    "Fully Insured",
    "100+ Projects Completed",
    "10+ Years Experience",
]

SNIPPET_HEADER = "Service Catalog"
SNIPPET_VALUES = ["Decks", "Fences", "Pergolas", "Pool Fencing", "Covered Decks", "Timber Fences", "Colorbond Fences"]


def main():
    urls = {g["name"]: g["url"] for g in json.load(open(f"web/data/{PROJECT}/step5.json"))["ad_groups"]}
    errors = []
    for text, d1, d2, _ in SITELINKS:
        errors += [f"too long: {t}" for t in (text, d1, d2) if len(t) > 25]
    errors += [f"callout too long: {c}" for c in CALLOUTS if len(c) > 25]
    errors += [f"snippet value too long: {v}" for v in SNIPPET_VALUES if len(v) > 25]
    if errors:
        sys.exit("\n".join(errors))

    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ad_group", "sitelink_number", "sitelink_text", "sitelink_char_count", "description_1",
                    "description_1_char_count", "description_2", "description_2_char_count", "final_url"])
        for ad_group, base in urls.items():
            for i, (text, d1, d2, anchor) in enumerate(SITELINKS, 1):
                w.writerow([ad_group, i, text, len(text), d1, len(d1), d2, len(d2), f"{base.rstrip('/')}#{anchor}"
                            if not base.endswith(".co.nz/") else f"{base}#{anchor}"])
    print(f"Wrote {len(urls) * len(SITELINKS)} sitelinks for {len(urls)} ad groups to {OUT_CSV}")
    write_step6_sitelinks_csv(PROJECT, LABEL, OUT_CSV, callouts=CALLOUTS,
                              snippet_header=SNIPPET_HEADER, snippet_values=SNIPPET_VALUES)


if __name__ == "__main__":
    main()
