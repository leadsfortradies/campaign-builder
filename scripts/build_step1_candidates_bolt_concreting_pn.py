"""
Step 1 candidate list + local volume for Bolt Concreting
(palmerstonnorthconcreting.co.nz, account 249-246-1698) - rebuild after the
2026-10-14 audit.

Scope (confirmed in chat 2026-10-14): concrete driveways, paths, patios,
slabs. NOT repairs/resurfacing (Bolt disputes those leads). Exact match only.

Candidates: the live account's existing keywords + every search term that
ever got a click (all campaigns), the concrete SEO research candidates
(output/concrete-manawatu-seo), plus tight manual seeds for gaps found in
the audit (replacement wording, pads/shed bases, price terms). Volume is
exact-phrase historical metrics for the account's target locations - never
nationwide idea generation (PROCESS.md Step 1).
"""
import csv, json, os, re, sys, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.google_ads_config import load_client
from lib.keyword_planner import map_competition, micros_to_currency

CUSTOMER_ID = "2492461698"
# Palmerston North City, Feilding City, Rangitikei District (current targets)
LOCATION_IDS = ["1011047", "9051263", "9117720"]
OUT_DIR = "output/bolt-concreting-palmerston-north"
SEO = "output/concrete-manawatu-seo/concrete-manawatu.candidates.json"
SEO_GROUPS = ["home", "driveway", "aggregate", "paths", "patio", "slabs", "cost", "decorative", "removal"]

