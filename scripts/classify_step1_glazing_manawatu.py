"""
One-off: classifies the raw Keyword Planner output for Altherm (aluminium
window/door joinery manufacturer) in Manawatu, per PROCESS.md Step 1's
standing rules.

Scope for this client (from chat, 2026-10-12): aluminium glazing (aluminium
windows/doors joinery), double glazing (incl. retrofit) and entrance doors.
Not stated, so excluded: repairs/maintenance (seals, latches, rollers,
handles etc.), glass/pane replacement (glazier work), uPVC/timber/steel/
fibreglass/composite products, secondary glazing, interior/shower/garage/
security doors, skylights/conservatories.

First KWR pass for this trade (no prior same-industry project to reuse).
Idea generation was geo-targeted to Palmerston North City + Manawatu District
(9117710, 9117711), four pulls (one per service + altherm.co.nz URL seed).
Historical metrics against the same geo came back floored at 10/mo for
almost everything (2067 of 2089), so volume can't rank - tier decides, same
as the Taupo/Hamilton runs.
"""

import csv
import os
import re

MIN_SEARCHES = 10
IN_PATH = "output/glazing-manawatu/merged_f10.csv"
OUT_DIR = "output/glazing-manawatu"
OUT_CATEGORIZED = f"{OUT_DIR}/step1_categorized.csv"
OUT_NEGATIVES = f"{OUT_DIR}/step1_negative_keywords.csv"
OUT_EXCLUDED_LOG = f"{OUT_DIR}/step1_excluded_log.csv"

LOCAL_PLACES = r"palmerston north|palmy|feilding|manawatu|ashhurst"
OTHER_PLACES = (
    r"auckland|west auckland|christchurch|chch|canterbury|wellington|lower hutt|"
    r"dunedin|hamilton|tauranga|tauriko|nelson|levin|wanganui|whanganui|wairarapa|"
    r"kapiti|hawkes bay|napier|new plymouth|northland|motueka|blenheim|cromwell|"
    r"waikato|australia"
)

COMPETITORS = (
    r"\bapl\b|vantage|nulook|first windows|\bfisher\b|\bsmarts?\b|smart systems|"
    r"thermawood|metro double|rylock|klima|\bhume\b|southern windows|viridian|"
    r"fairview|dawsons?|flaxpod|smartwood|frit[sz] ?jurgens?|fritsjurgen|dormakaba|"
    r"kawneer|anglian|everest|schlage|home depot|magnetite|nz ?windows|windows 2000|"
    r"parkwood|pfeiffer|warmcore|thermal ?heart|flushglaze|design windows|"
    r"central glazing|windowparts|aluminium solutions|double glazing ltd|"
    r"advanced double glazing|high performance windows|bridge windows|"
    r"architectural window systems|glass and window solutions|residential series|"
    r"\bvelux\b|877lm"
)

