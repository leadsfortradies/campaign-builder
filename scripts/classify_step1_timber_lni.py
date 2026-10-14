"""
One-off: classifies the raw Keyword Planner output for Lumberland
(lumberland.co.nz) - REDO of the first Manawatu-only pass, using the scope
the user gave on 2026-10-14.

Business: timber + building supply merchant in Palmerston North that
services most of the lower North Island (Manawatu, Taranaki, Hawke's Bay,
Wairarapa, Horowhenua/Kapiti, Wellington, north to Taihape). Customers:
mostly rural/farmers, then landscapers, then DIY.

Stated scope (priority order):
  1. Pole sheds - the main focus (incl. farm/hay/implement/machinery sheds)
  2. Large clear span sheds
  3. Through post and rail fencing (+ timber fence posts/rails/palings)
  4. Timber for decking (mainly DIYers)
  5. Small part: custom-built / made-to-order (chicken coops, picnic
     tables, trellis, planter boxes, sleepouts etc.)
Excluded FOR NOW (client choice, not irrelevant - so NOT added to the
negative list): general hardware, ply/gib/plasterboard, commodity timber
and building supplies.

Idea generation geo-targeted to 4 regions: Manawatu-Whanganui (21305),
Taranaki (21311), Hawke's Bay (21304), Wellington Region (21314). Volumes
are regional aggregates, so unlike the single-district pull they actually
differentiate.
"""

import csv
import os
import re
from collections import Counter

MIN_SEARCHES = 10
IN_PATH = "output/timber-supplies-lni/merged.csv"
OUT_DIR = "output/timber-supplies-lni"
OUT_CATEGORIZED = f"{OUT_DIR}/step1_categorized.csv"
OUT_NEGATIVES = f"{OUT_DIR}/step1_negative_keywords.csv"
OUT_EXCLUDED_LOG = f"{OUT_DIR}/step1_excluded_log.csv"

LOCAL_PLACES = (
    r"palmerston north|palmy|feilding|manawatu|ashhurst|levin|horowhenua|foxton|shannon|bulls|marton|"
    r"taihape|hunterville|rangitikei|whanganui|wanganui|taranaki|new plymouth|hawera|stratford|"
    r"hawkes? bay|napier|hastings|havelock north|waipukurau|dannevirke|woodville|pahiatua|tararua|"
    r"wairarapa|masterton|carterton|greytown|featherston|martinborough|wellington|kapiti|paraparaumu|"
    r"waikanae|otaki|porirua|upper hutt|lower hutt|lower north island|central north island"
)
OTHER_PLACES = (
    r"auckland|northland|whangarei|waikato|hamilton|tauranga|bay of plenty|rotorua|taupo|gisborne|"
    r"christchurch|chch|canterbury|otago|dunedin|queenstown|invercargill|southland|nelson|blenheim|"
    r"marlborough|timaru|oamaru|west coast|australia|australian|queensland|nsw|victoria|\bus\b|\buk\b|"
    r"\busa\b|american|texas|canada|ireland|scotland|england"
)

COMPETITORS = (
    r"bunnings?|mitre ?10|\bitm\b|placemakers?|carters|\bmccoys?\b|\bmk building|ultimate building|"
    r"\bcsr\b|tractor supply|stratco|goldpine|duratuf|gubba|yardmaster|keter|gallagher|walton|eglu|"
    r"trade ?tested|farmlands|\bpgg\b|wrightson|kmart|warehouse|briscoes|hammer hardware|trade ?me|"
    r"\bamazon\b|\bebay\b|\bikea\b|\bcostco\b|gardenmaster|pinehaven|absco|total span|totalspan|"
    r"widespanshed|\bspanbuilt|\bsteelbuilt|\bkitset ?sheds?\b ?nz|\bkiwispan|\bwidespan|\bnz sheds\b|"
    r"\bgreenwood\b|\bmitek\b|\bvitex\b|\bquila\b|\bwoolshed\b ?(the)|\bthe woolshed\b|\bthe wool shed\b|"
    r"\bthe garden shed\b|\bshedmart\b|\bbarnyard\b|\bplant ?barn|\bkiwi sheds"
)

