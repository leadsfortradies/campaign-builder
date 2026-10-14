"""
Final Step 1 build for Paint Aesthetics (Taupo), corrected 2026-10-07 per
user feedback:

1. Classification was over-including junk (road/line marking, concrete/
   epoxy/floor coatings, paint stripping/matching/mixing, overseas paint
   brands, scraped-looking business names, narrow single-component framing
   like "gutter/trim/room painter", subcontractor-recruitment intent) -
   classify_step1_taupo.py's HARD_EXCLUDES was extended to catch these
   themes (not just the exact keywords the user manually excluded).
2. Volume was pulled NZ-wide because Taupo District returned a flat "10 for
   everything" when queried via idea-generation. That inflated the whole
   list with national long-tail that won't actually get searched from
   Taupo. Fixed by using exact-phrase GenerateKeywordHistoricalMetrics
   (same technique as step2_location_keywords.py) scoped to Taupo District
   on a known candidate list, instead of broad idea-generation - this
   returns a real (if binary - 0 or 10, see below) local signal rather than
   a nationwide number.
3. New standing process rule: when a prior project already has approved
   Step 1 research for the same trade, reuse that keyword list (updated
   with fresh volumes for the new location) instead of a fresh broad idea-
   generation pass - Canterbury Painters' approved list is the base here,
   plus Taupo's own prior (nationwide) pull for deck/fence, which Canterbury
   doesn't cover.

Taupo District (pop ~25k) is too small for Keyword Planner to return
differentiated volume even via historical metrics - every phrase comes back
either 0 or the 10/mo floor, no numbers in between. That's still a real
signal (whether Google has ANY recorded search presence for that exact
phrase in Taupo) and is what actually matters here, just not a ranking
signal - so Priority 1 vs 2 falls back to intent-tier only within the
Taupo-verified set.
"""

import csv
import json
import sys

sys.path.insert(0, "scripts")
import classify_step1_taupo as c

TAUPO_GEO_CSV = "output/painting-taupo/raw_keywords_taupo_geo.csv"
OUT_CATEGORIZED = "output/painting-taupo/step1_categorized.csv"
OUT_NEGATIVES = "output/painting-taupo/step1_negative_keywords.csv"