# (regex, reason, phrase-negative term or None for exact)
HARD_EXCLUDES = [
    (r"\bcheap(est)?\b|\baffordable\b|\bbudget\b|\blow cost\b|\bdiscount\b|\$99|\bdeals?\b", "cheap/affordable/discount price-positioning - standing exclude", "cheap"),
    (r"\bfree\b", "free price-positioning term", "free"),
    (r"\baltherm\b|\batherm\b", "Altherm brand term - handled separately (see Manual Review)", None),
    (COMPETITORS, "competitor/other brand name", "COMPETITOR"),
    (rf"\b({OTHER_PLACES})\b", "outside Manawatu service area", "PLACE"),
    (r"\bbunnings\b|\btrade me\b|\bmitre ?10\b", "retailer/marketplace - DIY/off-the-shelf buying", "RETAIL"),
    (r"second hand|\b2nd hand\b|\bused\b|\bseconds\b|\breclaimed\b|\bwholesale\b", "second hand/used/wholesale", "SECONDHAND"),
    (r"\bdiy\b|\bhome made\b|\bhow to\b|\bguide\b|\bmeasuring\b|\bcaulk\b|\bputty\b|\bclean(er|ing)?\b|\bpowder coat|\brepaint|\bfaded\b|\bsealing\b|\bseal (aluminium|around)|\bresealing\b", "DIY/maintenance intent", "DIY"),
    (r"\brepair|\bfix(er|ing)?\b|\bblown\b|\bcondensation\b|\bcracked\b|\bdefogging\b|\bbroken window\b|\blatch broken\b|\bwon t close\b|\bleaking\b", "repairs - not a stated service", "REPAIR"),
    (r"\bseals?\b|\blatch(es)?\b|\bcatch(es)?\b|\bhandles?(ets)?\b|\bhinges?\b|\brollers?\b|\btracks?\b|\bscreens?\b|\bsills?\b|\bthreshold\b|\bjamb\b|\bsweep\b|\btrim\b|\bstays\b|\blocks?\b|\bhardware\b|\bfasteners\b|\bbalance\b|\bbead(ing)?\b|\bweather strip|\bspares\b|\bparts\b|\bcloser\b|\bpelmet\b|\bpivots\b|\bpivot bar\b|\bglazing bead\b|\bsash (pivot|replacement)\b|\binsert\b(?=.*\bdoor\b)|\bdoor glass insert\b|\bglass insert\b|\bpanel replacement\b", "component/hardware/repair part - not a stated service", "PARTS"),
    (r"\b(glass|pane|panes|glazing unit) (replacement|replace)|\breplace(ment)? (glass|door glass|double glazing glass)\b|\breplacing (glass|window pane)|\bpane replacement\b|\bglass replace\b|\breglaze\b|\bwindow pane\b|\bpane of glass\b|\bglass (cost|price|prices)\b|\bglazing glass price\b|\bunit prices\b|\bglass company\b|\bglass near me\b|\bhome glass\b|\bhouse glass\b|\bglass installers?\b|\bglass install\b|\bglazier windows\b|\bglass supplier\b|\bglass door supplier\b", "glass/pane replacement or glass supply - glazier work, not a stated service", "GLASS"),
    (r"\bupvc\b|\bpvc\b|\bvinyl\b|\bplastic\b|\bacrylic\b", "uPVC/PVC/plastic product - not what this business makes", "UPVC"),
    (r"\btimber\b|\bwood(en)?\b|\boak\b|\bcedar\b|\bmahogany\b|\bhardwood\b|\bhard wood\b|\bsolid core\b", "timber/wood product - not what this business makes", "TIMBER"),
    (r"\bfib(er|re) ?glass\b|\bsteel\b|\biron\b|\bmetal\b|\bcomposite\b|\bacp\b", "steel/iron/fibreglass/composite product - not what this business makes", "MATERIAL"),
    (r"\bsecondary\b|\bmagnetic\b|\bretro glazing\b", "secondary glazing - different product, not stated", "SECONDARY"),
    (r"\btriple\b", "triple glazing - not a stated service", "TRIPLE"),
    (r"\bshower\b|\binterior\b|\binternal\b|\binside\b|\bbedroom entrance\b|\bkitchen\b|\bbathroom\b|\bcupboard\b|\bgarage\b|\bshed\b|\broller (shutter|door)|\bshutters?\b|\bsecurity\b|\bburglar\b|\bmesh\b|\bfly ?screens?\b|\bscreen door\b|\bstorm\b|\bfire\b|\bdog door\b|\bbarn\b|\bpocket\b|\bcavity slider\b|\bskylight|\broof\b|\bconservatory\b|\bcaravan\b|\bbasement\b|\bbay window\b(?=.*\b(australia)\b)|\bexternal louvres\b|\baluminum awning$|\bporch\b|\bstained\b|\bstable\b|\baccordion\b|\bconcertina\b|\bgarden window\b|\bvertical sliding\b|\bshop drawings\b|\bdwg\b", "interior/shower/garage/security/other door or window type - not a stated service", "OTHERTYPE"),
    (r"\bdesign(s|er)?\b|\bstyles?\b|\blooks\b|\bcolou?rs?\b|\bdetails?\b|\bprofiles?\b|\bextrusions?\b|\bframing\b|\bframe profile\b|\bsection\b", "design/colour/spec research - not a hiring search", "DESIGN"),
    (r"^(aluminium |aluminum )?single (glazed|glazing|pane)\b(?!.*\breplace)|^aluminum single pane|^double (glazed|glazing|pane) (window )?glass$|\bwindow glass nz\b|\bglass units?\b|\breplacement window panes\b|\bdouble glazed panes\b|\bdouble glass window panes\b", "glass product / single glazing - not a service search", "GLASS"),
    (r"\b36\b|\b36 inch\b|\bprehung\b|\bpre hung\b|\bcraftsman\b|\bhome depot\b|\b8 exterior\b|\bbipass\b", "US product sizing/terminology - not NZ buyer intent", None),
    (r"\bdifference between\b|\balternatives\b|\boptions\b|\bvs\b|\benergy efficient\b|\bsound reduction\b|\bhistoric\b|\bwhat is\b", "comparison/educational research", None),
    (r"\bcommercial\b|\bshop ?fronts?\b|\bshop front\b", "COMMERCIAL", None),  # -> Manual Review (handled below)
]

