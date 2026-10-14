"""
One-off: classifies the raw Keyword Planner output for the CCTV/security
camera installation + fibre splicing business in Hamilton, per PROCESS.md
Step 1's standing rules.

Scope for this client (from chat): CCTV/security camera installation and
fibre splicing/cabling only - no alarms ("doesn't do alarms yet", corrected
2026-10-09), no general ethernet/data/network cabling (fibre only, user
confirmed 2026-10-09 - he "mainly" does fibre splicing, not copper/Cat5/
Cat6/LAN cabling), no monitoring, no fire alarm, no access control, no
DIY/self-install gear - none of those were stated.

Two unrelated seed pulls (security vs cabling), each run geo-targeted to
Hamilton City (geo target constant 1011038). Both came back almost entirely
floored at the 10/mo minimum - same data-quality pattern PROCESS.md already
documents for small towns, except here it's the niche (not the city size)
that's thin. Treated the same way: 0 = no verified demand (left out already
by the >=10 filter upstream), 10 = real but can't be ranked by volume, so
tier alone decides BOF Priority 1 vs 2.
"""

import csv
import re

MIN_SEARCHES = 10

INPUTS = {
    "security": "output/security_hamilton_f10.csv",
    "cabling": "output/cabling_hamilton_f10.csv",
    "fibre_splicing": "output/fibre_splicing_hamilton_f10.csv",
}

OUT_CATEGORIZED = "output/security-cabling-hamilton/step1_categorized.csv"
OUT_NEGATIVES = "output/security-cabling-hamilton/step1_negative_keywords.csv"
OUT_EXCLUDED_LOG = "output/security-cabling-hamilton/step1_excluded_log.csv"

