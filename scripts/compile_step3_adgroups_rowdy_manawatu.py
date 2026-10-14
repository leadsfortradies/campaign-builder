"""
Step 3 for Rowdy Builders (Manawatu rebuild, 2026-10-13): organises the
approved Step 1 + Step 2 keywords into STAGs per campaign (BOF - Priority 1
/ Price Discovery - no Priority 2 keywords survived Step 1, every BOF term
had a hiring signal).

Step 2 town keywords all carry a locality marker + service word (Tier B),
so they go to BOF - Priority 1. Fewer, tighter ad groups than the live
account's 14 (most of which got no impressions) - fencing gets its own
Palmerston North and wider-Manawatu groups because that's where the town
volume actually is.

Usage:
    venv/bin/python scripts/compile_step3_adgroups_rowdy_manawatu.py
"""

import csv
import json
import re
import sys

D = "output/rowdy-builders-manawatu"
OUT_CSV = f"{D}/step3_adgroups.csv"

# Kept in the Step 1 approval but its twin "pergola" was excluded - bare
# product term, user told it stays out unless they say otherwise.
DROP = {"pergolas"}

BOF_RULES = [
    ("Pool Fencing", r"\bpool\b"),
    ("Pergolas", r"\bpergola"),
    ("Deck & Fence Builders", r"\bdeck\b.*\bfence\b|\bfence\b.*\bdeck\b"),
    ("Composite Decks", r"\bcomposite deck"),
    ("Timber Decks", r"\bkwila\b|\btimber decking\b|\bwood deck\b"),
    ("Deck Builders", r"\bdeck"),
    ("Fencing Manawatu, Levin & Marton", r"\b(manawatu|levin|marton)\b"),
    ("Fencing Palmerston North", r"\bpalmerston north\b"),
    ("Brick Fences", r"\bbrick\b"),
    ("Aluminium & Metal Fences", r"\balumin|\bsteel\b|\biron\b|\bcolorbond\b|\bmetal\b"),
    ("Timber Fences", r"\btimber\b|\bwood(en)?\b|\bpaling\b|\bpicket\b|\bgarden fence\b"),
    ("Fence Builders", r"\bfenc"),
]
PD_RULES = [
    ("Pool Fencing Costs", r"\bpool\b"),
    ("Pergola Costs", r"\bpergola"),
    ("Covered Deck Costs", r"\bcover|\broof\b"),
    ("Deck Costs", r"\bdeck"),
    ("Aluminium, Brick & Colorbond Fence Costs", r"\balumin|\bbrick\b|\bcolorbond\b"),
    ("Timber Fence Costs", r"\btimber\b|\bwood|\bpaling\b|\bpicket\b"),
    ("Fence Costs", r"\bfenc"),
]


def ad_group_for(campaign, kw):
    for name, pat in (PD_RULES if campaign == "Price Discovery" else BOF_RULES):
        if re.search(pat, kw):
            return name
    sys.exit(f"ERROR: couldn't theme '{kw}' ({campaign})")


def main():
    s1 = json.load(open(f"{D}/step1_approved.json"))["kept_keywords"]
    s2 = json.load(open(f"{D}/step2_approved.json"))["kept_keywords"]
    rows = [r for r in s1 if r["keyword"] not in DROP] + [{**r, "group": "BOF - Priority 1"} for r in s2]

    out = []
    for r in rows:
        campaign = r["group"]
        if campaign not in ("BOF - Priority 1", "BOF - Priority 2", "Price Discovery"):
            sys.exit(f"ERROR: unexpected category {campaign} for '{r['keyword']}'")
        ag = ad_group_for(campaign, r["keyword"])
        out.append({"campaign": campaign, "ad_group": ag, "section": f"{campaign} — {ag}", "keyword": r["keyword"],
                    "avg_monthly_searches": r["avg_monthly_searches"], "competition": r["competition"],
                    "low_bid": r["low_bid"], "high_bid": r["high_bid"], "note": r.get("note", "")})

    assigned = {r["keyword"] for r in out}
    missing = [r["keyword"] for r in rows if r["keyword"] not in assigned]
    if missing:
        sys.exit(f"ERROR: unassigned keywords: {missing}")

    out.sort(key=lambda r: (r["campaign"], r["ad_group"], -int(r["avg_monthly_searches"]), r["keyword"]))
    with open(OUT_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)

    print(f"Wrote {len(out)} rows to {OUT_CSV}")
    counts = {}
    for r in out:
        counts.setdefault(r["section"], []).append(r["keyword"])
    for section, kws in counts.items():
        print(f"\n## {section} ({len(kws)})\n  " + ", ".join(kws))


if __name__ == "__main__":
    main()