# (regex, reason, neg-group). neg-group None = not added to the account
# negative list (scope-for-now or just noise, not "irrelevant traffic").
HARD_EXCLUDES = [
    (r"\bcheap(est|er)?\b|\baffordable\b|\bbudget\b|\blow cost\b|\blow price\b|\bdiscount\b|\binexpensive\b|\bdeals?\b|\bbest price\b", "cheap/affordable/discount price-positioning - standing exclude", "cheap"),
    (r"\bfree\b", "free price-positioning term", "free"),
    (r"\blumberland\b", "Lumberland brand term - handled separately (see Manual Review)", None),
    (COMPETITORS, "competitor/retailer/marketplace brand name", "RETAIL"),
    (rf"\b({OTHER_PLACES})\b", "outside the lower North Island service area / overseas", "PLACE"),
    (r"second hand|\b2nd hand\b|\bused\b|\bseconds\b|\breclaim(ed)?\b|\breclamation\b|\brecycl(ed|ing)\b|\brepurposed\b|\brepossessed\b|\bwholesale\b|\bdismantled\b|\bpallet\b|\bsalvage", "second hand/reclaimed/wholesale - not what this business sells", "SECONDHAND"),
    (r"\bdiy\b|\bhow to\b|\bhow do\b|\bplans?\b|\bbuild (a|your|it|my)\b|\bbuilding (a|my)\b|\bmaking a\b|\bmake a\b|\bblueprints?\b|\binstructions?\b|\beasy build\b|\bez build\b|\bconstruction\b", "DIY / build-it-yourself intent", "DIY"),
    (r"\binstall(ation|ers?|ing)?\b|\bfence (builders?|contractors?|erect)|\bfencing (contractors?|installers?|company|companies)\b|\bfencers?\b|\berect", "installation - this business supplies, doesn't install", "INSTALL"),
    (r"\bspca\b|\badopt|\bresc(ue|ued)\b|\bpound\b|\banimal (control|protection|protective|welfare|rescue)\b|\bkittens?\b|\bkitties\b|\bcats?\b|\bpuppy\b|\bpuppies\b|\bboarding\b|\bcattery\b|\bgrooming\b|\bvet\b|\btravel kennel\b|\bcrate\b", "animal rescue/boarding/pet services - wrong intent", "ANIMALRESCUE"),
    (r"\bjobs?\b|\bcareers?\b|\bemployment\b|\bvacanc|\bapprentice|\bcourse\b|\btraining\b|\bsalary\b|\bhiring\b", "jobs/training", "JOBS"),
    (r"\b\d{1,2} ?x ?\d{1,2}\b|\b\d+ ?(sf|sqft)\b", "US/imperial sizing - not NZ buyer terminology", None),
    (r"\bamish\b|\bhorse barns?\b|\bbarn (yard|houses?|fence|chicken|builders?|building)|\bbarn$(?<!pole barn)|\bbarns?\b(?!.*pole)(?<!pole barn)|\bchicken barns?\b|\bsteel barn\b|\bhouses? for sale\b|\bfor rent\b|\brent(al)?\b|\bhire\b|\bpole barn (houses?|contractors?|kits?)\b|\bkits? (and|&) prices\b|\bbarn kits?\b", "US pole-barn/barn variant, house or rental search - not a materials/shed supply search", None),
    (r"\bazek\b|\bteak\b|\bdecking (lights?|rope|steps?|screws?|oil|stain)\b|\bdeck (lights?|oil|stain|paint|cleaner|builders?)\b|\bdecking builders?\b|\btrailer\b|\bsteel deck|\bback ?yard\b|\beco decking\b|\blaying\b|\bmillboard\b|\boutdure\b|\babodo\b|\bjarrah\b|\breplacement\b|\blighting\b", "decking accessory/finish/installer or non-stocked brand/species - not timber-for-decking supply", "DECKOFF"),
    (r"\banimal shelters?\b(?!.*(custom|made|timber|wooden|builder|build|for sale))|\bshelter donations?\b|\bdonat", "animal shelter = rescue/donation intent unless made-to-order phrasing", "ANIMALRESCUE"),
    (r"\bkennels? (near|nearby|in my|services?|business)|\blocal kennels?\b|\bkennels? near\b|\bovernight\b|\bluxury\b|\bgerman shepherd\b|\bgunner\b|\bper day\b|\bkennel (cost|prices?)\b|\bkennels? for sale near|\bfisher\b|\bantique\b|\bdonations?\b", "boarding kennel/off-scope - not custom-built product", "ANIMALRESCUE"),
    # scope-for-now exclusions (client decision 2026-10-14) - NOT negatives
    (r"\bplywood\b|\bply\b|\bplasterboard\b|\bplaster ?boards?\b|\bgib\b|\bgypsum\b|\bhardware\b|\bbuilding (suppl(y|ies)|materials?)\b|\bbuilders? (suppl|merchants?|materials?|yards?)\b|\bconstruction (store|suppl)|\bhome improvement\b|\bcladding\b|\bweatherboard\b|\binsulation\b|\bfasteners?\b|\bnails?\b|\bscrews?\b|\bbolts?\b|\bpaint\b|\bcement\b|\bconcrete\b|\bsand\b|\bgravel\b|\bgib\b", "general hardware / ply / gib / building supplies - excluded for now (client decision), not a negative", "SCOPE_NOW"),
    (r"\bmetal\b|\bsteel (fence|post|picket|gate|shed|garden|storage|tool)|\btin\b|\bplastic\b|\bvinyl\b|\bresin\b|\baluminium\b|\baluminum\b|\bpvc\b|\bwire\b|\belectric\b|\bchain link\b|\bgalvanised\b|\bcolou?rbond\b|\bglass\b|\bmodular\b|\bprefab\b|\bprefabricated\b|\bportable\b|\bflat ?pack\b|\bpool fenc|\bdeer\b|\bsecurity\b|\bbamboo\b|\bcomposite\b|\bmodwood\b|\bwpc\b|\bpolymer\b|\brubber\b", "wrong material/product type - not what this business supplies", "MATERIAL"),
    (r"\bumbrellas?\b|\bloungers?\b|\bchairs?\b|\bcouch(es)?\b|\bsofa\b|\bdining\b|\bhammock\b|\bswing\b|\bbbq\b|\bparasol\b|\bsun ?bed|\bcushion|\bpatio set\b|\bwicker\b|\brattan\b|\bcafe\b|\brestaurant\b|\bsong\b|\bwoods?\b(?= (table|picnic))|\bin the woods\b|\bin woods\b|\bmovie\b|\bgame\b", "off-scope furniture/other usage", "FURNITURE"),
    (r"\bpotting\b|\bbike\b|\bbicycle\b|\bfirewood\b|\bshe sheds?\b|\bmini\b|\bkit homes?\b|\bhomes?\b|\bhouses? kit\b|\bunit\b|\bgarage\b(?!.*pole)|\bcarport\b|\bhouse\b|\bapartment\b|\bliving quarters\b|\bupstairs\b|\bstory\b|\bgreenhouse\b|\bplayhouse\b|\bcubby\b|\bhorse stable\b", "building type not stated for this business", "OTHERTYPE"),
    (r"\bcost per (sq|square|foot)|\bper square (foot|feet)\b|\bsquare foot\b|\b\d+ ?x ?\d+ ?(ft|feet|foot)\b|\bsq ?ft\b|\bfeet\b|\bgarage prices\b", "US sizing/terminology", None),
    (r"\bwhat is\b|\btreatment\b|\bbranz\b|\bdifference\b|\bvs\b|\bhistory\b|\bsize\b|\bmeaning\b|\bimages?\b|\bpictures?\b|\bideas?\b|\bmodern\b|\bdesigns?\b|\bphotos?\b|\bgallery\b|\bbest\b|\bbeautiful\b|\bcute\b|\bfancy\b|\blargest\b|\bbiggest\b|\bwhere to\b|\bplanner\b|\bdesigner\b|\bconvert(ing|ed)?\b|\btoy\b|\bstyle\b", "educational/inspiration research", None),
    (r"\bveneer\b|\bturning\b|\bmaple\b|\bslabs?\b|\bmills?\b|\bthinnest\b|\byou can\b|\bceiling\b|\bblack\b|\bblue\b|\bwhite\b|\bred\b|\bpink\b|\bbrown\b|\bgrey\b|\bgray\b|\byellow\b|\bcolou?r(ed)?\b|\bcopper\b|\blocust\b|\bcattle\b|\bmagnetic\b|\bwalnut\b|\bbeech\b|\bmarine\b|\bbirch\b|\boak\b|\bexotic\b|\bfsc\b|\bcedar\b|\beucalyptus\b|\bbalau\b|\baccoya\b", "colour/species/off-scope descriptor - not a stated product search", None),
    (r"\bsleepers?\b|\bretaining\b|\blandscap|\bbeams?\b|\bjoists?\b(?!.*deck)|\blvl\b|\bdoors?\b|\bgates?\b|\broofing\b|\bpergola\b|\bborder\b|\bpower pole\b|\bflooring\b|\bfloor\b|\bhandrail\b|\bbalustrade\b|\bsiding\b|\bbatten\b(?!.*deck)", "adjacent timber/building product not a stated product", None),
]