# ---------------------------------------------------------------------------
# Hard excludes (checked first, in order) - each is (regex, reason, neg_type)
# ---------------------------------------------------------------------------
HARD_EXCLUDES = [
    # --- price-positioning terms - standing rule, every trade, every category ---
    (r"\bcheap(est)?\b|\baffordable\b|\bbudget\b|\blow cost\b", "cheap/affordable/budget price-positioning - standing exclude", "cheap"),
    (r"\bfree\b", "free price-positioning/bait-offer term", "free"),
    # --- alarms - not a stated service (business doesn't do alarms yet, CCTV + fibre only) ---
    (r"\balarm\b|\balarms\b|\bburglar\b|\bintruder\b", "alarms - not a stated service (business doesn't do alarms yet, CCTV + fibre splicing only)", "alarm"),
    # --- general data/network/ethernet cabling - narrowed to fibre only (not fibre -> excluded) ---
    (r"^(?=.*\b(?:ethernet|cat ?5e?|cat ?6|rj ?45|lan cable|patch panel|structured cabl\w*|network cabl\w*|data cabl\w*|data wiring|data network|network data|computer network|cabl(?:e|es|ing)|wiring)\b)(?!.*\bfib(?:re|er)\b)",
     "general data/network/ethernet cabling - narrowed to fibre splicing only, not a stated service", "data cabling"),
    # --- fibre splicing EQUIPMENT shopping (other technicians/businesses buying their own
    # splicer tool) - not a customer looking to hire a splicing service ---
    (r"\bfujikura\b|\bsumitomo\b|\bcomway\b|\bcomptyco\b|\binno splicer\b|\bsignal fire\b|\bfuji ?kora\b", "named fibre-splicer equipment brand - tool-shopping, not a hiring search", "splicer equipment"),
    (r"\bsplic(er|ing machine)s?\b.*\b(for sale|price)\b|\bprice\b.*\bsplic(er|ing machine)s?\b|\bsplic(ing)? (machine|tool)s?\b|\bsplice tray\b|\bfiber optic cleaver\b|\bcleaver\b|\bfiber optic closure\b|\bribbon (cable )?splicer\b|\bcore alignment\b|\bmechanical splic", "fibre-splicing equipment/tool research, not a hiring search", "splicer equipment"),
    (r"\bsplicing (course|jobs)\b|\bfiber optic technician hiring\b|\bcertified fiber optic technician\b", "training/job-seeking query, not a customer search", None),
    (r"\bfiber ?glass\b", "fiberglass (the material) - keyword-planner misfire off \"fiber\", not fibre optic", None),
    # --- residential ISP/UFB connection requests - usually handled by the
    # telco's own installer, not a splicing contractor; excluded rather
    # than kept on an ambiguous guess ---
    (r"\bget(ting)? fib(re|er) installed\b|\binstall fib(re|er) to my (home|house)\b|\bhome fiber installation\b|\bfiber internet installation\b|\bfiber optic internet installation\b|\bhooking up fiber optic internet\b|\bconnecting fibre to the house\b", "residential ISP/UFB internet-connection request - typically the telco's own installer, not a splicing contractor", None),
    # --- competitor / brand names (security) ---
    (r"\badt\b", "ADT - named competitor brand, not a generic search", "adt"),
    (r"\btyco\b", "Tyco - named competitor brand", "tyco"),
    (r"\bchubb\b", "Chubb - named competitor brand", "chubb"),
    (r"\bjohnson controls\b", "Johnson Controls - named competitor brand", None),
    (r"\bgallagher\b", "Gallagher - named access-control/alarm brand", None),
    (r"\bhoneywell\b", "Honeywell - named alarm/access-control brand", None),
    (r"\bsiemens\b", "Siemens - named access-control brand", None),
    (r"\binner range\b", "Inner Range - named access-control brand", None),
    (r"\bdmp\b|\bdsx\b|\bnedap\b|\bkantech\b|\bgenetec\b|\bpti access\b|\bcardax\b|\bbiomax\b", "named access-control hardware brand", None),
    (r"\bbosch\b", "Bosch - named alarm hardware brand", None),
    (r"\bdsc\b(?! )|\bdsc \b", "DSC - named alarm hardware brand", None),
    (r"\bnapco\b|\bapex alarm\b|\balder\b|\bbrink alarm\b|\bconcord security\b|\bguardian alarm\b|\bprotec alarm\b|\bpremier alarm\b|\bgunnebo\b|\bmagal\b|\bqognify\b|\bavigilon\b|\binterface security\b|\bsecom\b", "named competitor/hardware brand", None),
    (r"\bpanasonic\b", "Panasonic - named camera hardware brand", None),
    (r"\b(sentinels?|tnt|cgs|pps|eyeon) security\b|\bvision security systems\b|\bsafe home security\b|\badvance(d)? (home )?security\b|\bcustom security systems\b|\bintegrated security (services|systems)\b", "reads as a specific competitor business name, not a generic search", None),
    # --- DIY camera/alarm brand names (retail self-install gear) ---
    (r"\bswann\b|\bzosi\b|\btapo\b|\btp.?link\b|\beufy|\barlo\b|\breolink\b|\bhikvision\b|\bdahua\b|\bhilook\b|\bezviz\b|\bimou\b|\bnetatmo\b|\bmi home\b|\bhiseeu\b|\bloosafe\b|\bsimpli ?safe\b|\bblink\b|\bring\b|\bnest\b|\btechage\b|\bajax\b", "consumer DIY camera/alarm brand - retail self-install product, not a stated service", "diy brand"),
    # --- fire alarm / fire protection - not stated ---
    (r"\bfire\b", "fire alarm/protection - not a stated service", "fire alarm"),
    # --- access control / door entry - not stated ---
    (r"\baccess control\b|\bdoor entry\b|\bturnstile\b|\bintercom\b|\bpanic button\b", "access control/door entry - not a stated service", "access control"),
    # --- monitoring / alarm response - business installs, doesn't monitor ---
    (r"\bmonitor", "alarm/security monitoring service - not a stated service (installation only)", "monitoring"),
    # --- DIY / self-install intent ---
    (r"\bdiy\b|\bdo it yourself\b|\bself.?install|\byourself\b|\beasy to (install|fit)\b|\beasiest .* to install\b|\beasy (install|fit)\b|\bhow to (install|set ?up|wire|mount)\b", "DIY/self-install intent", "diy"),
    (r"\bset ?up\b", "consumer gear setup/configuration query - DIY/configuration intent, not an install-trade hiring search", "setup"),
    # --- gerund+object descriptive (DIY-style task description, no hiring signal) ---
    (r"^(wiring|mounting|installing|running|pulling|connecting|connect)\b(?!.*\b(your|my)\b).*\b(a |an |the )?(cat ?5e?|cat ?6|cable|cord|cctv|camera|alarm|system|ethernet|fib(re|er)|socket|plate|conduit|lan)s?\b", "gerund + object DIY-style task description, no hiring/business signal", None),
    # --- product/manufacturer/supplier research, not an install service search ---
    (r"\bmanufacturers?\b|\bbrand\b|\bbranded\b|\bbest .* brands?\b", "product/brand research, not a hiring search", None),
    (r"\bbest place to (put|mount|install)\b", "DIY placement advice query", None),
    (r"\bcctv camera supplier\b|\bethernet cable suppliers\b", "retail product supplier, not an install service", None),
    # --- comparison/listicle/review research, no hiring signal ---
    (r"^(best|top|most|good|popular|advanced|custom|reddit|professionally installed|automated)\b(?!.*\b(compan(y|ies)|contractors?|installers?|installations?|near me|services?|suppliers?)\b)", "comparison/listicle/product-research query, no hiring signal", None),
    (r"\breddit\b", "forum/review research, not a hiring search", None),
    (r"\bcompany for sale\b|\bbusiness for sale\b", "buying/selling a business, not a customer search", None),
    (r"\bprice of adt\b|\bupgrade adt\b|\badt existing customer\b|\badt relocation\b|\badt scammers\b", "ADT account-specific/competitor query", "adt"),
    # --- wrong country / wrong infrastructure scope ---
    (r"\bnbn\b", "NBN - Australian broadband scheme, not NZ-relevant", "nbn"),
    (r"\bsubsea cable\b|\bglobal internet cable\b|\bvocus\b", "global/wholesale telco infrastructure topic, not a residential/commercial install service", None),
    # --- design / spec / enclosure product, not install labor ---
    (r"\bsystem design\b|\bwiring enclosure\b", "design/product spec, not install labor", None),
    (r"\binternet data cord\b|\bfibre optic box outside house\b|\bblown fibre\b|\bfiber optic cable underground\b", "unclear/niche technical term, not a clear hiring search", None),
    # --- commercial/business scope riding on generic expansion but genuinely fine to keep (not excluded) ---
]

