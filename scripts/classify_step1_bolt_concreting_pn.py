"""
Step 1 classification for Bolt Concreting (palmerstonnorthconcreting.co.nz,
account 249-246-1698) - rebuild after the 2026-10-14 audit.

Scope (confirmed in chat 2026-10-14): concrete driveways, paths, patios,
slabs. NOT stated, so excluded: repairs, resurfacing, crack filling,
sealing/coatings, polishing, kerbing, pavers/paving, retaining walls,
decorative stamping/stencil (Manual Review), concrete supply/pumping.
Bolt disputes repair/resurfacing leads (Airtable dispute reasons).

Volume: exact-phrase historical metrics for PN City, Feilding, Rangitikei.
Floor of 10/mo applies, EXCEPT keywords that already converted in this Ads
account (proven locally, Planner just can't see them at this scale).
Exact match only - no phrase keywords are produced.
"""
import csv, re
from collections import Counter

MIN_SEARCHES = 10
D = "output/bolt-concreting-palmerston-north"
IN_PATH = f"{D}/historical_local.csv"
OUT_CATEGORIZED = f"{D}/step1_categorized.csv"
OUT_NEGATIVES = f"{D}/step1_negative_keywords.csv"
OUT_EXCLUDED_LOG = f"{D}/step1_excluded_log.csv"

LOCAL_PLACES = r"palmerston north|palmy|palmerston|feilding|fielding|manawatu|rangitikei|ashhurst|bunnythorpe"
UNCONFIRMED_TOWNS = r"sanson|marton|bulls|levin|woodville|hunterville|shannon|foxton|otaki|dannevirke|pahiatua|taihape"
OTHER_PLACES = r"auckland|christchurch|wellington|hamilton|tauranga|dunedin|nelson|napier|hastings|whanganui|wanganui|new plymouth|taupo|rotorua|invercargill|queenstown|gisborne|masterton|kapiti|waikato|canterbury|otago|australia|usa|uk|sydney|melbourne|brisbane|perth"