COMMODITY_TIMBER_RE = re.compile(
    r"\btimber (suppl(y|ies|iers?)|merchants?|yards?|shops?|stores?|company|companies)\b|\blumber\b|\bmerchants?\b|"
    r"\b\d+ ?(mm|x)\b|\bh[1-5](\.\d)?\b|\bframing\b|\btreated (pine|timber|wood|lumber)\b|\bpressure treated\b|\bdressed\b|\bpine\b"
)

LOCALITY_RE = re.compile(rf"near me|in my area|nearby|nearest|closest|close to me|by me|\blocal\b|\b({LOCAL_PLACES})\b")
ENTITY_RE = re.compile(
    r"\bcompan(y|ies)\b|\bsuppliers?\b|\bsupplies\b|\bsupply\b|\bmerchants?\b|\byards?\b|\bstores?\b|\bshops?\b|"
    r"\bdistributors?\b|\bbuilders?\b|\bmanufacturers?\b|\bmakers?\b|\bdealers?\b|\bspecialists?\b"
)
BUY_RE = re.compile(r"\bfor sale\b|\bbuy\b|\bbuying\b|\border\b|\bdeliver(y|ed)?\b|\bmade to order\b|\bcustom( made| built)?\b|\bmade to measure\b|\bkit ?sets?\b")
PRICE_RE = re.compile(r"\bhow much\b|\bcosts?\b|\bprices?\b|\bpricing\b|\bquot(e|es|ation)\b|\bestimate\b|\bcalculator\b|\bper (metre|meter|m2|sheet|sqm|square)\b")