LOCALITY_RE = re.compile(r"near me|in my area|nearby|close to me|\blocal\b")
ENTITY_RE = re.compile(r"\bcompan(y|ies)\b|\bcontractors?\b|\bservices?\b|\bsuppliers?\b|\binstallers?\b|\bfirms?\b|\bspecialists?\b|\btechnicians?\b")
HIRE_QUALIFIER_RE = re.compile(r"\bhire\b|\bprofessional\b|\breputable\b|\b0800\b|\btrusted\b|\bqualified\b|\blicen[sc]ed\b|\bcertified\b")
EXPLICIT_REQUEST_RE = re.compile(r"\byour house\b|\byour home\b|\bmy house\b|\bmy home\b|\bfitted\b|\bsupply and install\b")
# bare trade-noun signal - the service verb-as-noun itself counts, same as
# "house painter" (Tier C) in the painting precedent. Noun-suffix required
# ("installation"/"installer") - the bare verb "install" is an imperative,
# not a noun, so it doesn't carry the same standalone signal (same reasoning
# as "painting" verb-form not counting alone in the painting precedent).
TRADE_NOUN_RE = re.compile(r"\binstall(ation|ations|er|ers)\b|\bfitt(ing|ed|ers?)\b|\bcabl(ing|er)\b|\bwiring\b|\bsplic(ing|er|ers)\b")

CALC_RE = re.compile(r"\bcalculator\b|\bestimator\b")
COST_CONTEXT_RE = re.compile(r"\bcost\b|\bprice\b|\bbudget\b|\bquote\b")
PRICE_DISCOVERY_RE = re.compile(
    r"\bhow much (does|would|will|is|should)|\bcost (to|of|for)\b|\bquote for\b|"
    r"\baverage cost\b|\bcost estimate\b|\bfree quote\b|\bget a quote\b|"
    r"\bcharges?\b|\bquotations?\b|\bquotes?\b|\bprices?\b|\bestimates?\b|\bpricing\b|"
    r"\bcosts?\b"
)

SERVICE_PATTERNS = {
    "Security - Cameras/CCTV": re.compile(r"\bcctv\b|\bcamera|\bsurveillance\b|\bvideo (door|camera|surveillance)\b|\bdoorbell camera\b|\bnvr\b|\bdvr\b"),
    "Security - General": re.compile(r"\bsecurity\b"),
    # "splicing" on its own is specifically a fibre-optic technique (copper/
    # ethernet cabling uses punch-down/crimping, not splicing), so it counts
    # as this service even without the word "fibre"/"fiber" present.
    "Fibre Cabling/Splicing": re.compile(r"\bfib(re|er)\b|\bsplic(ing|er|ers)\b"),
}

LOCALITY_WORDS = {"near", "me", "in", "my", "area", "nearby", "close", "to", "local"}