MANUAL_REVIEW_RULES = [
    (r"\bcommercial\b|\bshop ?fronts?\b", "commercial/shopfront - business mainly residential? confirm whether commercial work is wanted"),
    (r"\bfor sale\b|\bbuy(ing)?\b|\bshop\b|\bsale\b", "off-the-shelf buying phrasing - may be retail/DIY rather than made-to-measure supply + install"),
    (r"\bsash\b|\bexisting\b|\bwooden frames\b", "double glazing existing/sash/old windows - confirm business retrofits into existing (non-aluminium) frames"),
    (r"\bdoor frame replacement\b|\bwindow frame replacement\b|\bwindow and frame replacement\b|\bwindow frames?\b|\bnew window frames\b|\bwindows and frames\b|\bresidential window frames\b", "frame replacement/supply wording - could be full joinery replacement (in scope) or frame-only work"),
    (r"\bglazing company\b|\bglass glazing\b|\bglazing a window\b|^glazing windows\b|\bglazed window glass\b|\bglazing aluminum windows\b|\baluminum window glazing\b|\baluminium framed glazing\b", "\"glazing\" here could mean glass/glazier work rather than aluminium joinery"),
    (r"^doors (palmerston north|nz)$|^door entrance$|\bdoor window insert\b|\bwindow in doors\b|\bfront door window\b|\bdoors? with windows?\b|\bdoor sliding window\b|\bsliding door window\b|\bglass door window replacement\b|\bdoor installers\b", "generic \"doors\" - could be interior doors, not clearly entrance/aluminium doors"),
    (r"^fixed windows near me$", "\"fixed windows\" - could mean the fixed-pane window type or window repair"),
    (r"\breviews\b", "researching reviews of a retrofit provider - buyer intent but comparison stage"),
    (r"^aluminium palmerston north$|^aluminium nz$", "bare \"aluminium\" + place - likely joinery but could be aluminium metal supply"),
]

LOCALITY_RE = re.compile(rf"near me|in my area|nearby|close to me|\blocal\b|\b({LOCAL_PLACES})\b")
ENTITY_RE = re.compile(
    r"\bcompan(y|ies)\b|\bcontractors?\b|\bservices?\b|\bspecialists?\b|\binstallers?\b|"
    r"\bfitters?\b|\bfirms?\b|\bmanufacturers?\b|\bmakers?\b|\bmaker\b|\bfabricat(ors?|ion)\b|"
    r"\bsuppliers?\b|\bfactory\b|\bshowroom\b|\bglaziers\b|\bplaces\b"
)
HIRE_QUALIFIER_RE = re.compile(r"\bhire\b|\bprofessional\b|\breputable\b|\b0800\b|\btrusted\b|\bqualified\b|\brecommended\b")
JOB_RE = re.compile(
    r"\binstall(ation|ations|ers?|ing)?\b|\bfit(ting|ted)\b|\breplace(ment|ments)?\b|\breplacing\b|"
    r"\bretro ?fit(ting)?\b|\bretrofit(ted|ting)?\b|\bchang(e|ing) a window\b|\bchanging (exterior|front|entry) door\b|\bsupplied and fitted\b|"
    r"\bmade to order\b|\bcustom\b|\bto double glaze\b|\bdouble glaze\b|\bfitting\b"
)

PRICE_RE = re.compile(
    r"\bhow much\b|\bcosts?\b|\bprices?\b|\bpricing\b|\bquot(e|es|ation)\b|\bestimate\b|\bcalculator\b|\bper (window|m2|sqm|square)\b"
)