def main():
    # ---- 1. full exclusion log across both source pulls (for negatives) ----
    nz_rows = list(csv.DictReader(open(c.IN_CSV)))
    cant_rows = json.load(open("web/data/painting-canterbury/step1.json"))["rows"]

    excluded_log = []
    classified = {}  # keyword -> (category, service_or_reason, tier, _)
    for r in nz_rows:
        if int(r["avg_monthly_searches"]) < c.MIN_SEARCHES:
            continue
        result = c.classify(r["keyword"])
        classified[r["keyword"]] = result
        if result[0] == "Excluded":
            _, reason, neg_type, _ = result
            excluded_log.append({"keyword": r["keyword"], "reason": reason, "neg_type": neg_type})
    for r in cant_rows:
        kw = r["keyword"]
        if kw in classified:
            continue
        result = c.classify(kw)
        classified[kw] = result
        if result[0] == "Excluded":
            _, reason, neg_type, _ = result
            excluded_log.append({"keyword": kw, "reason": reason, "neg_type": neg_type})

    # ---- 2. Taupo-geo volume lookup ----
    taupo_rows = list(csv.DictReader(open(TAUPO_GEO_CSV)))
    taupo_vol = {r["keyword"]: r for r in taupo_rows}

    # ---- 3. final candidate pool: classified non-excluded AND verified >=10/mo at Taupo ----
    price_discovery, manual_review, bof_candidates = [], [], []
    for kw, result in classified.items():
        tr = taupo_vol.get(kw)
        if not tr or int(tr["avg_monthly_searches"] or 0) < c.MIN_SEARCHES:
            continue  # no verified Taupo search presence - leave out, not a negative (data-quality cutoff, not irrelevance)
        cat = result[0]
        row = {
            "keyword": kw,
            "avg_monthly_searches": tr["avg_monthly_searches"],
            "competition": tr["competition"],
            "low_top_of_page_bid": tr["low_top_of_page_bid"],
            "high_top_of_page_bid": tr["high_top_of_page_bid"],
        }
        if cat == "Price Discovery":
            price_discovery.append(row)
        elif cat == "Manual Review":
            manual_review.append({**row, "note": result[1]})
        elif cat == "BOF":
            _, service, tier, _ = result
            bof_candidates.append({**row, "service": service, "tier": tier})

    # ---- 4. Priority 1/2 split - tier-driven (Taupo volume ties almost
    # everything at the 10/mo floor, so there's no meaningful volume signal
    # left to rank within it). No hard cap - Tier A/B always Priority 1.
    by_service = {}
    for r in bof_candidates:
        by_service.setdefault(r["service"], []).append(r)

    tier_rank = {"A": 0, "B": 1, "C": 2}
    priority1, priority2 = [], []
    FLOOR = 5

    for service, items in by_service.items():
        clusters = {}
        for r in items:
            clusters.setdefault(c.cluster_key(r["keyword"]), []).append(r)
        representatives = []
        for members in clusters.values():
            members.sort(key=lambda r: -int(r["avg_monthly_searches"]))
            representatives.append(members[0])
            priority2.extend(members[1:])
        representatives.sort(key=lambda r: (tier_rank[r["tier"]], -int(r["avg_monthly_searches"])))

        p1 = representatives[:FLOOR]
        for r in representatives[FLOOR:]:
            if r["tier"] in ("A", "B"):
                p1.append(r)
            else:
                priority2.append(r)
        priority1.extend(p1)

    # ---- 5. write categorized CSV ----
    def fmt(r, category, note=""):
        return {
            "category": category,
            "keyword": r["keyword"],
            "avg_monthly_searches": r["avg_monthly_searches"],
            "competition": r["competition"],
            "low_top_of_page_bid": r["low_top_of_page_bid"],
            "high_top_of_page_bid": r["high_top_of_page_bid"],
            "note": note,
        }

    out_rows = []
    for r in priority1:
        out_rows.append(fmt(r, "BOF - Priority 1"))
    for r in priority2:
        out_rows.append(fmt(r, "BOF - Priority 2"))
    for r in price_discovery:
        out_rows.append(fmt(r, "Price Discovery"))
    for r in manual_review:
        out_rows.append(fmt(r, "Manual Review", note=r["note"]))
    out_rows.sort(key=lambda r: (r["category"], -int(r["avg_monthly_searches"])))

    with open(OUT_CATEGORIZED, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["category", "keyword", "avg_monthly_searches", "competition", "low_top_of_page_bid", "high_top_of_page_bid", "note"])
        writer.writeheader()
        writer.writerows(out_rows)

    # ---- 6. negative keyword list (irrelevance-based excludes only, volume-floor drops don't count) ----
    phrase_negs, exact_negs = {}, []
    for r in excluded_log:
        if r["neg_type"]:
            phrase_negs.setdefault(r["neg_type"], []).append(r["keyword"])
        else:
            exact_negs.append(r["keyword"])

    phrase_terms = {
        "cheap": "cheap", "design": "design", "commercial": "commercial",
        "industrial": "industrial", "paint price": "paint price", "farm": "farm fencing",
        "security": "security gate", "roof": "roof", "wrong location": None,  # too varied for one phrase - handled below
        "floor coating": "floor coating", "line marking": "line marking",
        "paint stripping": "paint stripping", "paint matching": "paint matching",
        "overseas brand": None,
    }
    neg_rows = []
    for neg_type, kws in phrase_negs.items():
        term = phrase_terms.get(neg_type, neg_type)
        if term:
            neg_rows.append({"negative_keyword": term, "match_type": "Phrase", "source_count": len(kws)})
        else:
            for kw in sorted(set(kws)):
                neg_rows.append({"negative_keyword": kw, "match_type": "Exact", "source_count": 1})
    for kw in sorted(set(exact_negs)):
        neg_rows.append({"negative_keyword": kw, "match_type": "Exact", "source_count": 1})

    with open(OUT_NEGATIVES, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["negative_keyword", "match_type", "source_count"])
        writer.writeheader()
        writer.writerows(neg_rows)

    print(f"Priority 1: {len(priority1)}")
    print(f"Priority 2: {len(priority2)}")
    print(f"Price Discovery: {len(price_discovery)}")
    print(f"Manual Review: {len(manual_review)}")
    print(f"Total BOF/PD/MR rows: {len(out_rows)}")
    print(f"Negative keyword rows: {len(neg_rows)}")
    print(f"(Excluded-for-irrelevance across both source pulls: {len(excluded_log)})")


if __name__ == "__main__":
    main()
