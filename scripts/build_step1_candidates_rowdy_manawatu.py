"""
Step 1 candidate list + local volume for Rowdy Builders (decks, fences,
pergolas, pool fencing, deck roofs/covers) - Manawatu rebuild of the
palmydecksandfences.co.nz account, 2026-10-13.

Per PROCESS.md "Reuse prior keyword research": candidates come from the
approved deck-fence-auckland Step 3 list (Auckland stripped out), the local
fence SEO candidate pull (output/fence-builder-palmerston-north-seo), the
live account's existing keywords, plus tight manual seeds for services the
Auckland run didn't cover well (pergolas, deck roofs/covers, non-timber
fence materials). Volume is exact-phrase historical metrics against the
account's own target locations - not nationwide idea generation.
"""

import csv
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib.google_ads_config import load_client
from lib.keyword_planner import map_competition, micros_to_currency

CUSTOMER_ID = "3592240013"
# Palmerston North, Feilding, Ashhurst, Levin, Marton, Bulls, Sanson,
# Woodville, Rangitikei District - the live account's existing targets.
LOCATION_IDS = ["1011047", "9051263", "9234396", "1011041", "9240393",
                "9249517", "9242815", "9246287", "9117720"]
OUT_DIR = "output/rowdy-builders-manawatu"

PERGOLA = [
    "pergola builders", "pergola builder", "pergola builders near me", "pergola builder near me",
    "pergola companies", "pergola company", "pergola companies near me", "pergola installers",
    "pergola installers near me", "pergola installation", "pergola contractors", "pergola contractors near me",
    "pergolas", "pergola", "pergolas near me", "pergola near me", "timber pergola", "wooden pergola",
    "timber pergola builders", "aluminium pergola", "aluminium pergolas", "aluminium pergola installers",
    "pergola with roof", "covered pergola", "pergola roof", "pergola roofing", "pergola with roof builders",
    "custom pergola", "custom pergolas", "custom built pergola", "attached pergola", "freestanding pergola",
    "deck and pergola builders", "deck and pergola builders near me", "pergola and deck builders",
    "pergola cost", "pergola cost nz", "pergola prices", "pergola price", "pergola prices nz",
    "how much does a pergola cost", "how much does a pergola cost nz", "cost to build a pergola",
    "cost to build a pergola nz", "pergola installation cost", "timber pergola cost", "aluminium pergola cost",
    "pergola quote", "pergola kits", "pergola kit nz", "pergola ideas", "pergola designs", "diy pergola",
    "how to build a pergola", "pergola plans", "louvre pergola", "louvre roof", "louvre roof pergola",
    "pergolas palmerston north", "pergola palmerston north", "pergola builders palmerston north",
]
DECK_ROOF = [
    "deck roof", "deck roofing", "deck roof builders", "deck roof installers", "deck roof installers near me",
    "covered deck", "covered decks", "covered deck builders", "covered deck builders near me",
    "deck cover", "deck covers", "deck cover installers", "roof over deck", "roof over deck builders",
    "deck canopy", "deck shelter", "deck roof nz", "deck roof ideas", "covered deck ideas",
    "polycarbonate deck roof", "clear deck roof", "deck roof cost", "deck roof cost nz", "covered deck cost",
    "covered deck cost nz", "cost to cover a deck", "cost to put a roof over a deck",
    "how much does it cost to build a covered deck", "covered deck cost calculator",
    "veranda", "verandah", "veranda builders", "verandah builders", "veranda builders near me",
    "verandah roof", "patio cover", "patio covers", "patio roof", "covered patio", "covered outdoor area",
    "outdoor room builders", "outdoor shelter", "deck and roof contractors near me",
]
FENCE_MATERIALS = [
    "aluminium fence installers", "aluminium fence installers near me", "aluminium fencing contractors",
    "aluminium fence company", "aluminium fencing companies", "aluminium fence builders",
    "steel fence installers", "steel fencing contractors", "metal fence installers", "metal fencing contractors",
    "iron fence", "iron fencing", "wrought iron fence", "wrought iron fencing", "iron fence installers",
    "composite fence", "composite fencing", "composite fence installers", "composite fencing installers",
    "composite fencing nz", "composite fence cost",
    "brick fence", "brick fence builders", "brick fence builders near me", "brick fencing", "block fence",
    "block wall fence", "concrete block fence", "masonry fence", "brick fence cost",
    "colorsteel fence installers", "colorbond fence installers", "colorsteel fencing contractors",
    "glass fence installers", "glass pool fence installers", "glass pool fencing installers",
    "pool fence installers", "pool fence installers near me", "pool fencing company", "pool fence company",
    "pool fencing companies near me", "pool fence contractors", "pool fencing contractors near me",
    "pvc fence", "vinyl fence", "timber fence installers", "timber fence installers near me",
    "paling fence builders", "paling fence contractors", "boundary fence builders", "privacy fence builders",
    "garden fence builders", "garden fence installers", "garden fence installers near me",
]