HARD_EXCLUDES = [
    (r"\bcheap(est)?\b|\baffordable\b|\bbudget\b|\blow cost\b|\bdiscount\b|\bbargain\b", "cheap/affordable price-positioning - standing exclude", "cheap"),
    (r"\bfree\b", "free price-positioning term", "free"),
    (rf"\b({OTHER_PLACES})\b", "outside service area", "place"),
    (r"\bbunnings\b|\bmitre ?10\b|\btrade ?me\b|\bplacemakers\b|\bcarters\b", "retailer/marketplace", "retail"),
    (r"\bfirth\b|\bhiggins\b|\bbridgeman\b|\bhynes\b|\bbullocks?\b|\bpavemasters?\b|\bpermacolou?r\b|\bjones\b|\bpukeko\b|\bconcrete doctor\b", "competitor/brand name", None),
    (r"\bdiy\b|\bhow to\b|\bhow do you\b|\bwhat to\b|\bwhat do you\b|\bkits?\b|\bplans\b|\bbuild your own\b|\bmake your own\b|\bdo it yourself\b|\bcan you\b|\bcan i\b|\bshould i\b", "DIY/how-to intent", "diy"),
    (r"\brepair(s|ing|ed)?\b|\bresurfac\w*\b|\bcrack(s|ed|ing)?\b|\bfix(es|ing|ed)?\b|\bpatch(ing)?\b|\brestor\w*\b|\brenovat\w*\b|\brefurbish\w*\b|\brejuvenat\w*\b|\bcrumbl\w*\b|\bspall\w*\b|\boverlay\w*\b|\btop ?coat\b|\bmud ?jack\w*\b|\bjacking\b|\braising\b|\blifting\b|\blevell?ing\b|\bsubsidence\b|\bsettl\w*\b|\bsinking\b|\bsunken\b|\bfiller\b|\bstain(ed|ing)?\b|\brefinish\w*\b|\btear(ing)? out\b|\bflooring\b", "repair/resurfacing/levelling - not a stated service (Bolt disputes these leads)", "repair"),
    (r"\bseal(s|ing|ed|er|ers)?\b|\bcoat(s|ing|ings)?\b|\bepoxy\b|\bresin\b|\bpaint(ing|s|ed|ers?)?\b|\bpolish\w*\b|\bgrind\w*\b|\bacid\b|\bclean\w*\b|\bpressure wash\w*\b|\bwater ?blast\w*\b|\bsandblast\w*\b|\bwash(ing)?\b", "sealing/coating/polishing/cleaning - not a stated service", "finish"),
    (r"\bpav(er|ers|ing|ement)\b|\bpaving\b|\bcobble\w*\b|\bbrick\w*\b|\bblocks?\b|\btiles?\b|\bstone\b|\bstones\b|\basphalt\b|\btar ?seal\w*\b|\bhot ?mix\b|\bbitumen\b|\bchip ?seal\w*\b|\bgravel\b|\bmetal\b|\bsand\b|\bcrushed\b|\bpebble\w*\b|\bturf\b|\bgrass\b|\bdecking\b|\bdeck\b|\bfenc\w*\b|\btimber\b|\bpergola\b|\bgrid\b|\bpermeable\b|\bpervious\b|\bporous\b", "different material/trade - not a stated service", "material"),
    (r"\bready ?mix\b|\bredi ?mix\b|\bcube price\b|\bper meter price\b|\bper metre price\b|\bcoring\b|\bwaterproof\w*\b|\btesting\b|\bformwork\b|\bstructural\b|\bvictory\b|\bpre ?mix\b|\bpremix\b|\bmixers?\b|\bmixing\b|\bconcrete mix\b|\bbags?\b|\bsuppl(y|ies|ier|iers)\b|\bdeliver\w*\b|\btrucks?\b|\bpump(ing|s|ers?)?\b|\bplacing boom\b|\bspray(ing|ed)?\b|\bhire\b.*\bmixer\b|\bwholesale\b|\bproducts?\b|\bmaterials?\b|\bcement\b|\bgrout\b|\bconcrete (bore|piles?|piling|pipes?|blocks?|panels?|tanks?|troughs?|posts?|stakes?|planters?|pots?|benches|furniture|countertops?|bench ?tops?|sinks?|baths?|fire ?pits?|pavers?|steps?|stairs?|walls?|retaining|barriers?|culverts?)\b|\bwater tanks?\b|\btanks?\b|\bpools?\b|\bretaining\b|\bwalls?\b|\bstairs?\b", "supply/pumping/precast/other concrete product - not a stated service", "product"),
    (r"\bcutting\b|\bcutters?\b|\bdrill\w*\b|\bcore ?drill\w*\b|\bsawing\b|\bdemolition\b|\bbreaking\b|\bbreakers?\b|\bremov\w*\b(?!.*replac)|\bkerb\w*\b|\bcurb\w*\b|\bedging\b|\bedge\b|\bbollards?\b|\bchannel\b|\bdrain\w*\b|\bexpansion joints?\b|\bcontrol joints?\b|\bsaw ?cut\w*\b", "cutting/demolition/kerbing/drainage - not a stated service", "other_trade"),
    (r"\bdesigns?\b|\bdesigner\b|\bideas\b|\bstyles?\b|\btypes?\b|\bcolou?rs?\b|\binspiration\b|\bpatterns?\b|\bphotos?\b|\bimages?\b|\bpictures?\b|\bexamples?\b|\boptions\b|\bpros and cons\b|\bvs\b|\bversus\b|\bcompar\w*\b|\balternatives?\b|\bdifference\b|\bbest way\b", "design/ideas/comparison research - standing exclude", "design"),
    (r"\bconsent\b|\bcouncil\b|\bpermits?\b|\bregulations?\b|\brules\b|\bcode\b|\bbuilding act\b|\bcompliance\b|\bstandard\b|\bnzs\b|\bspecifications?\b|\bthickness\b|\bdepth\b|\bcuring\b|\bcure\b|\bdry\b|\bset(ting)? time\b|\bdrying\b|\bstrength\b|\bmpa\b|\bwhat is\b|\bmeaning\b|\bdefinition\b|\bexpansion\b|\bshrinkage\b", "rules/specs/curing research - informational", "rules"),
    (r"\bjobs?\b|\bcareers?\b|\bvacanc\w*\b|\bemployment\b|\bapprentice\w*\b|\btraining\b|\bcourse\b|\bcourses\b|\bsalary\b|\bwages?\b|\bhiring\b|\bworkers? wanted\b|\blabou?rers?\b", "job-seeker / training", "jobs"),
    (r"\bfloor(s|ing)?\b.*\b(interior|kitchen|bathroom|lounge|house polished)\b|\binterior\b|\bunderfloor\b|\bsubfloor\b|\binsulat\w*\b|\bunderlay\w*\b|\bunderslab\b", "interior/subfloor - not a stated service", "interior"),
    (r"\bcalculator\b(?!.*\b(cost|price|pricing|quote)\b)|\bvolume\b|\bm3\b|\bcubic\b|\byards?\b|\bsquare feet\b|\bsq ?ft\b|\bper foot\b|\bsquare foot\b|\bsq foot\b|\binches\b|\bfeet\b|\blabor\b|\bcolor\b", "volume/materials calculator or US units - DIY/not NZ searcher", None),
    (r"\bhouse foundations? repair|\bfoundation repair\b", "foundation repair", "repair"),
    (r"\bmanual\b|\bsubcontract\w*\b|\bwholesale\b|\bwanted\b|\bfor sale\b|\bsecond hand\b|\bused\b", "not a homeowner service search", None),
]