SERVICE_ORDER = [
    ("Entrance Doors", re.compile(r"\b(front|entrance|entry|exterior|external|outside|outdoor|outer|main|house|home) (entry )?doors?\b|\bfront entry\b|\bpivot (front |entry |entrance )?doors?\b|\bpivot door entry\b|\bdoor (front|entrance)\b|\bentrance\b|\bentry way\b|\bfront door\b|\bdoors? for front door\b|\bfront and back doors\b|\bbig pivot\b|\blarge pivot\b|\bsingle pivot\b|\bdouble pivot\b|\bframeless (glass )?pivot\b|\bglass pivot\b")),
    ("Double Glazing", re.compile(r"\bdouble\b(?!.*\bdoors?\b)(?!.*\bhung\b)|\bglaz|\bdual glaze\b|\bpane\b|\binsulated (glass|windows)\b|\bthermal(ly)? (broken|break|double)\b|\bbroken windows\b|\bthermal broken\b")),
    ("Aluminium Windows & Doors", re.compile(r"\balumin|\balu\b|\bali\b|\balloy\b|\bjoinery\b|\bwindows?\b|\bsliding\b|\bslider\b|\bbi ?fold|\bfrench (doors?|windows?)\b|\bstack(er|ing|able)\b|\bpatio doors?\b|\bdoors?\b")),
]

# Tier C (bare product head term, no hiring signal) only allowed when every
# word is a core product word - anything else (style/colour/size/inspiration
# adjective) means browsing, not buying -> excluded as top-of-funnel.
CORE_WORDS = set("""
aluminium aluminum alu ali alloy joinery window windows door doors and & glass sliding slider sliders
bifold bifolds bi fold folding french stacking stacker stackable ranch patio exterior external entrance entry
front double glazing glazed glaze gla dual retrofit retro fit thermally broken thermal break nz new zealand
pivot awning casement louvre louver hung tilt turn bay house home homes for in with frame frames outside
outdoor outer main single pane paned insulated glazier glaziers back zealand
""".split())
PRODUCT_WORD_RE = re.compile(r"\bwindows?\b|\bdoors?\b|\bjoinery\b|\bglaz|\bslider|\bbifolds?\b|\bdual glaze\b|\bpanes?\b")

# Tier C bare head terms that still go to Priority 1: the main product name
# per service/sub-product. Volume is floored at 10/mo for nearly everything
# in Manawatu so it can't pick these out - judgment call, include rather than
# exclude per PROCESS.md (Priority 1 has no cap).
TIER_C_HEAD_TERMS = {
    "aluminium windows", "aluminium doors", "aluminium joinery", "aluminium windows and doors",
    "aluminium sliding doors", "aluminium bifold doors", "aluminium stacking doors", "aluminium french doors nz",
    "aluminium ranch slider", "aluminium patio doors", "aluminium window joinery", "window joinery",
    "aluminium casement windows", "aluminium awning windows", "aluminium louvre windows", "aluminium bifold windows",
    "new aluminium windows",
    "double glazing", "double glazed windows", "double glazing retrofit", "retrofit double glazed windows",
    "double glazed doors", "double glazed sliding doors", "aluminium double glazed windows", "aluminium double glazing",
    "thermally broken aluminium windows", "thermally broken windows", "thermally broken double glazing",
    "double glazed joinery", "new double glazing", "double glazed retrofit windows",
    "front doors", "entrance doors", "exterior doors", "front entry doors", "aluminium front doors",
    "aluminium entrance doors", "pivot doors", "pivot front door", "pivot entrance door", "pivot entry door",
    "aluminium exterior doors", "front entrance doors", "double front doors", "exterior entrance doors",
    "external doors", "double glazed front doors", "double glazed entrance doors", "new front door",
}

LOCALITY_WORDS = {"near", "me", "in", "my", "area", "nearby", "close", "to", "local"}
SPELLING = {"aluminum": "aluminium", "alu": "aluminium", "ali": "aluminium", "alloy": "aluminium"}


def cluster_key(kw):
    words = re.findall(r"[a-z]+", kw.lower())
    has_locality = any(w in LOCALITY_WORDS for w in words)
    norm = []
    for w in words:
        if w in LOCALITY_WORDS:
            continue
        w = SPELLING.get(w, w)
        if len(w) > 3 and w.endswith("ies"):
            w = w[:-3] + "y"
        elif len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]
        norm.append(w)
    key = tuple(sorted(norm))
    return key + (("__has_locality__",) if has_locality else ())


def service_for(kw):
    for name, pat in SERVICE_ORDER:
        if pat.search(kw):
            return name
    return None


