"""
One-off: classifies the raw Keyword Planner output for Lumberland
(lumberland.co.nz) in Manawatu, per PROCESS.md Step 1's standing rules.

Business: locally owned timber + building supply merchant in Palmerston
North (BuildLink Group). Mostly SELLS supplies (delivers across Manawatu),
plus an in-house builder who makes made-to-order items. Scope taken from
the live site (2026-10-12): pole sheds, through post and rail fencing,
timber (outdoor), ply and plaster, hardware / building supplies, and
made-to-order builds (garden sheds, animal shelters, trellis, sleepouts,
cabins, hot houses, outdoor furniture).

Not stated, so excluded: fence/shed *installation* (they supply, they don't
erect fences), decking composites (Modwood/Accoya), exotic/specialty
hardwood merchants, steel/metal/plastic sheds and posts, electric/wire/
chain-link/pool fencing, second-hand/reclaimed, retail competitors.

Farm/rural fencing is NOT excluded here (standing rule was for urban
fence/deck builders): post and rail + timber posts are this client's own
stated product and Manawatu is a farming region.

Idea generation was geo-targeted to Palmerston North City + Manawatu
District (9117710, 9117711). Volumes are floored at 10/mo for nearly
everything so tier decides, same as the Taupo/Hamilton/glazing runs.
"""

import csv
import os
import re
from collections import Counter

MIN_SEARCHES = 10
IN_PATH = "output/timber-supplies-manawatu/merged_f10.csv"
OUT_DIR = "output/timber-supplies-manawatu"
OUT_CATEGORIZED = f"{OUT_DIR}/step1_categorized.csv"
OUT_NEGATIVES = f"{OUT_DIR}/step1_negative_keywords.csv"
OUT_EXCLUDED_LOG = f"{OUT_DIR}/step1_excluded_log.csv"

LOCAL_PLACES = r"palmerston north|palmy|feilding|manawatu|ashhurst|levin|bulls|foxton|shannon|pahiatua|woodville|dannevirke"
OTHER_PLACES = (
    r"auckland|christchurch|chch|canterbury|wellington|lower hutt|dunedin|hamilton|"
    r"tauranga|nelson|wanganui|whanganui|wairarapa|kapiti|hawkes bay|napier|new plymouth|"
    r"northland|marton|eltham|taranaki|southland|invercargill|queenstown|rotorua|taupo|"
    r"gisborne|blenheim|timaru|oamaru|masterton|hastings|palmerston|australia|"
    r"\bus\b|american|america|uk|usa"
)
# palmerston alone would hit "palmerston north"; handled by checking LOCAL first
OTHER_PLACES = OTHER_PLACES.replace("|palmerston|", "|")

COMPETITORS = (
    r"bunnings|mitre ?10|\bitm\b|placemakers?|carters|\bmccoys?\b|\bmk building|ultimate building|"
    r"\bcsr\b|brentwood|tractor supply|stratco|goldpine|duratuf|gubba|yardmaster|keter|gallagher|"
    r"walton|eglu|plymasters|sunmica|trade ?tested|\bhirepool\b|big ?bin|farmlands|\bnzfarm|"
    r"\bpgg\b|wrightson|jb hi|kmart|warehouse|briscoes|hammer hardware|\bmitre\b|wattyl|"
    r"heritage building|bnz|trade me|trademe|\bamazon\b|\bebay\b|\bwayfair\b|\bikea\b|\bcostco\b"
)