def cluster_key(kw):
    """Collapse only genuine locality SYNONYMS into the same cluster (e.g.
    "near me" vs "in my area" vs "nearby" are the same underlying query) -
    not presence vs. absence of a locality marker at all. A keyword that
    carries a locality signal is a stronger, distinct query from the same
    phrase with no locality marker (Tier A/B vs Tier C), so dropping the
    locality words outright used to merge those into one cluster and let
    the bare/no-signal variant block the "near me" one out of Priority 1
    whenever it happened to be picked as the cluster representative."""
    words = re.findall(r"[a-z]+", kw.lower())
    has_locality = any(w in LOCALITY_WORDS for w in words)
    norm = []
    for w in words:
        if w in LOCALITY_WORDS:
            continue
        if len(w) > 3 and w.endswith("ies"):
            w = w[:-3] + "y"
        elif len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]
        norm.append(w)
    key = tuple(sorted(norm))
    if has_locality:
        key = key + ("__has_locality__",)
    return key


# bare imperative "install X" with no entity/locality/hire-qualifier/DIY-word/
# brand - genuinely ambiguous between a hiring request and a how-to search.
# Flagged for a human call rather than guessed either way.
AMBIGUOUS_IMPERATIVE_RE = re.compile(r"^install\b")


def classify(keyword):
    kw = keyword.lower().strip()

    for pattern, reason, neg_type in HARD_EXCLUDES:
        if re.search(pattern, kw):
            return ("Excluded", reason, neg_type, pattern)

    is_calc = CALC_RE.search(kw)
    if is_calc:
        if COST_CONTEXT_RE.search(kw):
            return ("Price Discovery", "", None, None)
        return ("Excluded", "non-cost calculator/estimator", None, None)

    if PRICE_DISCOVERY_RE.search(kw):
        return ("Price Discovery", "", None, None)

    has_locality = bool(LOCALITY_RE.search(kw))
    has_entity = bool(ENTITY_RE.search(kw))
    has_hire_qual = bool(HIRE_QUALIFIER_RE.search(kw))
    has_explicit = bool(EXPLICIT_REQUEST_RE.search(kw))
    has_trade_noun = bool(TRADE_NOUN_RE.search(kw))

    bof_signal = has_locality or has_entity or has_hire_qual or has_explicit or has_trade_noun

    if not bof_signal:
        if AMBIGUOUS_IMPERATIVE_RE.search(kw):
            return ("Manual Review", "bare imperative install request - no clear hiring vs DIY signal either way", None, None)
        return ("Excluded", "no hiring/business signal - top-of-funnel/exploratory", None, None)

    if re.search(r"\belectrician\b", kw):
        return ("Manual Review", "implies hiring an electrician specifically, not clearly a cabling-installer search", None, None)

    matched_services = [name for name, pat in SERVICE_PATTERNS.items() if pat.search(kw)]
    if "Security - General" in matched_services and len(matched_services) > 1:
        matched_services.remove("Security - General")
    if not matched_services:
        return ("Manual Review", "has a hiring signal but doesn't clearly name a stated service", None, None)
    if matched_services == ["Security - General"]:
        # bare "security" with no camera/CCTV word - ambiguous since alarms
        # aren't a stated service (business doesn't do alarms yet). Could be
        # a camera search phrased generically, or could be alarm-seeking
        # intent this business can't fulfil - flag rather than guess.
        return ("Manual Review", "generic \"security\" term - no camera/CCTV word, ambiguous with alarm-seeking intent (not offered)", None, None)
    service = matched_services[0]
    if len(matched_services) > 1:
        service = " + ".join(matched_services)

    # By this point the keyword has already matched a stated service
    # (alarm/cctv/camera/cabling/etc.) - that service word IS this trade's
    # equivalent of painting's "painter" trade noun, so it satisfies the
    # "trade noun" half of the painting rubric's Tier B test on its own.
    # Locality alone, entity alone, a hire-qualifier, or an explicit
    # request are each enough to clear Tier B once the service is already
    # confirmed - only a bare service-word-alone keyword (none of those)
    # falls to Tier C. Corrected 2026-10-09: originally also required a
    # literal install/fit/cable/wire word for Tier B, which wrongly sank
    # "alarm companies near me" / "burglar alarm installation near me" to
    # Tier C and let the floor/cluster mechanics bump them to Priority 2 -
    # user caught it (near me/companies/services terms are clearly P1).
    if has_locality and has_entity:
        tier = "A"
    elif has_locality or has_entity or has_hire_qual or has_explicit or has_trade_noun:
        tier = "B"
    else:
        tier = "C"

    return ("BOF", service, tier, None)


