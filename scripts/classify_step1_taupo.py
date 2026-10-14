"""
One-off: classifies the raw Keyword Planner output for Paint Aesthetics
(Taupo) per PROCESS.md Step 1's standing rules, applying the same judgment
that was made by hand on the Auckland/Canterbury runs, encoded as rules so it
scales to this run's larger (NZ-wide, 4417-row) result set. Output feeds
straight into webapp_sync.py step1.

Scope for this client (from Step 0): interior + exterior house painting,
deck painting/staining, fence painting/staining. Residential only. No roof
painting - client explicitly excludes it.
"""

import csv
import re

IN_CSV = "output/painting-taupo/raw_keywords_nz.csv"
OUT_CATEGORIZED = "output/painting-taupo/step1_categorized.csv"
OUT_NEGATIVES = "output/painting-taupo/step1_negative_keywords.csv"
OUT_EXCLUDED_LOG = "output/painting-taupo/step1_excluded_log.csv"

MIN_SEARCHES = 10

# ---------------------------------------------------------------------------
# Hard excludes (checked first, in order) - each is (regex, reason, neg_match_type)
# neg_match_type: "phrase" for a shared problem word/phrase worth blocking
# broadly, "exact" for a one-off that doesn't generalize.
# ---------------------------------------------------------------------------
HARD_EXCLUDES = [
    (r"\broofs?\b|\brespray", "roof painting - not a stated service", "roof"),
    (r"\bcheap(est)?\b|\baffordable\b|\bbudget\b|\blow cost\b", "cheap/affordable price-positioning - standing exclude", "cheap"),
    (r"\binterior design|\bdesigner\b", "interior design service, not painting labor", "design"),
    (r"\bindustrial\b", "commercial/industrial scope - client is residential only", "industrial"),
    (r"\bcommercial\b|\boffice\b|\bwarehouse\b|\bretail (store|shop)\b", "commercial scope - client is residential only", "commercial"),
    (r"\bdiy\b|^how to |\bhow do i\b|\byourself\b|\bhimself\b|\bherself\b", "DIY intent", None),
    (r"\bapprentice|\bjobs?\b|\bcareer|\bsalary|\bhiring\b.*\b(painters?|staff)\b|\bbecome a painter", "jobs/careers, not a customer search", None),
    (r"\bpaint colou?rs? (for|ideas|schemes|combinations)|\bbest colou?r\b|\bwhat colou?r\b|\bcolou?r (ideas|schemes|trends|palette)", "colour inspiration/advice, no hiring intent", None),
    (r"\b\d{1,2}\s?l(itre)?s?\b.*\bprice\b|\bpaint price\b|\bprice of paint\b|\bpaint prices\b|\bpaint brands?\b|\bbest paint brand", "product (tin of paint) pricing, not service pricing", "paint price"),
    (r"\bfarm\b|\brural\b|\bagricultural\b|\blivestock\b|\bpost and rail\b|\belectric fenc", "farm/rural/agricultural - wrong customer segment", "farm"),
    (r"\bsecurity (gate|fenc)", "security gate/fencing - not a stated service", "security"),
    (r"\bgate(s)?\b(?!.*fence)", "gates - not a stated service", None),
    (r"\bwallpaper (remov|hang|install)|\bhang wallpaper\b", "wallpapering - different trade", None),
    (r"\bplaster(er|ing)?\b(?! paint)|\bgib\s?stopp|\bgib fix", "plastering/gib stopping - different trade", None),
    (r"\bconcrete (paint|coat|seal)\w*\b|\bepoxy\b|\bgarage floor", "concrete/epoxy/garage floor coatings - different trade", "floor coating"),
    (r"\bfloor (paint|coat)\w*\b", "floor painting/coating - different trade", "floor coating"),
    (r"\bmetal painters?\b", "metal/structural painting - different material scope, not a stated service", None),
    (r"\bboat\b|\bcar paint|\bautomotive\b|\bfurniture paint|\bfurniture refinish|\bcabinet (paint|refinish)|\bkitchen cabinet|\bcabinets? paint", "wrong item type (not a house/deck/fence)", None),
    (r"\bcommercial\b", "commercial - not residential", None),
    (r"\b(auckland|wellington|christchurch|hamilton|tauranga|dunedin|napier|hastings|"
     r"palmerston north|nelson|rotorua|new plymouth|whangarei|invercargill|gisborne|"
     r"queenstown|timaru|whanganui|wanaka|manukau|north shore|lower hutt|upper hutt|"
     r"porirua|cambridge|te awamutu|matamata|phoenix|newton|austin|dallas)\b", "names a different location, not Taupo", "wrong location"),
    (r"\broad (paint|mark|strip)\w*|\bline (paint|mark|strip)\w*\b|\bcurb paint", "road/line marking - different trade", "line marking"),
    (r"\bpaint (strip|remov)\w*", "paint stripping/removal - different service (removal, not applying paint)", "paint stripping"),
    (r"\bpaint (match|mix)ing\b", "paint matching/mixing - a retail paint-shop service, not a painting contractor service", "paint matching"),
    (r"\b(nippon|asian|berger|benjamin moore|sherwin williams?)\b", "overseas paint brand name - not NZ-relevant", "overseas brand"),
    (r"\b(dulux|resene|wattyl|taubmans?|nippon|berger|asian paints?)\s+(accredited|certified|approved)\b", "brand-specific accreditation claim the business may not hold", None),
    (r"\binc\b", "US business-suffix ('inc', not NZ 'ltd') - scraped overseas business name, not a real local search", None),
    (r"\bsubcontractors?\b|\blooking for (a )?painters?\b|\bcontractors? looking for\b|\bpainters? needed\b|\bpainters? wanted\b", "subcontractor/trade-recruitment intent, not a customer looking to hire", None),
    (r"\bintumescent\b", "fire-rated/intumescent coatings - specialised commercial trade, not residential house painting", None),
    (r"\blimewash\b|\blime wash\b", "limewash - a specific decorative finish/niche product, not a stated service", None),
    (r"\b(shutter|gutter|trim|room|fascia|soffit)\s*painters?\b|\bpainters?\s*(of|for)\s*(a |the )?(shutter|gutter|trim)", "narrow single-component framing, not how a real customer searches for a whole-house painting company", None),
    (r"\bshutter\b", "shutters - narrow component item, not a stated service", None),
    (r"\bflooring\b", "flooring - different trade, not a stated service", None),
    (r"^the house painters$|^the painting company$|^fence spray painter$", "awkward/scraped phrasing - not a real search pattern", None),
]