# (regex, reason, group-tag for the negative keyword list)
HARD_EXCLUDES = [
    (r"\bcheap(est|er)?\b|\baffordable\b|\bbudget\b|\blow cost\b|\blow price\b|\bdiscount\b|\binexpensive\b|\bdeals?\b|\bbest price\b|\bcheapest\b", "cheap/affordable/discount price-positioning - standing exclude", "cheap"),
    (r"\bfree\b", "free price-positioning term", "free"),
    (r"\blumberland\b", "Lumberland brand term - handled separately (see Manual Review)", None),
    (COMPETITORS, "competitor/retailer/marketplace brand name", "RETAIL"),
    (rf"\b({OTHER_PLACES})\b", "outside Manawatu service area / overseas", "PLACE"),
    (r"second hand|\b2nd hand\b|\bused\b|\bseconds\b|\breclaim(ed)?\b|\breclamation\b|\brecycl(ed|ing)\b|\brepurposed\b|\brepossessed\b|\bwholesale\b|\bdismantled\b|\bpallet\b|\bsalvage", "second hand/reclaimed/wholesale - not what this business sells", "SECONDHAND"),
    (r"\bdiy\b|\bhow to\b|\bhow do\b|\bplans?\b|\bbuild (a|your|it)\b|\bbuilding a\b|\bblueprints?\b|\binstructions?\b|\beasy build\b|\bez build\b|\bsimple\b|\bpvc\b|\bpuller\b|\bfloor kit\b|\banchor|\bhold down\b|\bflooring kit\b", "DIY intent", "DIY"),
    (r"\binstall(ation|ers?|ing)?\b|\bfence (builders?|contractors?|erect)|\bfencing (contractors?|installers?|company|companies)\b|\bfencers?\b|\berect", "fence/other installation - this business supplies, doesn't install", "INSTALL"),
    (r"\bspca\b|\badopt|\bresc(ue|ued)\b|\bpound\b|\banimal (control|protection|protective|welfare|rescue)\b|\bkittens?\b|\bkitties\b|\bcats?\b|\bdogs?\b|\bpuppy\b|\bpets?\b|\banimal shelters? near me\b|\blocal animal shelters\b", "animal rescue/adoption - wrong intent", "ANIMALRESCUE"),
    (r"\bjobs?\b|\bcareers?\b|\bemployment\b|\bvacanc|\bapprentice|\bcourse\b|\btraining\b|\bsalary\b", "jobs/training", "JOBS"),
    (r"\bmetal\b|\bsteel\b|\biron\b|\btin\b|\bplastic\b|\bvinyl\b|\bresin\b|\bconcrete\b|\baluminium\b|\baluminum\b|\bpvc\b|\bwire\b|\belectric\b|\bchain link\b|\bgalvanised\b|\bcolorbond\b|\bcolourbond\b|\bglass\b|\bmodular\b|\bprefab\b|\bprefabricated\b|\bportable\b|\bcommercial\b|\bindustrial\b|\btemporary\b|\bpool fenc|\bdeer\b|\bsecurity\b", "wrong material/product type - not what this business supplies", "MATERIAL"),
    (r"\bcomposite\b|\bmodwood\b|\baccoya\b|\bbalau\b|\bwalnut\b|\bbeech\b|\bmarine\b|\bbirch\b|\boak\b|\bphenolic\b|\bsunmica\b|\bexotic\b|\bfsc\b|\bhardwood\b|\bcedar\b|\beucalyptus\b|\bjoinery\b|\bhandrail\b|\bfloor ?boards?\b|\bflooring\b", "specialty/exotic timber or composite - not a stated product", "SPECIALTY"),
    (r"\bcabinet\b|\bplumbing\b|\belectrical\b|\belectric\b|\bdoor stops?\b|\bfasteners?\b|\bfurniture hardware\b|\bwindow hardware\b", "unrelated hardware sub-category", "HARDWARE"),
    (r"\bumbrellas?\b|\bloungers?\b|\bchairs?\b|\bcouch(es)?\b|\bbench\b|\bseat(ing)?\b|\btables?\b|\bdining\b|\bhammock\b|\bswing\b|\bbbq\b|\bpicnic\b|\bparasol\b|\bsun ?bed|\bsofa\b|\bpatio set\b|\bcushion", "specific furniture item retail browsing - not made-to-order supply", "FURNITURE"),
    (r"\bpotting\b|\bbike\b|\bbicycle\b|\bwood store\b|\bfirewood\b|\bhay\b|\bcaravan\b|\bworkshop\b|\bgarage\b|\bshe sheds?\b|\bmini\b|\bkit homes?\b|\bhomes?\b|\bhouse kit\b|\bunit\b", "shed sub-type / building type not stated", "OTHERTYPE"),
    (r"\bcost per (sq|square|foot)|\bper square (foot|feet)\b|\bsquare foot\b|\b\d+ ?x ?\d+\b|\bsq ?ft\b|\bfeet\b|\binch(es)?\b|\bgarage prices\b", "US sizing/terminology", None),
    (r"\bdecking\b|\bdeck\b|\bcladding\b|\bsleepers?\b|\blandscap|\bretaining\b|\bbeams?\b|\bfloor\b|\bjoists?\b|\blvl\b|\bfurniture grade\b|\bdoors?\b|\bgates?\b|\broofing\b|\bpergola\b|\bborder\b|\bpoles? for sale\b(?=.*power)|\bpower pole\b", "adjacent timber product/trade not a stated product", "ADJACENT"),
    (r"\blog cabins?\b|\blog homes?\b|\bglamp|\bchalet\b|\bbarn\b(?!\s*$)(?<!pole barn)", "log cabin / other building - not stated", None),
    (r"\bwhat is\b|\btreatment\b|\bbranz\b|\bdifference\b|\bvs\b|\bhistory\b|\bsize\b|\bmeaning\b|\bimages?\b|\bpictures?\b|\bideas?\b|\bmodern\b|\bdesigns?\b|\bphotos?\b|\bgallery\b", "educational/inspiration research", None),
    (r"\bsuppliers? (us|uk|usa)\b|\bhome depot\b|\blowes\b|\bamerican hardware\b|\bwarehouse\b|\bsupply (store|company) us\b", "overseas retailer", None),
    (r"\btoy\b|\bgreenwood\b|\bmitek\b|\bplanner\b|\bdesigner\b|\bconvert(ing|ed)?\b|\bliving quarters\b|\bliveable\b|\bapartment\b|\bupstairs\b|\bstory\b|\bstyle\b|\bold pole\b|\bhouse (in|and|pole)\b|\bpole (barn|shed) house\b|\bpole shed house\b|\bhorse\b|\bcarport\b|\bpost frame\b|\bpole barn (built|builds|roof|posts|planner|style)\b|\bbuilding small\b|\bconstruction\b", "pole shed/US pole-barn variant: house conversion, living quarters, toy, planning or construction research - not a materials/shed supply search", "POLESHEDVARIANT"),
    (r"\bcement\b|\bsand\b|\bbuilding plastics\b|\bbuilding products\b|\bbuilders products\b|\bbuilders ware\b|\bbuilders pole\b|\btruss\b|\blog builders\b|\blog house\b|\bpole builders\b|\bpole suppliers\b|\bpole supply\b|\bconstruction (store|suppl)", "unrelated building product/trade or ambiguous 'pole' supply (power poles) - not a stated product", "UNRELATEDBUILD"),
    (r"\b(alternative|bmc|cob|hemp|green|natural|renewable|sustainable|wall|exterior|house|eco)\b(?=.*\bbuilding materials?\b)|\bcabots\b|\baquadeck\b|\bspecrite\b|\bforestwood\b|\bpainting\b|\bstaining\b|\bstain\b|\bshiplap\b|\bheat treated\b|\bgreen treated\b|\bwood storage kits\b", "off-topic building-material/brand/finishing variant - not a stated product search", "OFFTOPICMATERIAL"),
    (r"\bveneer\b|\bturning\b|\bmaple\b|\bslabs?\b|\bpallets? of\b|\bmills?\b|\bthinnest\b|\byou can\b|\bceiling\b|\bflat ?pack\b|\bbest\b|\bbeautiful\b|\bblack\b|\bblue\b|\bwhite\b|\bred\b|\bpink\b|\bbrown\b|\bgrey\b|\bgray\b|\byellow\b|\bcolou?r(ed)?\b|\bwicker\b|\brattan\b|\bbamboo\b|\bbrick\b|\bcopper\b|\blocust\b|\bcattle\b|\bmagnetic\b", "colour/style/species/off-scope descriptor or manufacturer - not a stated product search", "DESCRIPTOR"),
    (r"^(nearest|closest|local|the)? ?animal shelters?$|\banimal shelters?\b(?!.*(custom|made|timber|wooden|builder|build))", "animal shelter = rescue/SPCA intent unless made-to-order phrasing", "ANIMALRESCUE"),
    (r"\btool sheds?\b|\bstorage sheds?\b|\bstorage shed\b", "STORAGE", None),  # -> Manual Review below
]