def classify(keyword):
    kw = keyword.lower().strip()

    if re.search(r"\baltherm\b|\batherm\b", kw):
        if re.search(rf"\b({OTHER_PLACES})\b|\bcolou?rs?\b", kw):
            return ("Excluded", "Altherm brand term for another region / colours research", None)
        return ("Manual Review", "Altherm's own brand term - usually its own brand campaign rather than mixed into BOF; confirm if wanted", None)

    for pattern, reason, neg in HARD_EXCLUDES:
        if reason == "COMMERCIAL":
            continue
        if re.search(pattern, kw):
            return ("Excluded", reason, neg)

    for pattern, note in MANUAL_REVIEW_RULES:
        if re.search(pattern, kw):
            return ("Manual Review", note, None)

    service = service_for(kw)
    if service is None:
        return ("Excluded", "doesn't name a stated service", None)

    if PRICE_RE.search(kw):
        return ("Price Discovery", service, None)

    has_locality = bool(LOCALITY_RE.search(kw))
    has_entity = bool(ENTITY_RE.search(kw))
    has_hire = bool(HIRE_QUALIFIER_RE.search(kw))
    has_job = bool(JOB_RE.search(kw))

    if re.search(r"^best\b|\bgood\b", kw) and not (has_entity or has_locality):
        return ("Excluded", "comparison/listicle research, no hiring signal", None)

    if has_locality and has_entity:
        return ("BOF", service, "A")
    if has_locality or has_entity or has_hire or has_job:
        return ("BOF", service, "B")

    words = re.findall(r"[a-z&]+", kw)
    if all(w in CORE_WORDS for w in words) and PRODUCT_WORD_RE.search(kw) and not re.fullmatch(r"(new )?windows?( nz)?|nz window|window home|windows doors|door and window|hung window|window slider|windows sliding|sliding window window|window sliding window", kw):
        return ("BOF", service, "C")
    return ("Excluded", "no hiring/business signal - style/inspiration/top-of-funnel", None)