# calculator/estimator must be cost-flavoured to be Price Discovery; otherwise
# it's a paint-quantity DIY calculator and gets excluded.
CALC_RE = re.compile(r"\bcalculator\b|\bestimator\b")
COST_CONTEXT_RE = re.compile(r"\bcost\b|\bprice\b|\bbudget\b|\bquote\b")

PRICE_DISCOVERY_RE = re.compile(
    r"\bhow much (does|would|will|is|should)|\bcost (to|of|for)\b|\bquote for\b|"
    r"\bprice to paint\b|painting cost|paint job cost|\baverage cost\b|"
    r"\bcost estimate\b|\bfree quote\b|\bget a quote\b|"
    r"\bcharges?\b|\bquotations?\b|\bquotes?\b|\bprices?\b|\bestimates?\b|\bpricing\b|"
    r"\bcosts?\b|\brates?\b|\bper (sq ?ft|square foot|m2|metre|hour|room)\b"
)

# stated services for this client - used to score tiers / exclude unstated scope
SERVICE_PATTERNS = {
    "Interior Painting": re.compile(r"\binterior\b|\bindoor\b|\binside\b|\binternal\b"),
    "Exterior Painting": re.compile(r"\bexterior\b|\boutdoor\b|\boutside\b|\bexternal\b"),
    "Deck Painting/Staining": re.compile(r"\bdeck(s|ing)?\b"),
    "Fence Painting/Staining": re.compile(r"\bfenc(e|es|ing)\b"),
    "House Painting (General)": re.compile(r"\bhouse\b|\bhome\b|\bresidential\b|\bpaint(er|ers|ing)?\b"),
}