SEEDS = {
 "seed_driveway": [
  "driveway replacement", "driveway replacement cost", "replace concrete driveway", "replace driveway",
  "replacing a concrete driveway", "re concrete driveway", "new concrete driveway", "new driveway",
  "new driveway cost", "new driveway palmerston north", "driveway installers", "driveway installers near me",
  "driveway installation", "driveway installation near me", "driveway concreters", "driveway concreters near me",
  "driveway builders", "driveway builders near me", "driveway contractors near me", "driveway contractors palmerston north",
  "driveway contractor near me", "concrete driveway contractors", "concrete driveway contractors near me",
  "concrete driveway installers", "concrete driveway installers near me", "concrete driveway builders",
  "concrete driveway company", "concrete driveway companies", "concrete driveway companies near me",
  "concrete driveway palmerston north", "concrete driveways palmerston north", "concrete driveway feilding",
  "concrete driveway near me", "concrete driveways near me", "concrete driveway installation palmerston north",
  "driveways palmerston north", "driveway palmerston north", "driveway feilding", "driveways feilding",
  "exposed aggregate driveway", "exposed aggregate driveways", "exposed aggregate driveway cost",
  "exposed aggregate driveway palmerston north", "coloured concrete driveway", "coloured concrete driveways",
  "driveway quote", "driveway quotes", "concrete driveway quote", "concrete driveway quotes",
  "concrete driveway cost", "concrete driveway cost nz", "concrete driveway cost per m2", "concrete driveway price",
  "concrete driveway prices", "concrete driveway cost per square metre", "how much does a concrete driveway cost",
  "how much does a concrete driveway cost nz", "how much does a new driveway cost", "how much to concrete a driveway",
  "how much to concrete a driveway nz", "how much does it cost to concrete a driveway", "cost to concrete a driveway",
  "cost of a concrete driveway", "cost of concrete driveway nz", "cost to replace a driveway", "cost to replace concrete driveway",
  "driveway cost nz", "driveway cost per m2", "driveway cost per square metre", "average cost of a concrete driveway",
  "average cost for a new driveway", "average driveway cost nz", "concrete driveway estimate", "driveway estimate",
  "driveway cost calculator", "concrete driveway cost calculator", "driveway cost calculator nz",
 ],
 "seed_paths": [
  "concrete path", "concrete paths", "concrete path cost", "concrete path cost nz", "concrete path cost per m2",
  "concrete path contractors", "concrete path installers", "concrete path installers near me", "concrete paths palmerston north",
  "concrete path palmerston north", "concrete pathway cost", "concrete pathway contractors", "concrete footpath",
  "concrete footpath cost", "concrete footpath contractors", "concrete footpath palmerston north", "concrete walkway cost",
  "concrete walkway contractors", "path concreters", "path concreters near me", "how much does a concrete path cost",
  "how much to concrete a path", "cost to concrete a path", "cost of concrete path", "concrete path quote",
  "paths palmerston north", "concrete path installation", "concrete pathway installation",
 ],
 "seed_patios": [
  "concrete patio", "concrete patios", "concrete patio cost", "concrete patio cost nz", "concrete patio cost per m2",
  "concrete patio contractors", "concrete patio installers", "concrete patio installers near me", "concrete patio builders",
  "concrete patio palmerston north", "concrete patios palmerston north", "concrete patio near me", "patio concreters",
  "patio concreters near me", "patio contractors palmerston north", "patio contractors near me", "patio builders palmerston north",
  "exposed aggregate patio", "exposed aggregate patio cost", "coloured concrete patio", "how much does a concrete patio cost",
  "how much does a concrete patio cost nz", "how much to concrete a patio", "cost to concrete a patio", "cost of a concrete patio",
  "cost to pour a concrete patio", "concrete patio quote", "concrete patio installation", "patio concrete cost",
  "outdoor concrete patio", "backyard concrete patio", "concrete outdoor area", "concrete outdoor living area",
 ],
 "seed_slabs": [
  "concrete slab", "concrete slabs", "concrete slab cost", "concrete slab cost nz", "concrete slab cost per m2",
  "concrete slab price", "concrete slab prices", "concrete slab contractors", "concrete slab installers",
  "concrete slab installers near me", "concrete slab installation", "concrete slab installation near me",
  "concrete slab palmerston north", "concrete slabs palmerston north", "concrete slab near me", "slab concreters",
  "slab concreters near me", "slab contractors palmerston north", "slab builders palmerston north", "house slab",
  "house slab cost", "house slab cost nz", "house slab price", "house slab contractors", "new house slab",
  "house slab palmerston north", "shed slab", "shed slab cost", "shed slab nz", "shed base concrete", "concrete shed base",
  "concrete shed base cost", "concrete pad", "concrete pad cost", "concrete pad cost nz", "concrete pad for shed",
  "concrete pad contractors", "concrete pad palmerston north", "concrete pad near me", "concrete base", "concrete base cost",
  "garage slab", "garage slab cost", "garage slab nz", "garage floor concrete", "garage floor slab", "garage floor slab cost",
  "concrete garage floor", "concrete garage floor cost", "concrete garage slab", "concrete floor", "concrete floor cost",
  "concrete floor contractors", "concrete floor slab", "concrete floor slab cost", "concrete floor palmerston north",
  "pole shed floor", "pole shed concrete floor", "pole shed slab", "sleepout slab", "sleepout concrete floor",
  "granny flat slab", "granny flat slab cost", "caravan pad", "caravan concrete pad", "concrete parking pad",
  "parking pad concrete", "car pad concrete", "concrete turnaround", "how much does a concrete slab cost",
  "how much does a concrete slab cost nz", "how much for a concrete slab", "how much to pour a concrete slab",
  "how much to lay a concrete slab", "cost to pour a concrete slab", "cost to lay a concrete slab", "cost of a concrete slab",
  "cost of a concrete pad", "cost to pour concrete slab nz", "price to pour a concrete slab", "concrete slab quote",
  "concrete slab estimate", "slab cost per square metre nz", "concrete slab cost calculator", "concrete slab cost calculator nz",
  "concrete slab calculator cost", "house slab cost per m2", "ribraft slab", "ribraft slab cost", "ribraft floor",
  "ribraft slab contractors", "waffle slab", "raft slab",
 ],
 "seed_general": [
  "concreters palmerston north", "concreter palmerston north", "concreters feilding", "concrete contractors palmerston north",
  "concrete contractors feilding", "concrete company palmerston north", "concrete companies palmerston north",
  "concrete layers palmerston north", "concrete placers palmerston north", "concrete laying palmerston north",
  "concrete laying contractors", "concrete laying services", "concrete laying cost", "concrete laying price",
  "concrete laying cost per m2", "concrete laying cost nz", "concrete laying near me", "concrete services palmerston north",
  "concreting services palmerston north", "concreting palmerston north", "concrete work palmerston north",
  "concrete palmerston north", "concrete palmerston", "concrete feilding", "concrete manawatu", "concreters manawatu",
  "concrete contractors manawatu", "residential concrete contractors", "residential concreters", "residential concreting",
  "local concreters", "local concrete contractors", "best concreters palmerston north", "best concrete contractors palmerston north",
  "concrete quote", "concrete quotes", "concrete quote palmerston north", "concrete cost per m2 nz", "concrete cost per square metre nz",
  "concrete price per m2", "concrete price per square metre", "concrete cost nz", "how much does concrete cost per m2",
  "how much does concrete laying cost", "how much does it cost to lay concrete", "how much to lay concrete",
  "how much to pour concrete", "cost to pour concrete", "cost of pouring concrete", "cost of laying concrete",
  "price to pour concrete", "concrete pouring cost", "concrete pouring cost per m2", "concrete pour cost nz",
  "cost of concrete per m2 laid", "concrete installation cost", "concrete per m2 installed", "concreting cost",
  "concreting cost per m2", "concreting price", "concreting quote",
 ],
}


def norm(k):
    k = re.sub(r"[^a-z0-9 ]", " ", k.lower())
    return re.sub(r"\s+", " ", k).strip()


