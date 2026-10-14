"""
Step 2 for Lumberland (timber-supplies-lni): town-level location keywords
across the lower North Island. Resolves each place name internally, then
pulls exact-phrase historical metrics per location (same technique as
step2_location_keywords.py).

Usage: venv/bin/python scripts/step2_timber_lni.py
"""
import csv, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.google_ads_config import load_client
from lib.keyword_planner import resolve_locations, get_keyword_historical_metrics

CUSTOMER_ID = "9952256901"
OUT = "output/timber-supplies-lni/step2_location_keywords.csv"

BASE_TERMS = [
    "pole shed", "pole sheds", "pole barn", "farm shed", "farm sheds", "hay shed",
    "clear span shed", "large shed",
    "post and rail fencing", "post and rail fence", "fence posts", "fencing supplies",
    "chicken coop", "picnic table", "sleepout",
]
PLACES = [
    "Palmerston North", "Feilding", "Levin", "Foxton", "Ashhurst", "Bulls", "Marton", "Taihape",
    "Whanganui", "Dannevirke", "Woodville", "Pahiatua", "Eketahuna",
    "New Plymouth", "Hawera", "Stratford", "Inglewood", "Opunake",
    "Napier", "Hastings", "Havelock North", "Waipukurau", "Wairoa",
    "Masterton", "Carterton", "Greytown", "Featherston", "Martinborough",
    "Otaki", "Paraparaumu", "Waikanae", "Porirua", "Upper Hutt", "Lower Hutt", "Wellington",
    "Manawatu", "Horowhenua", "Wairarapa", "Taranaki", "Hawke's Bay", "Kapiti",
]
PREF = {"City": 0, "District": 1, "Locality": 2, "Region": 3}

client = load_client()
geo = {}
for p in PLACES:
    cands = [c for c in resolve_locations(client, [p]) if c["name"].lower().startswith(p.lower().split("'")[0].lower())]
    cands.sort(key=lambda c: PREF.get(c["target_type"], 9))
    if cands:
        geo[p] = cands[0]
        print(f"{p:<20} -> {cands[0]['id']} {cands[0]['name']} ({cands[0]['target_type']})")
    else:
        print(f"{p:<20} -> NOT FOUND")

rows = []
for p, g in geo.items():
    phrases = [f"{t} {p.lower()}" for t in BASE_TERMS]
    for m in get_keyword_historical_metrics(client, CUSTOMER_ID, phrases, [str(g["id"])]):
        m["location"] = p
        m["geo_target_id"] = g["id"]
        rows.append(m)
rows.sort(key=lambda r: -r["avg_monthly_searches"])
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows)
print(len(rows), "rows;", sum(1 for r in rows if r["avg_monthly_searches"] > 0), "with volume")
for r in rows[:60]:
    print(r["avg_monthly_searches"], r["keyword"], "|", r["location"])