MANUAL_REVIEW_RULES = [
    (rf"\\b({UNCONFIRMED_TOWNS})\\b", "town not confirmed as a service area yet - include only if Bolt works there"),
    (r"^concrete (cost|price|prices)( nz)?$|^concrete (price|cost) per (m2|square metre|square meter|metre|meter)( nz)?$|^concrete prices? nz$", "bare 'concrete price/cost' - often ready-mix supplier pricing rather than a laying job; confirm"),
    (r"^(custom concrete|concrete replacement)$", "ambiguous - could be decorative/precast or a repair-style replace; confirm"),
    (r"\bexposed aggregate\b|\baggregate\b", "exposed aggregate is a finish on a stated service (Bolt's site offers it) - confirm it should be targeted on its own"),
    (r"\bcolou?red concrete\b|\bcoloured\b|\bcolored\b|\bpigment\w*\b", "coloured concrete is a finish on a stated service - confirm"),
    (r"\bstamped\b|\bstencil\w*\b|\bimprint\w*\b|\bdecorative\b|\bpatterned\b", "decorative stamped/stencilled concrete - not a stated service, Bolt's site doesn't list it"),
    (r"\bsteps?\b|\bporch\b|\bveranda\b|\bverandah\b|\bcarport\b|\bgarage\b(?!.*\b(slab|floor|pad)\b)", "adjacent to a stated service but not named (steps / porch / carport) - confirm"),
    (r"\bfoundation\b|\bfoundations\b|\bribraft\b|\braft\b|\bwaffle\b|\bpiles?\b|\bpiling\b", "house foundations are bigger than a slab/pad job - confirm Bolt does new-house foundations"),
]

LOCALITY_RE = re.compile(rf"near me|in my area|nearby|close to me|\blocal\b|\b({LOCAL_PLACES})\b")
ENTITY_RE = re.compile(r"\bcompan(y|ies)\b|\bco\b|\bcontractors?\b|\bservices?\b|\bspecialists?\b|\binstallers?\b|\bbusiness(es)?\b|\bfirms?\b|\bexperts?\b|\bprofessionals?\b|\bformers?\b|\bforming\b")
TRADE_NOUN_RE = re.compile(r"\bconcreters?\b|\bconcreting\b|\bconcrete (layers?|placers?|finishers?|builders?|workers?|guys?|men|tradies|pourers?)\b|\bdriveway (builders?|layers?)\b|\bbuilders?\b|\blayers?\b|\bplacers?\b|\bfinishers?\b")
HIRE_RE = re.compile(r"\bhire\b|\bprofessional\b|\breputable\b|\bbest\b|\btop\b|\bresidential\b|\bcustom\b|\bget a\b|\bwho (does|can|lays|pours)\b|\blaying\b|\bpouring\b|\bpour\b|\blay\b|\bnew\b|\breplac\w*\b|\bre ?concret\w*\b|\binstall(ation|ed|ing)?\b|\bconstruction\b|\bbuild(ing)?\b")
PRICE_RE = re.compile(r"\bhow much\b|\bcosts?\b|\bprices?\b|\bpricing\b|\bquot(e|es|ation)\b|\bestimat(e|es|or)\b|\bcalculator\b|\bper (metre|meter|m2|sqm|square metre|square meter|m²)\b|\brates?\b|\bwhat does\b|\bhow expensive\b|\baverage\b")

SERVICES = [
    ("Driveways", re.compile(r"\bdriveways?\b|\bdrive\b|\bvehicle crossings?\b|\bcrossing\b|\bturnaround\b|\bturning bay\b|\bparking pads?\b|\bcar pads?\b")),
    ("Paths", re.compile(r"\bpaths?\b|\bpathways?\b|\bfootpaths?\b|\bwalkways?\b|\bpathers?\b")),
    ("Patios", re.compile(r"\bpatios?\b|\boutdoor (area|living|entertaining|space)\b|\bcourtyards?\b|\bbackyard\b|\bback yard\b|\bfront yard\b")),
    ("Slabs", re.compile(r"\bslabs?\b|\bpads?\b|\bfloors?\b|\bbase\b|\bsleepout\b|\bpole shed\b|\bshed\b|\bgarage\b|\bcaravan\b|\bgranny flat\b|\bhouse slab\b|\bsections?\b")),
]
GENERAL_RE = re.compile(r"\bconcret(e|er|ers|ing)\b|\bconcrete\b")
LOCALITY_WORDS = {"near", "me", "in", "my", "area", "nearby", "close", "to", "local"}


