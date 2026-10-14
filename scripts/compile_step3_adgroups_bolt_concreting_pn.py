"""
Step 3 for Bolt Concreting (2026-10-14): organises the approved Step 1 (+ the
single new Step 2 keyword) into STAGs per campaign.

Campaigns: Bottom of Funnel (Priority 1 + 2 combined) / Price Discovery.
Kept Step 1 "Manual Review" rows: cost/price wording -> Price Discovery,
everything else -> BOF - Priority 2 (PROCESS.md Step 3 item 3).
Exact match only (upload script is exact-only).
"""
import csv, json, re, sys

D = "output/bolt-concreting-palmerston-north"
OUT_CSV = f"{D}/step3_adgroups.csv"
PRICE = re.compile(r"\bcost\b|\bcosts\b|\bprice\b|\bprices\b|\bpricing\b|\bquotes?\b|\bhow much\b|\bestimate\b|\baverage\b|\bper (m2|metre|meter|square metre)\b")
LOC = r"\b(palmerston north|palmerston|palmy|feilding|manawatu|ashhurst|bunnythorpe|sanson|bulls|marton)\b"

BOF_P1 = [
    ("Driveway Replacement", r"\breplac|\bre ?concrete\b|\bnew driveway\b|\breplacement\b"),
    ("Concrete Patios", r"^(?!.*driveway).*\bpatio"),
    ("Concrete Paths", r"\bpath|\bfootpath|\bwalkway"),
    ("Concrete Floors", r"\bfloors?\b|\bflooring\b"),
    ("Concrete Slabs & Pads", r"\bslab|\bpad\b|\bshed\b"),
    ("Driveway Contractors", r"\bdriveway"),
    ("Concrete Layers & Placers", r"\blayers?\b|\bplacers?\b|\bpour|\blaying\b|\bfinishers?\b|\binstall"),
    ("Concreters Palmerston North", LOC),
    ("Concrete Contractors", r".*"),
]
BOF_P2 = [
    ("Exposed Aggregate", r"\baggregate"),
    ("Coloured Concrete", r"\bcolou?r"),
    ("Stamped & Decorative", r"\bstamped|\bstencil|\bimprint|\bpatterned|\bdecorative"),
    ("Foundations", r"\bfoundation|\bpiers?\b"),
    ("Concrete Steps", r"\bsteps?\b"),
    ("Carports & Garage Slabs", r"\bcarport|\bgarage"),
    ("Driveway Contractors", r"\bdriveway"),
    ("Concrete Contractors", r".*"),
]
PD = [
    ("Exposed Aggregate Costs", r"\baggregate"),
    ("Patio Costs", r"\bpatio"),
    ("Path Costs", r"\bpath|\bfootpath|\bwalkway"),
    ("Driveway Replacement Costs", r"\breplac|\bredo\b|\bre ?concrete\b|\bremove and replace\b"),
    ("Driveway Costs", r"\bdriveway|\bdrive\b"),
    ("Concrete Floor Costs", r"\bfloors?\b|\bflooring\b"),
    ("Slab & Pad Costs", r"\bslab|\bpad\b|\bshed\b|\bfoundation|\bcarport"),
    ("Concrete Costs", r".*"),
]
DROP = set()
BOF = "Bottom of Funnel"  # Priority 1 + 2 combined into one campaign (user, 2026-10-14)


def ad_group_for(rules, kw):
    for name, pat in rules:
        if re.search(pat, kw):
            return name
    sys.exit(f"ERROR: couldn't theme '{kw}'")


def main():
    s1 = json.load(open(f"{D}/step1_approved.json"))["kept_keywords"]
    s2 = [{"group": "BOF - Priority 1", "keyword": r["keyword"], "avg_monthly_searches": r["avg_monthly_searches"],
           "competition": r["competition"], "low_bid": r["low_top_of_page_bid"], "high_bid": r["high_top_of_page_bid"],
           "note": "Step 2 location keyword"} for r in csv.DictReader(open(f"{D}/step2_filtered.csv"))]
    out, seen = [], set()
    for r in s1 + s2:
        kw = r["keyword"]
        if kw in DROP or kw in seen:
            continue
        seen.add(kw)
        g = r["group"]
        if g == "Manual Review":
            g = "Price Discovery" if PRICE.search(kw) else "BOF - Priority 2"
        if g == "BOF - Priority 1":
            ag = ad_group_for(BOF_P1, kw)
            g = BOF
        elif g == "BOF - Priority 2":
            ag = ad_group_for(BOF_P2, kw)
            g = BOF
        elif g == "Price Discovery":
            ag = ad_group_for(PD, kw)
        else:
            sys.exit(f"unexpected category {g}")
        out.append({"campaign": g, "ad_group": ag, "section": f"{g} — {ag}", "keyword": kw,
                    "avg_monthly_searches": r["avg_monthly_searches"], "competition": r["competition"],
                    "low_bid": r["low_bid"], "high_bid": r["high_bid"], "note": r.get("note", "")})
    out.sort(key=lambda r: (r["campaign"], r["ad_group"], -int(r["avg_monthly_searches"]), r["keyword"]))
    with open(OUT_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader(); w.writerows(out)
    counts = {}
    for r in out:
        counts.setdefault(r["section"], []).append(r["keyword"])
    print(f"Wrote {len(out)} rows")
    for s, k in counts.items():
        print(f"## {s} ({len(k)}): " + ", ".join(k[:8]) + (" ..." if len(k) > 8 else ""))


if __name__ == "__main__":
    main()
