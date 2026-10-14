"""Discovery pull: local Keyword Planner idea generation per seed group.

Only used to SEE what people search locally (phrasing, sub-services). Local
numbers are mostly floored at 10 and full of US junk - never treat this
output as the keyword list. Prints concrete-relevant ideas for review.

Usage:
  venv/bin/python .claude/skills/seo/scripts/pull_ideas.py <out_dir> <seeds.json> --geo 9117710 9117711 [--match "regex"]
seeds.json: {"group name": ["seed", ...], ...}
"""
import argparse, csv, json, os, re, sys
ROOT = os.getcwd()
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from lib.google_ads_config import load_client
from lib.keyword_planner import generate_keyword_ideas

ap = argparse.ArgumentParser()
ap.add_argument("out_dir"); ap.add_argument("seeds")
ap.add_argument("--geo", nargs="+", required=True)
ap.add_argument("--customer-id", default="9952256901")
ap.add_argument("--match", default=None, help="regex a keyword must match to be printed")
a = ap.parse_args()
os.makedirs(a.out_dir, exist_ok=True)
client = load_client(); rows = {}
for group, seeds in json.load(open(a.seeds)).items():
    res = generate_keyword_ideas(client, a.customer_id, keywords=seeds, location_ids=a.geo)
    print(group, len(res), file=sys.stderr)
    for r in res:
        r["seed_group"] = group
        rows.setdefault(r["keyword"], r)
out = os.path.join(a.out_dir, "raw_ideas_local.csv")
rows = sorted(rows.values(), key=lambda r: -r["avg_monthly_searches"])
with open(out, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
rx = re.compile(a.match) if a.match else None
for r in rows:
    if r["avg_monthly_searches"] >= 10 and (not rx or rx.search(r["keyword"])):
        print(r["avg_monthly_searches"], r["keyword"])
print(f"saved {len(rows)} ideas -> {out}", file=sys.stderr)
