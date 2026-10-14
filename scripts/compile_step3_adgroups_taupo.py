"""
Step 3 for Paint Aesthetics (Taupo): organises the approved Step 1 keyword
list into Single Themed Ad Groups (STAGs), split per campaign (BOF -
Priority 1 / BOF - Priority 2 / Price Discovery), per PROCESS.md Step 3.

Theme assignment reuses Step 1's own service-pattern matching
(classify_step1_taupo.SERVICE_PATTERNS) so the ad-group theme for each
keyword is derived the same way its BOF service bucket was, rather than a
second hand-written keyword list - this project's keywords are already
tightly enough scoped (see Step 1's Taupo-volume rebuild) that there's no
need to hand-curate a separate theme list the way the first Auckland test
run did.

Usage:
    venv/bin/python scripts/compile_step3_adgroups_taupo.py <approval.json>
"""

import csv
import json
import sys

sys.path.insert(0, "scripts")
from classify_step1_taupo import SERVICE_PATTERNS

OUT_CSV = "output/painting-taupo/step3_adgroups.csv"

THEME_TO_AD_GROUP = {
    "House Painting (General)": "General House Painting",
    "Interior Painting": "Interior Painting",
    "Exterior Painting": "Exterior Painting",
    "Deck Painting/Staining": "Deck Painting & Staining",
    "Fence Painting/Staining": "Fence Painting & Staining",
}

# one-off manual calls for keywords SERVICE_PATTERNS can't theme cleanly
MANUAL_THEME = {
    "wall primer cost": "House Painting (General)",
    "exterior deck painters near me": "Deck Painting/Staining",
}


def theme_for(keyword):
    if keyword in MANUAL_THEME:
        return MANUAL_THEME[keyword]
    kw = keyword.lower()
    matched = [name for name, pat in SERVICE_PATTERNS.items() if pat.search(kw)]
    if "House Painting (General)" in matched and len(matched) > 1:
        matched.remove("House Painting (General)")
    if not matched:
        sys.exit(f"ERROR: couldn't theme '{keyword}' - add it to MANUAL_THEME")
    # prefer the more specific (non-general) theme first if multiple survive
    return matched[0]


def main():
    if len(sys.argv) != 2:
        sys.exit("Usage: compile_step3_adgroups_taupo.py <path to approved kept_keywords JSON>")

    with open(sys.argv[1], encoding="utf-8") as f:
        approval = json.load(f)

    rows = approval["kept_keywords"] if "kept_keywords" in approval else approval

    out_rows = []
    for row in rows:
        campaign = row["group"]
        theme = theme_for(row["keyword"])
        ad_group = THEME_TO_AD_GROUP[theme]
        out_rows.append(
            {
                "campaign": campaign,
                "ad_group": ad_group,
                "section": f"{campaign} — {ad_group}",
                "keyword": row["keyword"],
                "avg_monthly_searches": row["avg_monthly_searches"],
                "competition": row["competition"],
                "low_bid": row["low_bid"],
                "high_bid": row["high_bid"],
                "note": row.get("note", ""),
            }
        )

    assigned = {r["keyword"] for r in out_rows}
    missing = [r["keyword"] for r in rows if r["keyword"] not in assigned]
    if missing:
        print(f"ERROR: {len(missing)} approved keywords not assigned to any ad group:")
        for m in missing:
            print(f"  {m}")
        sys.exit(1)

    out_rows.sort(key=lambda r: (r["campaign"], r["ad_group"], -r["avg_monthly_searches"]))

    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
        writer.writeheader()
        writer.writerows(out_rows)

    print(f"Wrote {len(out_rows)} rows to {OUT_CSV}\n")
    campaign_counts = {}
    for r in out_rows:
        campaign_counts[r["campaign"]] = campaign_counts.get(r["campaign"], 0) + 1
    for c, n in campaign_counts.items():
        print(f"Campaign: {c} - {n} keywords")
    print()
    counts = {}
    for r in out_rows:
        counts[r["section"]] = counts.get(r["section"], 0) + 1
    for section, n in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {section}: {n}")


if __name__ == "__main__":
    main()
