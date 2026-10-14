"""
Step 6 extensions for Bolt Concreting (2026-10-14), both campaigns. Sitelink
copy is shared across ad groups; each ad group's links point at its own Step 5
landing page + a section anchor that exists on every /quote/ page
(#form-anchor, #anchor-services, #anchor-gallery, #anchor-testimonials,
#how-it-works, #areas). Link text 25, descriptions 25, callouts 25.
Facts only from the site (17+ Facebook reviews, 48-hour quote, owner does the
work, 12+ years, guaranteed workmanship). Dropped the old "Affordable
Pricing" callout (standing no-cheap/affordable rule).
"""
import csv, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.webapp_export import write_step6_sitelinks_csv

PROJECT = "bolt-concreting-palmerston-north"
LABEL = "Bolt Concreting - Palmerston North (rebuild)"
OUT_CSV = f"output/{PROJECT}/step6_sitelinks.csv"

SITELINKS = [
    ("Free On-Site Quote", "Firm Written Price", "Within 48 Hours", "form-anchor"),
    ("5-Star Rated", "17+ Facebook Reviews", "Real Customer Feedback", "anchor-testimonials"),
    ("See Our Work", "Recent Concrete Jobs", "Driveways, Paths, Slabs", "anchor-gallery"),
    ("Our Services", "Driveways To Slabs", "New Concrete Only", "anchor-services"),
    ("How It Works", "Quote, Pour, Clean Up", "Owner Does The Work", "how-it-works"),
    ("Service Areas", "Palmy And Manawatū", "Feilding, Ashhurst & More", "areas"),
]
CALLOUTS = [
    "Free On-Site Quotes", "Quote Within 48 Hours", "One Firm Price In Writing",
    "Owner Does The Work", "12+ Years Experience", "Workmanship Guaranteed",
]
SNIPPET_HEADER = "Service Catalog"
SNIPPET_VALUES = ["Concrete Driveways", "Concrete Paths", "Concrete Patios", "Concrete Slabs",
                  "Concrete Floors", "Concrete Steps", "Exposed Aggregate"]


def main():
    urls = {g["name"]: g["url"] for g in json.load(open(f"web/data/{PROJECT}/step5.json"))["ad_groups"]}
    errors = []
    for text, d1, d2, _ in SITELINKS:
        errors += [f"too long: {t}" for t in (text, d1, d2) if len(t) > 25]
    errors += [f"callout too long: {c}" for c in CALLOUTS if len(c) > 25]
    errors += [f"snippet value too long: {v}" for v in SNIPPET_VALUES if len(v) > 25]
    if len(CALLOUTS) != 6 or len(SITELINKS) != 6:
        errors.append("need 6 callouts and 6 sitelinks")
    if errors:
        sys.exit("\n".join(errors))
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ad_group", "sitelink_number", "sitelink_text", "sitelink_char_count", "description_1",
                    "description_1_char_count", "description_2", "description_2_char_count", "final_url"])
        for ad_group, base in urls.items():
            for i, (text, d1, d2, anchor) in enumerate(SITELINKS, 1):
                w.writerow([ad_group, i, text, len(text), d1, len(d1), d2, len(d2), f"{base.rstrip('/')}#{anchor}"])
    print(f"Wrote {len(urls) * len(SITELINKS)} sitelinks for {len(urls)} ad groups to {OUT_CSV}")
    write_step6_sitelinks_csv(PROJECT, LABEL, OUT_CSV, callouts=CALLOUTS,
                              snippet_header=SNIPPET_HEADER, snippet_values=SNIPPET_VALUES)


if __name__ == "__main__":
    main()