# unstated adjacent services that sometimes ride along in generic "painter"
# expansions - exclude these explicitly per scope-discipline rule at the top
# of PROCESS.md (only research what the client actually stated).
UNSTATED_SERVICE_RE = re.compile(
    r"\bline (marking|striping)\b|\bspray paint(ing)? (car|metal|graffiti)|"
    r"\bgraffiti removal\b|\bwallpaper\b|\bdrywall\b|\bplasterboard\b|"
    r"\bpatio\b|\bpergola\b|\bdriveway\b(?!.*fence)|\bgutter (clean|install|repair|guard)|"
    r"\bfence install|"
    r"\bfence build(ing)?\b(?!.*(paint|stain))|\bdeck build(ing)?\b(?!.*(paint|stain))|"
    r"\bnew deck\b|\bnew fence\b|\bbuild a deck\b|\bbuild a fence\b"
)

LOCALITY_RE = re.compile(r"near me|in my area|nearby|close to me|\blocal\b")
# "business" deliberately excluded as a standalone entity signal - "painting
# business" reads as ambiguous between "hire a painting business" and "start
# a painting business" (Canterbury flagged these Manual Review; user manually
# excluded "painting business" on the Taupo run too) - company/contractor/
# services don't have that ambiguity.
ENTITY_RE = re.compile(r"\bcompan(y|ies)\b|\bcontractors?\b|\bservices?\b")
HIRE_QUALIFIER_RE = re.compile(r"\bhire\b|\bprofessional\b|\breputable\b|\bhandyman\b|\b0800\b|\btrusted\b|\bqualified\b|\blicen[sc]ed\b|\bcertified\b")
EXPLICIT_REQUEST_RE = re.compile(r"paint my (house|home|deck|fence)|get (my|your) house painted|have my house painted|hire a painter")
# "painter(s)" (the person/trade noun) is itself a valid signal per PROCESS.md's
# standing rule and the Tier C example ("house painter"). Bare "painting"
# (the gerund/activity word alone) is NOT - see the rule's own "interior
# house painting" = Excluded example - so this is deliberately narrower than
# TRADE_NOUN_RE below (which still includes "painting" for tier/service scoring).
PERSON_NOUN_RE = re.compile(r"\bpainters?\b")
TRADE_NOUN_RE = re.compile(r"\bpainters?\b|\bpainting\b")


LOCALITY_WORDS = {"near", "me", "in", "my", "area", "nearby", "close", "to", "local"}


def cluster_key(kw):
    """Close-variant clustering key (locality synonym / plural / minor
    function-word differences collapse to the same key) - module-level so
    build_step1_taupo_final.py can reuse it against a different volume
    source without duplicating the logic."""
    words = re.findall(r"[a-z]+", kw.lower())
    norm = []
    for w in words:
        if w in LOCALITY_WORDS:
            continue
        if len(w) > 3 and w.endswith("ies"):
            w = w[:-3] + "y"
        elif len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]
        norm.append(w)
    return tuple(sorted(norm))