SERVICES = [
    ("Pole Sheds", re.compile(r"\bpole (\w+ )?(sheds?|barns?|buildings?|houses?|garages?)\b|\bpost frame\b|\bfarm (\w+ )?sheds?\b|\bhay (sheds?|barns?)\b|\bimplement sheds?\b|\bmachinery sheds?\b|\btractor sheds?\b|\bcalf sheds?\b|\bwool ?sheds?\b|\bshearing sheds?\b|\bstock sheds?\b")),
    ("Large Clear Span Sheds", re.compile(r"\bclear ?span\b|\bwide ?span\b|\bspan sheds?\b|\blarge sheds?\b|\bbig sheds?\b|\bbig storage sheds?\b|\blarge (storage|workshop) sheds?\b|\bworkshop sheds?\b|\bcommercial sheds?\b|\bsteel frame\b|\btimber frame sheds?\b|\bshed frame\b|\bwide sheds?\b")),
    ("Post & Rail Fencing", re.compile(r"\bpost (and|&|n) rail\b|\bpost ?& ?rail\b|\brail fenc|\bfence rails?\b|\bfence posts?\b|\bfencing posts?\b|\bfence palings?\b|\bpalings?\b|\bpailing|\bstrainer posts?\b|\bfence (post )?caps?\b|\bfencing (supplies|materials|timber)\b|\bfence (supplies|materials)\b|\bfencing\b|\bround (wooden )?posts?\b|\bhalf round\b|\btimber posts?\b|\bwood(en)? posts?\b|\btreated posts?\b|\bposts? for sale\b|\bfence stakes?\b|\bfence\b|\bposts? and rails?\b|\bcapping\b")),
    ("Decking Timber", re.compile(r"\bdecking\b|\bdeck (timber|boards?|building|framing|joists?|bearers?|materials?)\b|\bdeck\b|\bbearers?\b|\bjoists?\b|\bkwila\b")),
    ("Made to Order & Custom Builds", re.compile(r"\bchicken (coops?|houses?|runs?|pens?|huts?|hutch)|\bhen (coops?|houses?)\b|\bcoops?\b|\bchook\b|\bpoultry\b|\bpicnic (tables?|benches|bench)\b|\btrellis\b|\bplanter\b|\braised (garden )?beds?\b|\bgarden beds?\b|\bsleep ?outs?\b|\bcabins?\b|\banimal shelters?\b|\bcalf (shelter|hutch)\b|\bhot ?houses?\b|\bgarden furniture\b|\boutdoor (furniture|tables?|seating)\b|\bgarden (benches|bench|seats?)\b|\bmade to order\b|\bcustom (built|made)\b|\bdog (kennels?|houses?|runs?)\b|\bkennels?\b|\bgarden sheds?\b|\bwooden sheds?\b|\btimber sheds?\b|\bwood sheds?\b|\bhutch\b|\bchicken\b")),
    ("General Sheds", re.compile(r"\bsheds?\b")),
]