def main():
    rows_by_keyword = {}
    for source, path in INPUTS.items():
        with open(path, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                r["_source"] = source
                kw_lower = r["keyword"].lower().strip()
                # same keyword can surface from more than one seed pull
                # (e.g. "fibre cable installation" from both the cabling and
                # fibre-splicing pulls) - keep one row, the higher-volume copy.
                existing = rows_by_keyword.get(kw_lower)
                if existing is None or int(r["avg_monthly_searches"]) > int(existing["avg_monthly_searches"]):
                    rows_by_keyword[kw_lower] = r
    rows = list(rows_by_keyword.values())

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

    by_service = {}
    for r in bof_candidates:
        by_service.setdefault(r["service"], []).append(r)

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
            priority2.extend(members[1:])

        representatives.sort(key=lambda r: (tier_rank[r["tier"]], -int(r["avg_monthly_searches"])))

        p1 = representatives[:FLOOR]
        rest = representatives[FLOOR:]
        for r in rest:
            if r["tier"] in ("A", "B") or int(r["avg_monthly_searches"]) >= 20:
                p1.append(r)
            else:
                priority2.append(r)

        priority1.extend(p1)

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

    import os
    os.makedirs("output/security-cabling-hamilton", exist_ok=True)

    with open(OUT_CATEGORIZED, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["category", "keyword", "avg_monthly_searches", "competition", "low_top_of_page_bid", "high_top_of_page_bid", "note"])
        writer.writeheader()
        writer.writerows(out_rows)

    # individual DIY camera/alarm brand names worth their own phrase negative
    # (each recurs many times in the excluded log) - same convention as the
    # competitor brands below: a word that recurs broadly gets Phrase match,
    # a one-off gets Exact.
    DIY_BRAND_WORDS = [
        "swann", "zosi", "tapo", "tp-link", "tp link", "eufy", "arlo", "reolink",
        "hikvision", "dahua", "hilook", "ezviz", "imou", "netatmo", "mi home",
        "hiseeu", "loosafe", "simplisafe", "simpli safe", "blink", "ring", "nest",
        "techage", "ajax",
    ]
    # same per-word splitting for the general data/network/ethernet cabling
    # bucket (now out of scope, fibre splicing only) - these keywords share
    # several different recurring words, not one, so group by whichever
    # specific word matched rather than dumping the whole phrase as a
    # one-off exact negative.
    NON_FIBRE_CABLING_WORDS = [
        "ethernet", "cat 5", "cat5", "cat 6", "cat6", "rj45", "rj 45",
        "lan cable", "patch panel", "structured cabling", "structured cabl",
        "network cabling", "network cabl", "data cabling", "data cabl",
        "data wiring", "data network", "network data", "computer network",
        "cabling", "cable", "wiring",
    ]

    phrase_negs = {}
    exact_negs = []
    for r in excluded_log:
        if r["neg_type"] == "diy brand":
            kw_lower = r["keyword"].lower()
            matched_brand = next((b for b in DIY_BRAND_WORDS if b in kw_lower), None)
            if matched_brand:
                phrase_negs.setdefault(matched_brand, []).append(r["keyword"])
            else:
                exact_negs.append(r["keyword"])
        elif r["neg_type"] == "data cabling":
            kw_lower = r["keyword"].lower()
            matched_word = next((w for w in NON_FIBRE_CABLING_WORDS if w in kw_lower), None)
            if matched_word:
                phrase_negs.setdefault(matched_word, []).append(r["keyword"])
            else:
                exact_negs.append(r["keyword"])
        elif r["neg_type"]:
            phrase_negs.setdefault(r["neg_type"], []).append(r["keyword"])
        else:
            exact_negs.append(r["keyword"])

    neg_rows = []
    phrase_terms = {
        "adt": "adt",
        "tyco": "tyco",
        "chubb": "chubb",
        "fire alarm": "fire",
        "alarm": "alarm",
        "splicer equipment": "splicer",
        "cheap": "cheap",
        "free": "free",
        "access control": "access control",
        "monitoring": "monitoring",
        "diy": "diy",
        "setup": "set up",
        "nbn": "nbn",
    }
    for neg_type, kws in phrase_negs.items():
        term = phrase_terms.get(neg_type, neg_type)
        neg_rows.append({"negative_keyword": term, "match_type": "Phrase", "source_count": len(kws)})
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