def classify(keyword):
    kw = keyword.lower().strip()

    # "painter and decorator" is a standard combined NZ/UK trade title, not a
    # separate interior-design service - only exclude "decorator" when it
    # shows up with no "paint"/"painter" in the same keyword (i.e. a genuine
    # decorating/design-only search).
    if re.search(r"\bdecorat", kw) and not re.search(r"\bpaint", kw):
        return ("Excluded", "interior decorating service, not painting labor", "design", None)

    for pattern, reason, neg_type in HARD_EXCLUDES:
        if re.search(pattern, kw):
            return ("Excluded", reason, neg_type, pattern)

    if UNSTATED_SERVICE_RE.search(kw):
        return ("Excluded", "mixes in a service not stated for this business", None, None)

    is_calc = CALC_RE.search(kw)
    if is_calc:
        if COST_CONTEXT_RE.search(kw):
            return ("Price Discovery", "", None, None)
        return ("Excluded", "paint-quantity DIY calculator, not a cost calculator", None, None)

    if PRICE_DISCOVERY_RE.search(kw):
        return ("Price Discovery", "", None, None)

    has_locality = bool(LOCALITY_RE.search(kw))
    has_entity = bool(ENTITY_RE.search(kw))
    has_hire_qual = bool(HIRE_QUALIFIER_RE.search(kw))
    has_explicit = bool(EXPLICIT_REQUEST_RE.search(kw))
    has_trade_noun = bool(TRADE_NOUN_RE.search(kw))
    has_person_noun = bool(PERSON_NOUN_RE.search(kw))

    bof_signal = has_locality or has_entity or has_hire_qual or has_explicit or has_person_noun

    if not bof_signal:
        return ("Excluded", "no hiring/business signal - top-of-funnel/exploratory", None, None)

    # service scope
    matched_services = [name for name, pat in SERVICE_PATTERNS.items() if pat.search(kw)]
    if "House Painting (General)" in matched_services and len(matched_services) > 1:
        matched_services.remove("House Painting (General)")
    if not matched_services:
        return ("Manual Review", "has a hiring signal but doesn't clearly name a stated service", None, None)
    service = matched_services[0]
    if len(matched_services) > 1:
        service = " + ".join(matched_services)

    # tier scoring
    if has_locality and has_entity:
        tier = "A"
    elif has_trade_noun and (has_locality or has_entity):
        tier = "B"
    else:
        tier = "C"

    return ("BOF", service, tier, None)