# commodity-ish "service" check: generic timber terms go out for now
MANUAL_REVIEW = [
    (r"^(tool|storage|garden|outdoor|utility|backyard|yard|small|wooden|wood|timber)? ?sheds?$|^tool sheds?$|^sheds?$|^storage sheds?$", "bare/generic shed term - highest volume in the set but mostly off-the-shelf retail intent (Mitre 10/Bunnings kitsets); confirm business wants general shed traffic"),
    (r"\bkwila\b", "kwila decking - the biggest decking term; confirm kwila is stocked and wanted"),
    (r"\bdog (kennels?|houses?|runs?)\b|\bkennels?\b", "dog kennel - custom-built animal shelter variant, large volume but not named on the site; confirm"),
    (r"\bsteel frame\b|\bshed frame\b", "steel/shed frame - clear span sheds may be steel portal frame; confirm material it supplies"),
    (r"\bhardwood\b", "hardwood decking - confirm stocked"),
    (r"\bgarden sheds?$|^garden sheds?\b", "garden shed - made-to-order item but broad retail term; confirm"),
    (r"\bplanter|\braised (garden )?beds?\b|\bgarden beds?\b|\bplanter box", "raised bed/planter box - plausible custom-built timber product but not named on the site; confirm"),
    (r"^trellis$|^timber trellis$|^wooden trellis$", "bare trellis - stated product but ~880/mo of mostly retail/DIY gardening intent; confirm"),
    (r"\bpalings?\b|\bpailing", "fence palings - residential paling fencing, not through post and rail; confirm it is wanted"),
]
MANUAL_HEADS = {
    "tool shed", "tool sheds", "garden shed", "garden sheds", "shed", "sheds", "storage shed", "wooden shed",
    "fence palings", "palings", "timber palings", "planter box", "planter boxes", "raised garden bed", "raised garden beds",
    "raised bed", "raised beds", "garden beds", "wooden planter box", "trellis", "timber trellis", "wooden trellis", "kwila decking", "kwila", "dog kennel", "dog kennels", "kennel", "kennels", "steel frame shed", "wooden garden sheds",
}

