"""Exact-phrase volumes (local + NZ) for a curated candidate list.

Usage:
  venv/bin/python .claude/skills/seo/scripts/pull_volumes.py <out_dir> <candidates.json> --geo 9117710 9117711
candidates.json: {"group": ["keyword", ...], ...}  (groups are just for the printout)
Writes <out_dir>/historical.json {"kws": [...], "local": {kw: n}, "nz": {kw: n}}.
A keyword missing from local/nz = Google merged it as a close variant.
"""
import argparse, json, os, sys
ROOT = os.getcwd()
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from lib.google_ads_config import load_client
from lib.keyword_planner import get_keyword_historical_metrics

ap = argparse.ArgumentParser()
ap.add_argument("out_dir"); ap.add_argument("candidates")
ap.add_argument("--geo", nargs="+", required=True)
ap.add_argument("--customer-id", default="9952256901")
a = ap.parse_args()
groups = json.load(open(a.candidates))
kws = []
for ks in groups.values():
    for k in ks:
        k = k.lower().strip()
        if k not in kws: kws.append(k)
client = load_client()
def pull(geo):
    out = {}
    for i in range(0, len(kws), 500):
        for m in get_keyword_historical_metrics(client, a.customer_id, kws[i:i + 500], geo):
            out[m["keyword"]] = m["avg_monthly_searches"]
    return out
local, nz = pull(a.geo), pull(["2554"])
os.makedirs(a.out_dir, exist_ok=True)
json.dump({"kws": kws, "local": local, "nz": nz}, open(os.path.join(a.out_dir, "historical.json"), "w"), indent=0)
for g, ks in groups.items():
    rows = sorted({k.lower() for k in ks}, key=lambda k: -nz.get(k, -1))
    print(f"===== {g}")
    print("; ".join(f"{k} {local.get(k, 'cv')}/{nz.get(k, 'cv')}" for k in rows))