MANUAL_REVIEW_RULES = [
    (r"\blumberland\b", "Lumberland's own brand name - normally its own brand campaign, confirm if wanted mixed in here"),
    (r"^(tool|storage|garden|outdoor|utility|backyard|yard|small|large|big|wooden|wood|timber)? ?sheds?$|^tool sheds?$|^sheds?$", "bare shed/tool shed term - highest volume in the dataset but mostly off-the-shelf metal/plastic retail intent; confirm business wants general shed traffic"),
    (r"\bchicken|\bhen\b|\bcoops?\b|\bpoultry\b|\bhen house\b", "chicken coop - an animal shelter variant but not named on the site; confirm"),
    (r"\bgreenhouses?\b|\bhot ?houses?\b|\bhothouse\b", "greenhouse/hot house - stated (hot houses) but searcher often wants retail/glass greenhouse; confirm"),
    (r"\boutdoor furniture\b", "outdoor furniture - stated made-to-order item but searches are mostly retail furniture browsing; confirm"),
    (r"\bkit ?sets?\b|\bkits?\b", "kitset/kit shed - this business supplies pole shed materials; confirm it wants kitset shed traffic"),
    (r"\bkwila\b", "kwila - specific outdoor hardwood, confirm it's stocked"),
    (r"\bstorage shed\b", "storage shed - generic off-the-shelf shed term; confirm"),
]