# bare head terms that still go to Priority 1
CORE_BARE_RE = re.compile(
    r"^(pole sheds?|pole barns?|pole storage sheds?|pole shed garage|pole barn garage|pole buildings?|farm sheds?|hay sheds?|"
    r"clear ?span sheds?|clear ?span|wide span sheds?|(through )?post and rail( fenc(e|ing))?|post & rail( fenc(e|ing))?|"
    r"fence posts?|fence palings?|timber fence posts?|decking timber|deck timber|timber decking|decking boards|pine decking|treated decking|"
    r"chicken coops?|chicken runs?|hen coops?|picnic tables?|wooden picnic tables?|sleepouts?|trellis|planter boxes?|raised garden beds?)$"
)

PRODUCT_VOCAB = set("""
pole shed sheds barn barns storage garage building buildings farm hay implement machinery tractor calf wool lean to leaning
clear span wide large big post posts rail rails fence fencing paling palings pailing capping cap caps half round strainer
timber wood wooden decking deck boards board pine treated untreated kwila bearers joists nz
chicken coop coops run runs pen pens hen house houses picnic table tables bench benches trellis planter box boxes raised garden bed beds
sleepout sleepouts sleep out outs cabin cabins hutch hutches for sale
""".split())


def service_for(kw):
    for name, pat in SERVICES:
        if pat.search(kw):
            return name
    return None