def main():
    rows = []
    with open(IN_CSV, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append(r)

    excluded_log = []
    price_discovery = []
    bof_candidates = []
    manual_review = []

    for r in rows:
        kw = r["keyword"]
        searches = int(r["avg_monthly_searches"])
        if searches < MIN_SEARCHES:
            continue
        result = classify(kw)
        cat = result[0]
        if cat == "Excluded":
            _, reason, neg_type, pattern = result
            excluded_log.append({**r, "reason": reason, "neg_type": neg_type or "", "pattern": pattern or ""})
        elif cat == "Price Discovery":
            price_discovery.append(r)
        elif cat == "Manual Review":
            _, reason, _, _ = result
            manual_review.append({**r, "note": reason})
        elif cat == "BOF":
            _, service, tier, _ = result
            bof_candidates.append({**r, "service": service, "tier": tier})

    # ---- Priority 1 / Priority 2 split within BOF, per service ----
    # Collapse close-variant clusters first (locality synonym / plural /
    # minor function-word differences = same underlying query per the
    # PROCESS.md rubric) - only the best-volume phrasing in a cluster
    # competes for Priority 1, the rest of the cluster falls to Priority 2.
    by_service = {}
    for r in bof_candidates:
        by_service.setdefault(r["service"], []).append(r)

    # No hard cap on Priority 1 (PROCESS.md is explicit: "Beyond the floor
    # there's no hard cap - use judgment on where genuine hiring-intent
    # quality tapers off... let actual data quality decide rather than
    # forcing a number"). A prior version of this script capped each
    # service at 12 and that silently dropped genuinely high-intent,
    # high-volume keywords (e.g. "house painters near me", 880/mo) to
    # Priority 2 just because enough Tier A items came ahead of them -
    # corrected 2026-10-07 per user feedback. When unsure, include in P1
    # rather than exclude.
    tier_rank = {"A": 0, "B": 1, "C": 2}
    priority1 = []
    priority2 = []
    FLOOR = 5

    for service, items in by_service.items():
        clusters = {}
        for r in items:
            clusters.setdefault(cluster_key(r["keyword"]), []).append(r)

        representatives = []
        for members in clusters.values():
            members.sort(key=lambda r: -int(r["avg_monthly_searches"]))
            representatives.append(members[0])
            priority2.extend(members[1:])  # rest of cluster -> P2, never P1

        representatives.sort(key=lambda r: (tier_rank[r["tier"]], -int(r["avg_monthly_searches"])))

        p1 = representatives[:FLOOR]
        rest = representatives[FLOOR:]
        for r in rest:
            # Tier A/B = genuine hiring intent on its own (locality/entity/
            # hire-qualifier/explicit-request signal), goes to P1 regardless
            # of volume - no reason to hold back a real buyer-intent keyword
            # just because it's not also high-volume. Tier C (bare trade
            # noun / hiring qualifier only) is where real long-tail bloat
            # lives, so that's the only tier where the 10/mo floor alone
            # means "let it taper to P2".
            if r["tier"] in ("A", "B") or int(r["avg_monthly_searches"]) >= 20:
                p1.append(r)
            else:
                priority2.append(r)

        priority1.extend(p1)

    # ---- write categorized CSV ----
    out_rows = []
    for r in priority1:
        out_rows.append(_fmt(r, "BOF - Priority 1"))
    for r in priority2:
        out_rows.append(_fmt(r, "BOF - Priority 2"))
    for r in price_discovery:
        out_rows.append(_fmt(r, "Price Discovery"))
    for r in manual_review:
        out_rows.append(_fmt(r, "Manual Review", note=r["note"]))

    out_rows.sort(key=lambda r: (r["category"], -int(r["avg_monthly_searches"])))

    with open(OUT_CATEGORIZED, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["category", "keyword", "avg_monthly_searches", "competition", "low_top_of_page_bid", "high_top_of_page_bid", "note"])
        writer.writeheader()
        writer.writerows(out_rows)

    # ---- negative keyword list: dedupe by (neg_type or keyword) ----
    phrase_negs = {}
    exact_negs = []
    for r in excluded_log:
        if r["neg_type"]:
            phrase_negs.setdefault(r["neg_type"], []).append(r["keyword"])
        else:
            exact_negs.append(r["keyword"])

    neg_rows = []
    phrase_terms = {
        "cheap": "cheap",
        "design": "design",
        "commercial": "commercial",
        "paint price": "paint price",
        "farm": "farm fencing",
        "security": "security gate",
    }
    for neg_type, kws in phrase_negs.items():
        neg_rows.append({"negative_keyword": phrase_terms.get(neg_type, neg_type), "match_type": "Phrase", "source_count": len(kws)})
    for kw in sorted(set(exact_negs)):
        neg_rows.append({"negative_keyword": kw, "match_type": "Exact", "source_count": 1})

    with open(OUT_NEGATIVES, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["negative_keyword", "match_type", "source_count"])
        writer.writeheader()
        writer.writerows(neg_rows)

    with open(OUT_EXCLUDED_LOG, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["keyword", "avg_monthly_searches", "reason", "neg_type"])
        writer.writeheader()
        for r in excluded_log:
            writer.writerow({"keyword": r["keyword"], "avg_monthly_searches": r["avg_monthly_searches"], "reason": r["reason"], "neg_type": r["neg_type"]})

    print(f"Priority 1: {len(priority1)}")
    print(f"Priority 2: {len(priority2)}")
    print(f"Price Discovery: {len(price_discovery)}")
    print(f"Manual Review: {len(manual_review)}")
    print(f"Excluded: {len(excluded_log)}")
    print(f"Negative keyword rows (deduped): {len(neg_rows)}")
    print(f"Total classified: {len(out_rows)}")


def _fmt(r, category, note=""):
    return {
        "category": category,
        "keyword": r["keyword"],
        "avg_monthly_searches": r["avg_monthly_searches"],
        "competition": r["competition"],
        "low_top_of_page_bid": r["low_top_of_page_bid"],
        "high_top_of_page_bid": r["high_top_of_page_bid"],
        "note": note,
    }


if __name__ == "__main__":
    main()