# Short head terms allowed into Manual Review without a purchase/locality
# signal; longer no-signal variants (size/count/style) are excluded.
MANUAL_HEADS = {
    "tool shed", "tool sheds", "garden shed", "shed", "storage shed", "wooden shed", "outdoor furniture",
    "chicken coop", "hen coop", "poultry coop", "chicken run", "chicken runs", "greenhouse", "kitset sheds",
    "kwila", "kwila wood", "kwila price",
}

LOCALITY_RE = re.compile(rf"near me|in my area|nearby|nearest|closest|close to me|by me|\blocal\b|\b({LOCAL_PLACES})\b")
ENTITY_RE = re.compile(
    r"\bcompan(y|ies)\b|\bsuppliers?\b|\bsupplies\b|\bsupply\b|\bmerchants?\b|\byards?\b|\bstores?\b|\bshops?\b|"
    r"\bdistributors?\b|\bbuilders?\b|\bmanufacturers?\b|\bmakers?\b|\bmills?\b|\bwarehouse\b|\bdealers?\b"
)
BUY_RE = re.compile(r"\bfor sale\b|\bbuy\b|\bbuying\b|\border\b|\bdeliver(y|ed)?\b|\bmade to order\b|\bcustom( made| built)?\b|\bcustom\b|\bmade to measure\b|\bspecialist\b")
PRICE_RE = re.compile(r"\bhow much\b|\bcosts?\b|\bprices?\b|\bpricing\b|\bquot(e|es|ation)\b|\bestimate\b|\bcalculator\b|\bper (metre|meter|m2|sheet|sqm|square)\b")