def account_candidates(client):
    svc = client.get_service("GoogleAdsService")
    kws, terms = {}, {}
    q = ("SELECT ad_group_criterion.keyword.text, metrics.impressions, metrics.clicks, metrics.cost_micros, metrics.conversions "
         "FROM keyword_view WHERE segments.date BETWEEN '2025-05-01' AND '2026-10-14' AND ad_group_criterion.negative = FALSE")
    for b in svc.search_stream(customer_id=CUSTOMER_ID, query=q):
        for r in b.results:
            k = norm(r.ad_group_criterion.keyword.text); v = kws.setdefault(k, [0, 0, 0.0, 0.0]); m = r.metrics
            v[0] += m.impressions; v[1] += m.clicks; v[2] += m.cost_micros / 1e6; v[3] += m.conversions
    q = ("SELECT search_term_view.search_term, metrics.impressions, metrics.clicks, metrics.cost_micros, metrics.conversions "
         "FROM search_term_view WHERE segments.date BETWEEN '2025-05-01' AND '2026-10-14'")
    for b in svc.search_stream(customer_id=CUSTOMER_ID, query=q):
        for r in b.results:
            k = norm(r.search_term_view.search_term); v = terms.setdefault(k, [0, 0, 0.0, 0.0]); m = r.metrics
            v[0] += m.impressions; v[1] += m.clicks; v[2] += m.cost_micros / 1e6; v[3] += m.conversions
    # also pull every keyword that exists (even zero impressions)
    q = ("SELECT ad_group_criterion.keyword.text FROM ad_group_criterion WHERE ad_group_criterion.type='KEYWORD' "
         "AND ad_group_criterion.negative=FALSE AND ad_group_criterion.status != 'REMOVED'")
    for b in svc.search_stream(customer_id=CUSTOMER_ID, query=q):
        for r in b.results:
            kws.setdefault(norm(r.ad_group_criterion.keyword.text), [0, 0, 0.0, 0.0])
    return kws, terms


def metrics(client, keywords):
    svc = client.get_service("KeywordPlanIdeaService")
    req = client.get_type("GenerateKeywordHistoricalMetricsRequest")
    req.customer_id = CUSTOMER_ID
    req.keywords.extend(keywords)
    req.language = "languageConstants/1000"
    req.geo_target_constants = [f"geoTargetConstants/{i}" for i in LOCATION_IDS]
    req.keyword_plan_network = client.enums.KeywordPlanNetworkEnum.GOOGLE_SEARCH_AND_PARTNERS
    out = []
    for r in svc.generate_keyword_historical_metrics(request=req).results:
        m = r.keyword_metrics
        out.append({"keyword": r.text, "close_variants": list(r.close_variants),
                    "avg": m.avg_monthly_searches, "comp": map_competition(m.competition),
                    "low": micros_to_currency(m.low_top_of_page_bid_micros), "high": micros_to_currency(m.high_top_of_page_bid_micros)})
    return out


def main():
    client = load_client()
    kws, terms = account_candidates(client)
    sources = {}
    for k in kws: sources.setdefault(k, "live_account_keyword")
    for k, v in terms.items():
        if v[1] >= 1 or v[3] > 0: sources.setdefault(k, "account_search_term")
    seo = json.load(open(SEO))
    for g in SEO_GROUPS:
        for k in seo.get(g, []): sources.setdefault(norm(k), f"seo_{g}")
    for g, lst in SEEDS.items():
        for k in lst: sources.setdefault(norm(k), g)
    keywords = sorted(k for k in sources if k)
    print(len(keywords), "unique candidates")

    results, merged = {}, {}
    for i in range(0, len(keywords), 1000):
        for r in metrics(client, keywords[i:i + 1000]):
            results[r["keyword"]] = r
            for v in r["close_variants"]: merged.setdefault(v, r["keyword"])
    for k in keywords:
        if k not in results and k in merged:
            results[k] = dict(results[merged[k]], merged_with=merged[k])

    os.makedirs(OUT_DIR, exist_ok=True)
    perf = {}
    for k in keywords:
        a = kws.get(k, [0, 0, 0, 0]); t = terms.get(k, [0, 0, 0, 0])
        perf[k] = [max(a[0], t[0]), max(a[1], t[1]), max(a[2], t[2]), max(a[3], t[3])]
    with open(f"{OUT_DIR}/historical_local.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["keyword", "source", "avg_monthly_searches", "competition", "low_bid", "high_bid", "merged_with",
                    "ads_impr", "ads_clicks", "ads_cost", "ads_conv"])
        for k in keywords:
            r = results.get(k, {})
            p = perf[k]
            w.writerow([k, sources[k], r.get("avg", 0), r.get("comp", ""), round(r.get("low", 0), 2), round(r.get("high", 0), 2),
                        r.get("merged_with", ""), p[0], p[1], round(p[2], 2), round(p[3], 1)])
    print("with metrics:", len(results), "-> wrote", f"{OUT_DIR}/historical_local.csv")


if __name__ == "__main__":
    main()