def service_for(kw):
    hits = [n for n, p in SERVICES if p.search(kw)]
    if len(hits) == 1:
        return hits[0]
    if len(hits) > 1:
        return "Concrete Contractors"
    return "Concrete Contractors" if GENERAL_RE.search(kw) else None


def cluster_key(kw):
    words = re.findall(r"[a-z]+", kw.lower())
    norm = []
    for w in words:
        if w in LOCALITY_WORDS:
            continue
        w = {"concreters": "concreter", "concreting": "concrete", "contractors": "contractor", "companies": "company",
             "driveways": "driveway", "slabs": "slab", "patios": "patio", "paths": "path", "palmy": "palmerston"}.get(w, w)
        norm.append(w)
    return tuple(sorted(set(norm))) + (("__loc__",) if any(w in LOCALITY_WORDS for w in words) else ())


def classify(kw):
    for pattern, reason, neg in HARD_EXCLUDES:
        if re.search(pattern, kw):
            return ("Excluded", reason, neg)
    service = service_for(kw)
    if service is None:
        return ("Excluded", "doesn't name a stated service", None)
    for pattern, note in MANUAL_REVIEW_RULES:
        if re.search(pattern, kw):
            return ("Manual Review", note, None)
    if PRICE_RE.search(kw):
        return ("Price Discovery", service, None)
    loc, ent, trade = bool(LOCALITY_RE.search(kw)), bool(ENTITY_RE.search(kw)), bool(TRADE_NOUN_RE.search(kw))
    if loc and (ent or trade):
        return ("BOF", service, "A")
    if loc or ent or trade or HIRE_RE.search(kw):
        return ("BOF", service, "B")
    return ("Excluded", "no hiring/business signal - bare product/service search", None)


def hist(r):
    c = float(r["ads_cost"]); n = float(r["ads_conv"]); k = int(r["ads_clicks"])
    if k == 0:
        return ""
    return f"Ads history: {k} clicks, ${c:.0f}, {n:g} conv" + (f" (${c/n:.0f}/lead)" if n else " (0 conv)")