SERVICES = [
    ("Pole Sheds", re.compile(r"\bpole (\w+ )?(sheds?|barns?|buildings?|houses?)\b|\bpost frame\b|\bfarm sheds?\b|\bhay barn|\bkitset pole|\bpole shed|\bgarage pole\b")),
    ("Post & Rail Fencing", re.compile(r"\bpost (and|&|n) rail\b|\bpost ?& ?rail\b|\brail fenc|\bfence rails?\b|\bfence posts?\b|\bfencing posts?\b|\bfence palings?\b|\bpalings?\b|\bpailings?\b|\bpost and rail\b|\bstrainer posts?\b|\bfence (post )?caps?\b|\bfencing (supplies|materials|timber)\b|\bfence (supplies|materials|building supplies)\b|\bfencing\b|\bround (wooden )?posts?\b|\bhalf round\b|\btimber posts?\b|\bwood(en)? posts?\b|\btreated posts?\b|\bposts? for sale\b|\bstakes?\b|\bfence stakes?\b|\bfence\b|\btimber poles?\b|\bpoles? for sale\b|\bpole suppliers?\b|\bwood poles?\b")),
    ("Ply & Plasterboard", re.compile(r"\bply(wood)?\b|\bplaster ?boards?\b|\bgib\b|\bplaster\b|\bgypsum\b|\bboard\b")),
    ("Made to Order Sheds, Sleepouts & Cabins", re.compile(r"\bgarden sheds?\b|\bwooden sheds?\b|\bwood sheds?\b|\btimber sheds?\b|\bcustom (built |made )?(garden |wood |wooden )?(sheds?|buildings?)\b|\bsheds? (made|custom)\b|\bsleep ?outs?\b|\bcabins?\b|\banimal shelters?\b|\btrellis\b|\bhot ?houses?\b|\bgreen ?houses?\b|\boutdoor furniture\b|\bmade to order\b|\bsheds?\b|\blean to\b|\bcedar sheds?\b|\bchicken\b|\bcoop\b|\bhen\b|\bshed\b")),
    ("Timber Supply", re.compile(r"\btimbers?\b|\blumber\b|\btreated\b|\bmerchants?\b|\btimber yard\b|\bpine\b|\bh[1-5]\b|\b[0-9]+ ?x ?[0-9]+\b|\bframing\b|\bkwila\b|\bwood\b")),
    ("Building Supplies & Hardware", re.compile(r"\bbuilding (suppl(y|ies)|materials?)\b|\bbuilders? (suppl|merchants?|materials?)\b|\bconstruction (store|suppl)|\bhardware\b|\bbuilding\b|\bhome improvement\b")),
]

# anything that mentions pole shed is core; bare product terms for these
# still go to Priority 1 because the product itself is the buying intent
CORE_BARE_RE = re.compile(r"^(pole sheds?|pole barns?|pole buildings?|post and rail fenc(e|ing)|post & rail fenc(e|ing)|post and rail|fence posts?|fence palings?|palings?|timber supplier|timber merchants?|timber yards?|treated timber|building suppl(y|ies)|builders merchants?|garden sheds?|sleep ?outs?|ply(wood)?( sheets?)?|gib board|plasterboard|pole sheds nz)$")


def service_for(kw):
    for name, pat in SERVICES:
        if pat.search(kw):
            return name
    return None