def main():
    rows = [r for r in csv.DictReader(open(IN_PATH, newline="", encoding="utf-8")) if int(r["avg_monthly_searches"]) >= MIN_SEARCHES]

    excluded, price, manual, bof = [], [], [], []
    for r in rows:
        cat, a, b = classify(r["keyword"])
        if cat == "Excluded":
            excluded.append({**r, "reason": a, "neg": b or ""})
        elif cat == "Price Discovery":
            price.append({**r, "service": a})
        elif cat == "Manual Review":
            manual.append({**r, "note": a})
        else:
            bof.append({**r, "service": a, "tier": b})

    tier_rank = {"A": 0, "B": 1, "C": 2}
    p1, p2 = [], []
    by_service = {}
    for r in bof:
        by_service.setdefault(r["service"], []).append(r)
    for service, items in by_service.items():
        clusters = {}
        for r in items:
            clusters.setdefault(cluster_key(r["keyword"]), []).append(r)
        reps = []
        for members in clusters.values():
            members.sort(key=lambda r: (tier_rank[r["tier"]], -int(r["avg_monthly_searches"]),
                                        "aluminum" in r["keyword"], "near me" not in r["keyword"], len(r["keyword"])))
            reps.append(members[0])
            p2.extend(members[1:])
        reps.sort(key=lambda r: (tier_rank[r["tier"]], -int(r["avg_monthly_searches"])))
        # No cap on Priority 1 - every Tier A/B representative goes in. Tier C
        # bare head terms fill the floor of 5 or go in on volume (20+/mo).
        for i, r in enumerate(reps):
            if r["tier"] in ("A", "B") or i < 5 or int(r["avg_monthly_searches"]) >= 20 or r["keyword"] in TIER_C_HEAD_TERMS:
                p1.append(r)
            else:
                p2.append(r)

    def fmt(r, cat, note=""):
        return {
            "category": cat,
            "service": r.get("service", ""),
            "keyword": r["keyword"],
            "avg_monthly_searches": r["avg_monthly_searches"],
            "competition": r["competition"],
            "low_top_of_page_bid": r["low_top_of_page_bid"],
            "high_top_of_page_bid": r["high_top_of_page_bid"],
            "note": note,
        }

    out = [fmt(r, "BOF - Priority 1") for r in p1] + [fmt(r, "BOF - Priority 2") for r in p2]
    out += [fmt(r, "Price Discovery") for r in price]
    out += [fmt(r, "Manual Review", r["note"]) for r in manual]
    out.sort(key=lambda r: (r["category"], r["service"], -int(r["avg_monthly_searches"]), r["keyword"]))

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_CATEGORIZED, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)

    with open(OUT_EXCLUDED_LOG, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["keyword", "avg_monthly_searches", "reason", "neg"])
        w.writeheader()
        for r in sorted(excluded, key=lambda r: (r["reason"], r["keyword"])):
            w.writerow({k: r[k] for k in ["keyword", "avg_monthly_searches", "reason", "neg"]})

    # Negative list: phrase-match terms for recurring themes, exact for one-offs.
    PHRASE_TERMS = {
        "cheap": ["cheap", "affordable", "discount", "low cost", "budget", "deals"],
        "free": ["free"],
        "RETAIL": ["bunnings", "trade me"],
        "SECONDHAND": ["second hand", "2nd hand", "used", "seconds", "reclaimed", "wholesale"],
        "DIY": ["diy", "how to", "home made", "clean", "cleaning", "cleaner", "putty", "caulk", "powder coating", "repainting"],
        "REPAIR": ["repair", "repairs", "repairing", "fix", "fixing", "fixer", "blown", "condensation"],
        "PARTS": ["seal", "seals", "latch", "latches", "catches", "handle", "hinge", "rollers", "track", "screen", "sill", "threshold", "jamb", "hardware", "stays", "lock", "beading", "glazing bead", "spares"],
        "GLASS": ["glass replacement", "pane replacement", "window pane", "glass installers", "reglaze"],
        "UPVC": ["upvc", "pvc", "plastic", "acrylic"],
        "TIMBER": ["timber", "wood", "wooden", "oak", "cedar", "mahogany", "hardwood"],
        "MATERIAL": ["fiberglass", "fibreglass", "steel", "iron", "metal", "composite"],
        "SECONDARY": ["secondary glazing", "magnetic"],
        "TRIPLE": ["triple glazed", "triple glazing"],
        "OTHERTYPE": ["shower", "interior", "internal", "kitchen", "bathroom", "garage", "shed", "roller shutter", "security door", "mesh", "fly screen", "fire door", "dog door", "barn", "skylight", "conservatory", "caravan", "storm door"],
        "DESIGN": ["design", "designs", "colours", "colors", "profiles", "styles"],
        "PLACE": ["auckland", "christchurch", "chch", "wellington", "lower hutt", "dunedin", "hamilton", "tauranga", "nelson", "levin", "wanganui", "whanganui", "wairarapa", "kapiti", "hawkes bay", "napier", "new plymouth", "northland", "australia"],
        "COMPETITOR": ["apl", "vantage", "nulook", "first windows", "fisher", "smarts", "thermawood", "metro double glazing", "rylock", "klima", "hume", "viridian", "fairview", "flaxpod", "smartwood", "fritsjurgens", "dormakaba", "nz windows", "thermalheart", "velux", "magnetite"],
    }
    neg_rows = []
    seen = set()
    by_neg = {}
    for r in excluded:
        by_neg.setdefault(r["neg"], []).append(r["keyword"].lower())
    for group, terms in PHRASE_TERMS.items():
        kws = by_neg.get(group, [])
        for t in terms:
            n = sum(1 for k in kws if re.search(rf"\b{re.escape(t)}\b", k))
            if n:
                neg_rows.append({"negative_keyword": f'"{t}"', "match_type": "Phrase", "source_count": n})
                seen.update(k for k in kws if re.search(rf"\b{re.escape(t)}\b", k))
    for r in excluded:
        k = r["keyword"].lower()
        if k in seen:
            continue
        # skip ones excluded only for lacking a hiring signal - bare
        # style/inspiration searches aren't harmful enough to block outright
        # and many are close variants of kept head terms
        if r["reason"].startswith("no hiring") or r["reason"].startswith("doesn't name") or r["reason"].startswith("Altherm"):
            continue
        neg_rows.append({"negative_keyword": f"[{k}]", "match_type": "Exact", "source_count": 1})
        seen.add(k)

    with open(OUT_NEGATIVES, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["negative_keyword", "match_type", "source_count"])
        w.writeheader()
        w.writerows(neg_rows)

    from collections import Counter
    print(Counter(r["category"] for r in out), "excluded", len(excluded), "negatives", len(neg_rows))


if __name__ == "__main__":
    main()