def main():
    rows = []
    for r in csv.DictReader(open(IN_PATH)):
        proven = float(r["ads_conv"]) > 0
        if int(r["avg_monthly_searches"]) >= MIN_SEARCHES or proven:
            rows.append(r)
    out, excluded, bof = [], [], []
    for r in rows:
        kw = r["keyword"]
        cat, a, b = classify(kw)
        base = {"keyword": kw, "avg_monthly_searches": int(r["avg_monthly_searches"]), "competition": r["competition"],
                "low_top_of_page_bid": r["low_bid"], "high_top_of_page_bid": r["high_bid"]}
        h = hist(r)
        if int(r["avg_monthly_searches"]) < MIN_SEARCHES:
            h = ("Kept under the 10/mo floor: already converted in this account. " + h).strip()
        if cat == "Excluded":
            excluded.append({**base, "reason": a, "neg": b or "", "hist": h})
        elif cat == "BOF" and float(r["ads_cost"]) >= 30 and float(r["ads_conv"]) == 0:
            out.append({"category": "Manual Review", "service": a, **base,
                        "note": "Tested in this account: spent $%.0f over %s clicks with 0 leads - hiring signal is real but it didn't convert. %s" % (float(r["ads_cost"]), r["ads_clicks"], "")})
        elif cat == "BOF":
            bof.append({**base, "service": a, "tier": b, "note": h})
        elif cat == "Manual Review":
            out.append({"category": "Manual Review", "service": service_for(kw) or "", **base, "note": (a + (" | " + h if h else ""))})
        else:
            out.append({"category": cat, "service": a, **base, "note": h})

    by_service = {}
    for r in bof:
        by_service.setdefault(r["service"], []).append(r)
    for service, items in by_service.items():
        ab = [r for r in items if r["tier"] in ("A", "B")]
        for r in ab:
            out.append({"category": "BOF - Priority 1", "service": service, **{k: r[k] for k in r if k not in ("service", "tier")}})
        clusters = {}
        for r in items:
            if r["tier"] == "C":
                clusters.setdefault(cluster_key(r["keyword"]), []).append(r)
        for members in clusters.values():
            members.sort(key=lambda r: (-r["avg_monthly_searches"], len(r["keyword"])))
            for i, m in enumerate(members):
                out.append({"category": "BOF - Priority 1" if i == 0 else "BOF - Priority 2", "service": service,
                            **{k: m[k] for k in m if k not in ("service", "tier")}})

    out.sort(key=lambda r: (r["category"], r["service"], -r["avg_monthly_searches"], r["keyword"]))
    with open(OUT_CATEGORIZED, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["category", "service", "keyword", "avg_monthly_searches", "competition",
                                          "low_top_of_page_bid", "high_top_of_page_bid", "note"])
        w.writeheader(); w.writerows(out)
    with open(OUT_EXCLUDED_LOG, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["keyword", "avg_monthly_searches", "reason", "neg", "hist"])
        w.writeheader()
        for r in sorted(excluded, key=lambda r: (r["reason"], r["keyword"])):
            w.writerow({k: r[k] for k in ["keyword", "avg_monthly_searches", "reason", "neg", "hist"]})

    PHRASE = {
        "cheap": ["cheap", "cheapest", "affordable", "budget", "low cost", "discount"],
        "free": ["free"],
        "place": OTHER_PLACES.split("|"),
        "retail": ["bunnings", "mitre 10", "trade me", "placemakers"],
        "diy": ["diy", "how to", "kit", "kits", "plans", "build your own", "make your own", "do it yourself"],
        "design": ["design", "designs", "ideas", "styles", "types", "colours", "colors", "patterns", "vs", "versus", "alternatives"],
        "repair": ["repair", "repairs", "repairing", "resurfacing", "resurface", "crack", "cracks", "cracked", "fix", "fixing", "patch", "restoration", "restore", "renovation", "refurbish", "overlay", "topcoat", "levelling", "leveling", "jacking", "raising", "lifting", "subsidence", "crumbling", "spalling", "sinking", "sunken", "filler"],
        "finish": ["sealing", "sealer", "seal", "coating", "coatings", "epoxy", "resin", "painting", "paint", "polishing", "polished", "polish", "grinding", "grinder", "acid wash", "cleaning", "pressure washing", "water blasting"],
        "material": ["pavers", "paver", "paving", "cobblestone", "brick", "bricks", "blocks", "tiles", "asphalt", "tar seal", "hotmix", "gravel", "chip seal", "bitumen", "permeable", "pervious"],
        "product": ["ready mix", "readymix", "premix", "concrete mix", "concrete bags", "supplier", "suppliers", "supplies", "delivery", "delivered", "concrete truck", "concrete trucks", "concrete pump", "concrete pumping", "water tank", "water tanks", "retaining wall", "retaining walls", "precast", "concrete blocks", "concrete pipes", "concrete posts", "concrete planters"],
        "other_trade": ["concrete cutting", "concrete cutters", "core drilling", "concrete drilling", "demolition", "concrete removal", "kerbing", "curbing", "garden edging", "concrete edging", "bollards", "drainage"],
        "rules": ["consent", "council", "regulations", "building code", "curing time", "how long", "mpa", "specifications", "thickness"],
        "jobs": ["jobs", "careers", "vacancies", "employment", "apprenticeship", "training", "course", "courses", "labourer", "labourers", "salary", "wages"],
        "interior": ["underfloor", "subfloor", "insulation", "underlay"],
    }
    by_neg = {}
    for r in excluded:
        by_neg.setdefault(r["neg"], []).append(r["keyword"])
    neg_rows, covered = [], set()
    for group, terms in PHRASE.items():
        for t in terms:
            hits = [k for k in by_neg.get(group, []) if re.search(rf"\b{re.escape(t)}\b", k)]
            if hits:
                neg_rows.append({"negative_keyword": f'"{t}"', "match_type": "Phrase", "source_count": len(hits)})
                covered.update(hits)
    # one-off exact negatives only for excluded terms that carry a real hiring signal
    # but are wrong-scope (not for "no hiring signal" drops, which are just not bid on)
    for r in excluded:
        if r["keyword"] in covered or not r["neg"]:
            continue
        neg_rows.append({"negative_keyword": f"[{r['keyword']}]", "match_type": "Exact", "source_count": 1})
        covered.add(r["keyword"])
    with open(OUT_NEGATIVES, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["negative_keyword", "match_type", "source_count"])
        w.writeheader(); w.writerows(neg_rows)

    print(Counter(r["category"] for r in out), "| excluded", len(excluded), "| negatives", len(neg_rows))
    print(Counter((r["category"], r["service"]) for r in out))


if __name__ == "__main__":
    main()