def classify(keyword):
    kw = re.sub(r"\s+", " ", keyword.lower().strip())

    if re.search(r"\blumberland\b", kw):
        if re.search(rf"\b({OTHER_PLACES})\b", kw):
            return ("Excluded", "Lumberland brand in another region", "PLACE")
        return ("Manual Review", "Lumberland's own brand name - normally its own brand campaign, confirm if wanted mixed in here", None)

    # lower-North-Island places always win over a coincidental OTHER_PLACES hit (e.g. "wellington")
    for pattern, reason, neg in HARD_EXCLUDES:
        if neg == "PLACE" and re.search(rf"\b({LOCAL_PLACES})\b", kw):
            continue
        if re.search(pattern, kw):
            return ("Excluded", reason, neg)

    service = service_for(kw)
    if service is None:
        return ("Excluded", "doesn't name a stated product/service", None)

    # generic commodity timber (not decking, not posts/palings) is out for now
    if service in ("Decking Timber", "General Sheds") or service is None:
        pass
    if COMMODITY_TIMBER_RE.search(kw) and service not in ("Decking Timber", "Post & Rail Fencing", "Pole Sheds"):
        return ("Excluded", "general/commodity timber - excluded for now (client decision), not a negative", "SCOPE_NOW")
    if re.search(r"\btimber\b|\bwood\b|\blumber\b", kw) and service == "General Sheds":
        pass

    for pattern, note in MANUAL_REVIEW:
        if re.search(pattern, kw):
            if PRICE_RE.search(kw):
                break
            sig = bool(LOCALITY_RE.search(kw) or ENTITY_RE.search(kw) or BUY_RE.search(kw))
            if kw in MANUAL_HEADS or sig:
                # "garden shed(s)" family with a buy/locality signal is a normal made-to-order keyword
                if service == "Made to Order & Custom Builds" and re.search(r"garden sheds?|wooden sheds?|timber sheds?|wood sheds?", kw) and sig:
                    break
                return ("Manual Review", note, None)
            if kw in MANUAL_HEADS:
                return ("Manual Review", note, None)
            if re.search(r"\bkwila\b", kw):
                return ("Manual Review", note, None)
            return ("Excluded", "variant of a Manual Review head term with no purchase/locality signal - top-of-funnel", None)

    if PRICE_RE.search(kw):
        return ("Price Discovery", service, None)

    has_loc = bool(LOCALITY_RE.search(kw))
    has_ent = bool(ENTITY_RE.search(kw))
    has_buy = bool(BUY_RE.search(kw))

    if service == "General Sheds":
        # generic shed buying - real but weak; always Priority 2
        if has_loc or has_ent or has_buy:
            return ("BOF", service, "G")
        return ("Excluded", "generic shed term with no purchase/supplier/locality signal", None)

    if has_loc and has_ent:
        return ("BOF", service, "A")
    if has_loc or has_ent or has_buy:
        return ("BOF", service, "B")
    if CORE_BARE_RE.match(kw):
        return ("BOF", service, "C-core")
    words = [w for w in re.findall(r"[a-z]+", kw) if w not in ("mm", "m", "x", "by", "ml", "cm")]
    if words and all(w in PRODUCT_VOCAB for w in words):
        return ("BOF", service, "C")
    return ("Excluded", "no hiring/business signal - top-of-funnel", None)


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

    tier_rank = {"A": 0, "B": 1, "C-core": 2, "C": 3, "G": 4}
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
            # Volume can override tier (3x+): a high-volume lower-tier member beats a low-volume higher-tier one.
            best_vol = max(members, key=lambda r: int(r["avg_monthly_searches"]))
            if best_vol is not rep and int(best_vol["avg_monthly_searches"]) >= 3 * int(rep["avg_monthly_searches"]) and best_vol["tier"] in ("C-core", "C", "B", "A"):
                rep = best_vol
            rest = [m for m in members if m is not rep]
            # No cap on Priority 1: every Tier A/B/core rep goes in. Tier C
            # (plain product/spec term) and generic sheds go to Priority 2.
            (p2 if rep["tier"] in ("C", "G") else p1).append(rep)
            for m in rest:
                # core head terms (pole shed, post and rail fencing, ...) are
                # never demoted just because a "near me" variant won the cluster
                (p1 if m["tier"] == "C-core" else p2).append(m)

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

    # Account-specific negatives: only concrete, identifiable irrelevance.
    # SCOPE_NOW terms (hardware/ply/gib/commodity) are deliberately NOT
    # negatives - the client may add them later.
    PHRASE_TERMS = {
        "cheap": ["cheap", "cheapest", "affordable", "discount", "low cost", "budget", "deals", "inexpensive"],
        "free": ["free"],
        "RETAIL": ["bunnings", "mitre 10", "mitre10", "itm", "placemakers", "carters", "mccoys", "tractor supply", "stratco", "goldpine", "duratuf", "gubba", "yardmaster", "keter", "gallagher", "walton", "trade me", "farmlands", "trade tested", "gardenmaster", "pinehaven", "absco", "total span"],
        "SECONDHAND": ["second hand", "2nd hand", "used", "reclaimed", "recycled", "repurposed", "repossessed", "wholesale", "salvage", "pallet"],
        "DIY": ["diy", "how to", "plans", "instructions", "blueprints"],
        "INSTALL": ["installation", "installers", "installer", "fencers", "fencing contractors", "fence builders"],
        "ANIMALRESCUE": ["spca", "adoption", "adopt", "rescue", "pound", "kittens", "boarding", "cattery"],
        "JOBS": ["jobs", "careers", "apprentice", "training", "course"],
        "MATERIAL": ["metal", "steel fence posts", "plastic", "vinyl", "aluminium", "aluminum", "electric fence", "chain link", "wire fencing", "galvanised", "pool fencing", "portable", "composite", "bamboo", "modwood"],
        "FURNITURE": ["umbrella", "chairs", "lounger", "couch", "dining set", "hammock"],
        "PLACE": ["auckland", "christchurch", "waikato", "hamilton", "tauranga", "otago", "canterbury", "australia", "queensland", "texas"],
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
        if k in seen or not r["neg"] or r["neg"] == "SCOPE_NOW":
            continue
        neg_rows.append({"negative_keyword": f"[{k}]", "match_type": "Exact", "source_count": 1})
    with open(OUT_NEGATIVES, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["negative_keyword", "match_type", "source_count"])
        w.writeheader()
        w.writerows(neg_rows)

    print(Counter(r["category"] for r in out), "excluded", len(excluded), "negatives", len(neg_rows))
    tot = Counter()
    for r in out:
        tot[r["category"]] += int(r["avg_monthly_searches"])
    print(dict(tot))


if __name__ == "__main__":
    main()