def classify(keyword):
    kw = keyword.lower().strip()
    kw = re.sub(r"\s+", " ", kw)

    # Manual review overrides that must run before generic hard excludes
    if re.search(r"\blumberland\b", kw):
        if re.search(rf"\b({OTHER_PLACES})\b", kw):
            return ("Excluded", "Lumberland brand in another region", "PLACE")
        return ("Manual Review", MANUAL_REVIEW_RULES[0][1], None)

    for pattern, reason, neg in HARD_EXCLUDES:
        if neg is None and pattern.startswith(r"\btool sheds"):
            continue
        if re.search(pattern, kw):
            return ("Excluded", reason, neg)

    service = service_for(kw)
    if service is None:
        return ("Excluded", "doesn't name a stated product/service", None)

    is_pole = bool(re.search(r"\bpole (\w+ )?sheds?\b|\bpole barns?\b|\bpole buildings?\b", kw))
    if not is_pole:
        for pattern, note in MANUAL_REVIEW_RULES[1:]:
            if re.search(pattern, kw):
                sig = bool(LOCALITY_RE.search(kw) or ENTITY_RE.search(kw) or BUY_RE.search(kw))
                if PRICE_RE.search(kw):
                    break
                if sig or kw in MANUAL_HEADS:
                    return ("Manual Review", note, None)
                return ("Excluded", "variant of a Manual Review head term with no purchase/locality signal (size/count/style) - top-of-funnel", None)
    elif re.search(r"\bkit ?sets?\b|\bkits?\b", kw) and not LOCALITY_RE.search(kw):
        return ("BOF", "Pole Sheds", "B")

    if PRICE_RE.search(kw):
        return ("Price Discovery", service, None)

    has_loc = bool(LOCALITY_RE.search(kw))
    has_ent = bool(ENTITY_RE.search(kw))
    has_buy = bool(BUY_RE.search(kw))

    if has_loc and has_ent:
        return ("BOF", service, "A")
    if has_loc or has_ent or has_buy:
        return ("BOF", service, "B")
    if CORE_BARE_RE.match(kw) or service == "Pole Sheds":
        return ("BOF", service, "C-core")
    if service in ("Ply & Plasterboard", "Timber Supply", "Post & Rail Fencing"):
        # spec/size product searches ("18mm plywood", "100mm round posts") are
        # real merchant buying queries even without a locality/entity word:
        # Priority 2, never dropped. Anything with a non-product word is
        # inspiration/research and goes out.
        words = [w for w in re.findall(r"[a-z]+", kw) if w not in ("mm", "m", "x", "by", "ml", "cm", "metre", "meter", "metres")]
        if words and all(w in PRODUCT_VOCAB for w in words):
            return ("BOF", service, "C")
        return ("Excluded", "no purchase/supplier/locality signal and not a plain product/spec term - top-of-funnel", None)
    return ("Excluded", "no hiring/business signal - top-of-funnel", None)


PRODUCT_VOCAB = set("""
ply plywood board boards sheet sheets gib plasterboard plaster wood timber timbers treated untreated pine radiata
fence fencing post posts paling palings pailing pailings round half rail rails cap caps batten battens planed
structural non exterior interior laminated shuttering centring thick thin rough sawn dressed kiln dried nz
pressure tanalised acq h lumber strainer strainers timber stake stakes capping treated sheet fire rated
waterproof formwork construction cc grade lining hardiflex fibre cement gypsum stud studs
""".split())


