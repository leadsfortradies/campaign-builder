"""
Step 2 for Bolt Concreting (2026-10-14): "<service term> <town>" phrases per
town in the confirmed service area (Palmerston North, Feilding, Ashhurst,
Bunnythorpe, Sanson, Bulls, Marton - Levin excluded by the user), exact-phrase
volume per town via GenerateKeywordHistoricalMetrics. Keywords are used
exact match only. Keeps >=10/mo, drops anything already approved in Step 1,
and applies the same scope/standing excludes as Step 1.
"""
import csv, json, os, sys, re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.google_ads_config import load_client
from step2_location_keywords import run_location_research
import classify_step1_bolt_concreting_pn as c1

CUSTOMER_ID = "2492461698"
D = "output/bolt-concreting-palmerston-north"
APPROVAL = "web/approvals/processed/bolt-concreting-palmerston-north__step1__1791924980.json"
if not os.path.exists(APPROVAL):
    APPROVAL = "web/approvals/bolt-concreting-palmerston-north__step1__1791924980.json"

BASE_TERMS = [
    "concreters", "concreter", "concrete contractors", "concrete company", "concrete companies", "concrete services",
    "concreting", "concreting services", "concrete layers", "concrete placers", "concrete",
    "concrete driveways", "concrete driveway", "driveways", "driveway contractors", "driveway concreters",
    "driveway replacement", "new driveway", "concrete paths", "concrete path", "concrete footpath",
    "concrete patios", "concrete patio", "patio concreters", "concrete slabs", "concrete slab", "house slab",
    "shed slab", "concrete pad", "concrete floor",
    # price discovery
    "concrete cost", "concrete quote", "concrete driveway cost", "driveway cost", "concrete slab cost",
    "concrete patio cost", "concrete path cost", "concrete cost per m2", "how much does concrete cost",
    "how much does a concrete driveway cost",
]
LOCATIONS = {
    "palmerston north": "1011047",
    "palmy": "1011047",
    "feilding": "9051263",
    "ashhurst": "9234396",
    "bunnythorpe": "9237348",
    "sanson": "9242815",
    "bulls": "9249517",
    "marton": "9240393",
    "manawatu": "9117711",
}


def main():
    approved = {r["keyword"] for r in json.load(open(APPROVAL))["kept_keywords"]}
    client = load_client()
    res = run_location_research(client, CUSTOMER_ID, BASE_TERMS, LOCATIONS)
    raw = f"{D}/step2_location_keywords.csv"
    with open(raw, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["location", "keyword", "avg_monthly_searches", "competition", "low_top_of_page_bid", "high_top_of_page_bid"])
        for r in res:
            w.writerow([r["location"], r["keyword"], r["avg_monthly_searches"], r["competition"],
                        round(r["low_top_of_page_bid"], 2), round(r["high_top_of_page_bid"], 2)])
    kept, seen = [], set()
    dropped = {"under_10": 0, "dup_step1": 0, "scope": 0}
    for r in res:
        kw = r["keyword"]
        if r["avg_monthly_searches"] < 10:
            dropped["under_10"] += 1; continue
        if kw in approved or kw in seen:
            dropped["dup_step1"] += 1; continue
        cat, _, _ = c1.classify(kw)
        if cat == "Excluded":
            dropped["scope"] += 1; continue
        seen.add(kw)
        kept.append(r)
    out = f"{D}/step2_filtered.csv"
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["location", "keyword", "avg_monthly_searches", "competition", "low_top_of_page_bid", "high_top_of_page_bid", "note"])
        for r in sorted(kept, key=lambda r: (r["location"], -r["avg_monthly_searches"], r["keyword"])):
            w.writerow([r["location"], r["keyword"], r["avg_monthly_searches"], r["competition"],
                        round(r["low_top_of_page_bid"], 2), round(r["high_top_of_page_bid"], 2), ""])
    print(len(res), "phrases;", len(kept), "kept;", dropped)


if __name__ == "__main__":
    main()
