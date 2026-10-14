"""
Steps 1 (final filter) + 2 + 3 for Lumberland (timber-supplies-lni), per the
user's 2026-10-14 direction:
  - drop ALL timber/decking terms for now (incl. kwila, Price Discovery)
  - drop tool shed / garden shed terms
  - Manual Review rows are NOT carried (unresolved, not approved)
  - add the location keywords that have real exact-phrase volume
  - split into STAGs per campaign (BOF - Priority 1 / 2 / Price Discovery)
Outputs under output/timber-supplies-lni/.
"""
import csv, re, sys
from collections import Counter, defaultdict

D = "output/timber-supplies-lni"
rows = list(csv.DictReader(open(f"{D}/step1_categorized.csv")))

DROP = re.compile(r"\bdeck(ing)?\b|\bkwila\b|\btool sheds?\b|\bgarden (storage |tool )?sheds?\b|\btimber deck\b|\bdecks?\b")

kept = []
dropped = Counter()
for r in rows:
    if r["category"] == "Manual Review":
        dropped["manual review (not carried)"] += 1
        continue
    if r["service"] == "Decking Timber" or DROP.search(r["keyword"]):
        dropped["decking / tool shed / garden shed"] += 1
        continue
    kept.append(r)

# ---- step 2: location keywords with real volume (per-location geo OR NZ-wide exact) ----
loc = {}
for fn in ("step2_location_keywords.csv", "step2_nz_exact.csv"):
    try:
        for r in csv.DictReader(open(f"{D}/{fn}")):
            if int(r["avg_monthly_searches"]) >= 10:
                loc[r["keyword"]] = r
    except FileNotFoundError:
        pass
loc = {k: v for k, v in loc.items() if not re.search(r"timber|deck", k)}  # timber out for now
step2_rows = sorted(loc.values(), key=lambda r: -int(r["avg_monthly_searches"]))
with open(f"{D}/step2_filtered.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["keyword", "avg_monthly_searches", "competition", "competition_index", "low_top_of_page_bid", "high_top_of_page_bid", "location"])
    for r in step2_rows:
        place = r.get("location") or next((p for p in ["palmerston north","wellington","hastings","manawatu","taranaki","wairarapa","hawke's bay","new plymouth","lower hutt"] if r["keyword"].endswith(p)), "")
        w.writerow([r["keyword"], r["avg_monthly_searches"], r["competition"], r.get("competition_index", ""), r["low_top_of_page_bid"], r["high_top_of_page_bid"], place])

# ---- step 3: ad groups ----
GROUPS = [  # (ad group, regex) - first match wins, per service
    ("Pole Sheds", [
        ("Farm & Hay Sheds", r"\bfarm\b|\bhay\b|\bcalf\b|\bimplement\b|\bmachinery\b|\bwool\b|\bshearing\b|\bstock\b|\blivestock\b|\bagri\b|\bdairy\b|\btractor\b|\brural\b"),
        ("Pole Sheds", r".*"),
    ]),
    ("Large Clear Span Sheds", [
        ("Clear Span Sheds", r"\bclear ?span\b|\bwide ?span\b|\bspan sheds?\b|\bportal\b|\bsteel frame\b|\btimber frame\b"),
        ("Large Sheds", r".*"),
    ]),
    ("Post & Rail Fencing", [
        ("Rural & Farm Fencing", r"\bfarm\b|\brural\b|\bagri|\bag fencing\b|\bhorse\b|\bcow\b|\bfield\b|\bstock\b|\bsheep\b|\bpaddock\b|\blifestyle\b|\bcattle\b|\bdeer\b"),
        ("Post & Rail Fencing", r"\brails?\b|\bpost (and|&) rail\b|\bhalf round\b"),
        ("Fence Posts", r".*"),
    ]),
    ("Made to Order & Custom Builds", [
        ("Chicken Coops", r"\bchicken\b|\bhen\b|\bchook\b|\bcoops?\b|\bpoultry\b"),
        ("Picnic Tables", r"\bpicnic\b"),
        ("Sleepouts & Cabins", r"\bsleep ?outs?\b|\bcabins?\b"),
        ("Outdoor Furniture & Benches", r"\bbench|\bfurniture\b|\boutdoor (table|seating)\b|\bseat"),
        ("Custom Built Sheds", r".*"),
    ]),
    ("General Sheds", [("Sheds For Sale", r".*")]),
]
G = dict(GROUPS)

def ad_group(service, kw):
    for name, pat in G[service]:
        if re.search(pat, kw):
            return name
    sys.exit(f"unassigned: {kw}")

def service_of_loc(kw):
    if re.search(r"chicken|coop", kw): return "Made to Order & Custom Builds"
    if re.search(r"picnic", kw): return "Made to Order & Custom Builds"
    if re.search(r"sleep", kw): return "Made to Order & Custom Builds"
    if re.search(r"pole|farm shed|hay shed", kw): return "Pole Sheds"
    if re.search(r"span|large shed", kw): return "Large Clear Span Sheds"
    return "Post & Rail Fencing"

out = []
seen = set()
for r in kept:
    camp = r["category"]
    ag = ad_group(r["service"], r["keyword"])
    out.append({"campaign": camp, "ad_group": ag, "keyword": r["keyword"], "avg_monthly_searches": r["avg_monthly_searches"],
                "competition": r["competition"], "low_bid": r["low_top_of_page_bid"], "high_bid": r["high_top_of_page_bid"], "note": ""})
    seen.add(r["keyword"])
for r in step2_rows:
    if r["keyword"] in seen:
        continue
    svc = service_of_loc(r["keyword"])
    out.append({"campaign": "BOF - Priority 1", "ad_group": ad_group(svc, r["keyword"]), "keyword": r["keyword"],
                "avg_monthly_searches": r["avg_monthly_searches"], "competition": r["competition"],
                "low_bid": r["low_top_of_page_bid"], "high_bid": r["high_top_of_page_bid"], "note": "location keyword"})
for o in out:
    o["section"] = f'{o["campaign"]} — {o["ad_group"]}'
out.sort(key=lambda o: (o["campaign"], o["ad_group"], -int(o["avg_monthly_searches"]), o["keyword"]))
with open(f"{D}/step3_adgroups.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["campaign","ad_group","section","keyword","avg_monthly_searches","competition","low_bid","high_bid","note"])
    w.writeheader(); w.writerows(out)

# final step1 view (kept rows only)
with open(f"{D}/step1_final.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(kept[0].keys()))
    w.writeheader(); w.writerows(kept)

print("dropped:", dict(dropped), "| kept step1:", len(kept), "| location kws:", len(step2_rows))
t = defaultdict(lambda: [0, 0])
for o in out:
    k = (o["campaign"], o["ad_group"]); t[k][0] += 1; t[k][1] += int(o["avg_monthly_searches"])
for k, v in sorted(t.items()): print(k, v)