def cluster_key(kw):
    words = re.findall(r"[a-z0-9]+", kw.lower())
    loc = {"near", "me", "in", "my", "area", "nearby", "nearest", "closest", "close", "to", "local", "by", "nz", "new", "zealand", "for", "sale", "buy", "the", "a", "of"}
    norm = []
    for w in words:
        if w in loc:
            continue
        if len(w) > 3 and w.endswith("ies"):
            w = w[:-3] + "y"
        elif len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]
        norm.append(w)
    return tuple(sorted(norm))


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
            manual.append({**r, "note": a, "service": service_for(r["keyword"].lower()) or ""})
        else:
            bof.append({**r, "service": a, "tier": b})

    tier_rank = {"A": 0, "B": 1, "C-core": 2, "C": 3}
    p1, p2 = [], []
    by_service = {}
    for r in bof:
        by_service.setdefault(r["service"], []).append(r)
    for service, items in by_service.items():
        clusters = {}
        for r in items:
            clusters.setdefault(cluster_key(r["keyword"]), []).append(r)
        for members in clusters.values():
            members.sort(key=lambda r: (tier_rank[r["tier"]], -int(r["avg_monthly_searches"]), "near me" not in r["keyword"], len(r["keyword"])))
            rep = members[0]
            # No cap on Priority 1 - every Tier A/B/core rep goes in; cluster
            # duplicates fall to Priority 2 (never dropped).
            # Tier C (plain product/spec term, no signal) is real buying
            # intent for a merchant but weakest tier -> Priority 2.
            (p2 if rep["tier"] == "C" else p1).append(rep)
            p2.extend(members[1:])

    def fmt(r, cat, note=""):
        return {
            "category": cat, "service": r.get("service", ""), "keyword": r["keyword"],
            "avg_monthly_searches": r["avg_monthly_searches"], "competition": r["competition"],
            "low_top_of_page_bid": r["low_top_of_page_bid"], "high_top_of_page_bid": r["high_top_of_page_bid"],
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

    # Account-specific negatives: only concrete, identifiable irrelevance
    # (not "no hiring signal" cutoffs). Phrase match for recurring problem
    # words, exact for one-offs.
    PHRASE_TERMS = {
        "cheap": ["cheap", "cheapest", "affordable", "discount", "low cost", "budget", "deals", "inexpensive"],
        "free": ["free"],
        "RETAIL": ["bunnings", "mitre 10", "mitre10", "itm", "placemakers", "carters", "mccoys", "tractor supply", "stratco", "goldpine", "duratuf", "gubba", "yardmaster", "keter", "gallagher", "walton", "trade me", "farmlands"],
        "SECONDHAND": ["second hand", "2nd hand", "used", "reclaimed", "recycled", "repurposed", "repossessed", "wholesale", "salvage", "pallet"],
        "DIY": ["diy", "how to", "plans", "instructions", "blueprints"],
        "INSTALL": ["installation", "installers", "installer", "fencers", "fencing contractors", "fence builders"],
        "ANIMALRESCUE": ["spca", "adoption", "adopt", "rescue", "pound", "kittens", "cats for adoption", "dogs"],
        "JOBS": ["jobs", "careers", "apprentice", "training", "course"],
        "MATERIAL": ["metal", "steel", "plastic", "vinyl", "concrete", "aluminium", "aluminum", "electric fence", "chain link", "wire fencing", "galvanised", "pool fencing", "portable"],
        "SPECIALTY": ["composite", "modwood", "accoya", "balau", "walnut", "exotic", "marine plywood", "birch", "oak", "hardwood", "cedar"],
        "FURNITURE": ["umbrella", "chairs", "lounger", "couch", "dining set", "hammock"],
        "PLACE": ["auckland", "christchurch", "wellington", "hamilton", "tauranga", "marton", "eltham", "taranaki", "australia"],
        "HARDWARE": ["cabinet hardware", "plumbing hardware", "electrical hardware"],
    }
    by_neg = {}
    for r in excluded:
        by_neg.setdefault(r["neg"], []).append(r["keyword"].lower())
    neg_rows, seen = [], set()
    for group, terms in PHRASE_TERMS.items():
        kws = by_neg.get(group, [])
        for t in terms:
            hit = [k for k in kws if re.search(rf"\b{re.escape(t)}\b", k)]
            if hit:
                neg_rows.append({"negative_keyword": f'"{t}"', "match_type": "Phrase", "source_count": len(hit)})
                seen.update(hit)
    for r in excluded:
        k = r["keyword"].lower()
        if k in seen:
            continue
        if r["reason"].startswith(("variant of", "off-topic building", "pole shed/US", "unrelated building", "colour/style", "no purchase", "no hiring", "doesn't name", "educational", "adjacent", "unrelated", "shed sub-type", "log cabin", "US sizing", "overseas retailer", "specific furniture")):
            continue
        neg_rows.append({"negative_keyword": f"[{k}]", "match_type": "Exact", "source_count": 1})
    with open(OUT_NEGATIVES, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["negative_keyword", "match_type", "source_count"])
        w.writeheader()
        w.writerows(neg_rows)

    print(Counter(r["category"] for r in out), "excluded", len(excluded), "negatives", len(neg_rows))


if __name__ == "__main__":
    main()