def auckland_candidates():
    rows = json.load(open("web/data/deck-fence-auckland/step3.json"))["rows"]
    out = []
    for r in rows:
        kw = re.sub(r"\s+", " ", re.sub(r"\b(west |north |south |east )?auckland\b", "", r["keyword"])).strip()
        if kw:
            out.append(kw)
    return out


def local_fence_seo_candidates():
    c = json.load(open("output/fence-builder-palmerston-north-seo/candidates.json"))
    return [k for v in c.values() for k in v]


def live_account_keywords():
    path = "/private/tmp/claude-501/-Users-liamemery-Desktop-Work-Shit-Google-Ads-Campaign-Builder/418d343f-4d9c-42e0-85ba-61020bf57496/scratchpad/audit/data/keywords.json"
    if not os.path.exists(path):
        return []
    return [r["ad_group_criterion"]["keyword"]["text"] for r in json.load(open(path))]


def historical_metrics_with_variants(client, keywords):
    svc = client.get_service("KeywordPlanIdeaService")
    request = client.get_type("GenerateKeywordHistoricalMetricsRequest")
    request.customer_id = CUSTOMER_ID
    request.keywords.extend(keywords)
    request.language = "languageConstants/1000"
    request.geo_target_constants = [f"geoTargetConstants/{lid}" for lid in LOCATION_IDS]
    request.keyword_plan_network = client.enums.KeywordPlanNetworkEnum.GOOGLE_SEARCH_AND_PARTNERS
    out = []
    for r in svc.generate_keyword_historical_metrics(request=request).results:
        m = r.keyword_metrics
        out.append({
            "keyword": r.text,
            "close_variants": list(r.close_variants),
            "avg_monthly_searches": m.avg_monthly_searches,
            "competition": map_competition(m.competition),
            "low_top_of_page_bid": micros_to_currency(m.low_top_of_page_bid_micros),
            "high_top_of_page_bid": micros_to_currency(m.high_top_of_page_bid_micros),
        })
    return out


def main():
    sources = {}
    for src, kws in (("auckland_approved", auckland_candidates()),
                     ("local_fence_seo", local_fence_seo_candidates()),
                     ("live_account", live_account_keywords()),
                     ("seed_pergola", PERGOLA), ("seed_deck_roof", DECK_ROOF),
                     ("seed_fence_materials", FENCE_MATERIALS)):
        for k in kws:
            k = re.sub(r"[^a-z0-9 ]", " ", k.lower())
            k = re.sub(r"\s+", " ", k).strip()
            if k and k not in sources:
                sources[k] = src
    keywords = sorted(sources)
    print(f"{len(keywords)} unique candidates")

    client = load_client()
    results = {}
    merged_into = {}
    for i in range(0, len(keywords), 1000):
        for r in historical_metrics_with_variants(client, keywords[i:i + 1000]):
            results[r["keyword"]] = r
            for v in r["close_variants"]:
                merged_into.setdefault(v, r["keyword"])
    # Keyword Planner folds close variants (plural, word order) into one
    # result - a candidate missing from the response isn't 0 volume, it
    # shares its variant's number.
    for k in keywords:
        if k not in results and k in merged_into:
            results[k] = dict(results[merged_into[k]], merged_with=merged_into[k])

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(f"{OUT_DIR}/historical_local.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["keyword", "source", "avg_monthly_searches", "competition", "low_bid", "high_bid", "merged_with"])
        for k in keywords:
            r = results.get(k, {})
            w.writerow([k, sources[k], r.get("avg_monthly_searches", 0), r.get("competition", ""),
                        round(r.get("low_top_of_page_bid", 0), 2), round(r.get("high_top_of_page_bid", 0), 2), r.get("merged_with", "")])
    print(f"returned metrics for {len(results)}; wrote {OUT_DIR}/historical_local.csv")


if __name__ == "__main__":
    main()
