"""
One-off: classifies the raw Keyword Planner output for an electrician in
Christchurch, per PROCESS.md Step 1's standing rules.

Stated scope (from chat, 2026-10-14): electrical repairs and servicing,
small scale renovations (electrical work for small renos), switchboard
upgrades. Nothing else - no commercial/industrial, no gates/garage doors,
no generators, no hot water/heating/aircon, no fans, no alarms/fire, no EV
chargers, no solar - none of those were stated.

Christchurch is a single big metro, so this pull was run geo-targeted to
Christchurch City (9117696) with a tight, service-scoped seed list. The
volume data is still mostly floored at 10/mo outside a handful of head
terms, so tier does most of the ranking work.
"""

import csv
import os
import re

MIN_SEARCHES = 10
INPUTS = ["output/electrical-christchurch/raw_core.csv", "output/electrical-christchurch/raw_switch_reno.csv"]
OUT_DIR = "output/electrical-christchurch"
OUT_CATEGORIZED = f"{OUT_DIR}/step1_categorized.csv"
OUT_NEGATIVES = f"{OUT_DIR}/step1_negative_keywords.csv"
OUT_EXCLUDED_LOG = f"{OUT_DIR}/step1_excluded_log.csv"

SERVICE_WORDS = r"switchboard|switch board|fuse ?(box|board|panel)|meter board|rewir\w*|re wir\w*|repair\w*|servicing|fault|power ?point|renovation"

HARD_EXCLUDES = [
    # price-positioning - standing rule, every trade
    (r"\bcheap(est)?\b|\baffordable\b|\bbudget\b|\blow cost\b|\breasonabl[ey]\b", "cheap/affordable/reasonable price-positioning - standing exclude", "cheap"),
    (r"\bfree\b", "free price-positioning term", "free"),
    # misspellings - close variants already covered by the real keyword
    (r"electrictrician|electriciansnear|electricianwork|electricianu|\belectrician u\b|\belectrician day\b|electrician 101", "misspelling/junk - close variant already covered", None),
    # job-seeking / training / career
    (r"\bbecoming\b|\blevel [23]\b|\bjourneyman\b|\bapprentice|\bcourse|\bjobs?\b|\bwireman\b|\belectrician levels\b|\bfor dummies\b|\bmagazine\b|\bworker\b|\belectrician board\b|\bhiring\b|\bsalary\b", "job-seeking/training query, not a customer search", "jobs"),
    (r"\breddit\b|\byellow pages\b|\bangi\b|\bfilipino\b|\bnfpa\w*\b|\beicr\b|\bniceic\b|\bllc\b|\bamerican\b", "forum/directory/wrong-country (US/UK) term", None),
    # wrong scope: commercial / industrial / HV / mechanical
    (r"\bcommercial\b|\bindustrial\b|\bhigh voltage\b|\bhv\b|\bsubstation|\bswitchgear\b|\btransformer\b|\bsf6\b|\bplc\b|\binstrumentation\b|\blineman\b|\bconstruction\b|\bmechanical\b|\bm ?& ?e\b|\bmotors?\b|\bmachine\b|\bautomation\b|\bcrane\b|\bheat trace\b|\bpower plant\b|\bpower lines?\b|\bcable feeder\b|\bhigh voltage\b|\blow voltage\b|\bsubcontract\w*\b|\bsub contract\w*\b|\bcontract electrical\b|\btender\b|\bmaintenance electrician\b|\bpreventive\b|\bpreventative\b|\bpower contractors\b|\bbuilding electrician\b|\bgovt\b|\blarge\b|\bbiggest\b|\bbig (electric\w*|electrician)\b|\bmajor\b", "commercial/industrial/HV/trade-contract scope - not a stated service", "commercial"),
    # unstated adjacent trades/products
    (r"\bgates?\b|\bgarage door|\broller door|\bgenerators?\b|\binverter\b|\bhot tub\b|\bhot water\b|\bwater heater\b|\bgas heater\b|\bheater\b|\bheating\b|\bhvac\b|\baircon\b|\bair con\b|\bmitsubishi\b|\brheem\b|\bshower\b|\bfans?\b|\bcooker\b|\boven\b|\bchandelier\b|\bsolar\b|\bev charg\w*\b|\balarm\b|\bfire\b|\bplumb\w*\b|\blandscape\b|\boutdoor lighting\b|\bsprinkler\b|\bsmart home\b|\bheat pump\b|\bbath panel\b|\bwire coating\b|\bgas\b|\bmeter repair\b|\belectric meter\b|\bpower inverter\b|\bearthing\b|\bgarage contractor\b|\bdomestic installer\b|\bpower pole|\btemporary\b|\bunderground\b|\bpower testing\b|\bpole testing\b|\bpat testing\b|\bemergency power\b|\bcable repair\b", "not a stated service (adjacent trade/product)", "adjacent"),
    (r"\bpower ?point\b.*\b(presentation|theme|mac|microsoft|ms|ppt)\b|\b(install|download|new)\b.*\b(ppt|ms powerpoint|microsoft powerpoint|powerpoint (presentation|theme|on mac))\b|\bppt\b|\bnew powerpoint\b|\bnew ppt\b|\bpowerpoint installer\b", "Microsoft PowerPoint software - keyword-planner misfire off 'power point'", "powerpoint software"),
    (r"\bmobile home\b|\ba ?1\b|\bpowerco\b|\band maintenance$|\bmaintenance system\b|\btechnician maintenance\b|\bmaintenance electrical technician\b|\belectrical electrician\b|\bwired electrical\b|\bthree phase\b|\bphase\b", "junk/US-style/utility-company/non-service phrasing", None),
    # wholesale / retail / products
    (r"\bwholesale\b|\bsuppliers?\b|\bmanufacturers?\b|\bbuilders\b|\bpanel builders\b|\bproducts?\b", "retail/wholesale/manufacturing - not a hiring search", None),
    # DIY intent
    (r"\bdiy\b|\bdo it yourself\b|\bhow to\b|\bself.?install\b", "DIY intent", "diy"),
    (r"\b(re ?wir\w*|wiring)\b (a|an|the)?\s?(plug|light|fixture|fitting|switch|socket|fuse|room)\b|\bre ?wire (a|your)? ?(plug|light|fuse)\b|\brewiring a\b$", "DIY-style plug/fitting rewire task", "diy"),
    (r"^(fix|replace|replacing|change|changing|repair|replace a|fixing)\b.*\b(fuse|breaker|outlet|plug|switch|dimmer|wire|socket|gfci|short circuit|loose|light)\b(?!.*\b(near me|company|companies|service|services|contractor|electrician)\b)", "DIY-style fix/replace task on a small component, no hiring signal", "diy"),
    (r"^(fix|fixing)\b(?!.*\b(near me|company|services?|electrician)\b)", "DIY-style fix task, no hiring signal", "diy"),
    # US-style terms
    (r"\bgfci\b|\boutlets?\b(?!.*\bnear me\b)|\bbreaker box\b|\bbreaker panel\b|\bservice panel\b|\b\d{3} amp\b|\bsub ?panel\b|\bservice entrance\b|\baluminum\b|\bsocal\b|\bstate ?wide\b", "US-style electrical terminology/product - not NZ search phrasing", "us terms"),
    # other places
    (r"\bnorth shore\b|\beastern suburbs\b|\bnelson\b|\bboston\b|\bbristol\b|\bphoenix\b|\bkingston\b|\bwest coast\b|\beast coast\b|\bnorth east\b|\bnorth west\b|\bsouth east\b|\bsoutheastern\b|\bcounty\b|\bvalley\b|\bbay\b|\briverside\b|\blake\b|\bpacific\b|\bcoast\b", "other place / US-style regional business name", None),
    # comparisons / directories with no hiring signal handled later
    (r"\bcompany for sale\b|\bplaces near me\b|\bbusinesses near me\b", "directory/business-listing search", None),
    (r"\bestimating\b|\belectrician charges per hour\b|\blabour charges\b", "estimating software/labour-rate research", None),
]

# Tokens that are expected in a legitimate generic keyword. Anything outside
# this vocabulary reads as a competitor/company name or an off-topic term and
# is excluded (and logged so it can be eyeballed).
GENERIC = set("""
electrician electricians electrical electric electrics electrically sparky sparkies sparks
service services servicing repair repairs repairing maintenance fault finding fix
near me nearby near by close to around area my in the a an for of and or on at your
local emergency urgent same day 24 7 247 24hr 24x7 hour hours hrs hr after out call callout
licensed licenced registered qualified professional reputable trusted best top good rated highly
recommended reliable independent private find need needs looking i get contact
company companies contractor contractors firm firms specialist specialists technician tech
home house household residential domestic new old
switchboard switchboards switch board boards fuse fuses box boards panel panels meter upgrade upgrades upgrading
update replace replacement replacing change installation installations install installer installers
rewire rewiring re wire wiring wired rewired renovation renovations reno remodel
power point points powerpoint powerpoints socket sockets plug plugs lighting light lights
cost costs price prices pricing quote quotes quotation estimate how much does charge charges per
inspection testing test available now weekend sunday handyman handy
wiring cable cables circuit breaker breakers rcd
full whole entire home's complete with
electrician's skilled master level
certified nearest any us highest 24hrs inspectors inspector contracting general ltd limited fixer broken circuits
average typical approximate bed bedroom bedrooms three two 2 3 1000 sq ft redo room older houses damaged wall urban housing small
""".split())

LOCALITY_RE = re.compile(r"near me|in my area|nearby|close to me|\blocal\b|\bnear by\b|\baround me\b|\bin the area\b|\bclose by\b|\bnearest\b")
ENTITY_RE = re.compile(r"\bcompan(y|ies)\b|\bcontractors?\b|\bservices?\b|\bfirms?\b|\bspecialists?\b|\btechnicians?\b|\belectricians?\b|\bsparky\b|\bsparkies\b")
HIRE_QUALIFIER_RE = re.compile(r"\bhire\b|\bprofessional\b|\breputable\b|\b0800\b|\btrusted\b|\bqualified\b|\blicen[sc]ed\b|\bregistered\b|\bemergency\b|\bsame day\b|\b24\b|\b24hr\b|\bafter hours\b|\bcall out\b|\burgent\b|\bmaster\b|\bnearest\b|\bneed\b|\blooking for\b|\bfind\b")
EXPLICIT_REQUEST_RE = re.compile(r"\byour (house|home)\b|\bmy (house|home)\b|\bfor (my|your) \w+\b|\bi need\b|\bneed an?\b")
TRADE_NOUN_RE = re.compile(r"\belectricians?\b|\bsparky\b|\bsparkies\b|\binstallation\b|\bupgrade\b|\breplacement\b|\brepairs?\b|\bservicing\b|\brewir(e|ing)\b|\bre wir(e|ing)\b|\bfault finding\b|\btesting\b|\binspection\b|\bmaintenance\b")

PRICE_DISCOVERY_RE = re.compile(
    r"\bhow much\b|\bcost (to|of|for)\b|\bquotes?\b|\bquotations?\b|\baverage cost\b|\bprices?\b|\bpricing\b|\bcosts?\b|\bcharges?\b|\bper hour\b|\bestimates?\b"
)
CALC_RE = re.compile(r"\bcalculator\b|\bestimator\b")

SERVICE_PATTERNS = [
    ("Switchboard Upgrades", re.compile(r"\bswitch ?boards?\b|\bfuse ?(box|board|panel|es)?\b|\bmeter board\b|\belectrical panel\b|\belectric panel\b|\bpanel (upgrade|replacement)\b|\bmain electrical panel\b|\bcircuit breaker|\bbreaker\b|\brcd\b|\belectric panel\b|\bpanel box\b|\bpanel for home\b")),
    ("Small Renos & Rewiring", re.compile(r"\brewir\w*|\bre wir\w*|\bhouse wiring\b|\bhome wiring\b|\bwiring (installation|services?|an old|old|repair|maintenance)\b|\bresidential wiring\b|\bwiring contractor\b|\brenovation|\bremodel\b|\bpower ?points?\b|\bnew power\b|\blighting\b|\blight switch\b|\bwiring\b|\bnew home\b|\bwiring in old\b|\bold wiring\b|\bwiring a new house\b|\bdimmer\b")),
    ("Repairs & Servicing", re.compile(r"\brepair\w*|\bservicing\b|\bservice call\b|\bfault\b|\bemergency\b|\burgent\b|\bcall ?out\b|\b24\b|\b24hr\b|\bafter hours\b|\bout of hours\b|\bsame day\b|\bmaintenance\b|\binspection\b|\btesting\b|\bfix\b|\bfixer\b|\bon call\b|\bweekend\b|\bsunday\b")),
]


def cluster_key(kw):
    words = re.findall(r"[a-z0-9]+", kw.lower())
    loc_words = {"near", "me", "in", "my", "area", "nearby", "close", "to", "local", "around", "the", "by", "nearest"}
    has_locality = any(w in loc_words for w in words)
    norm = []
    for w in words:
        if w in loc_words:
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


def has_unknown_token(kw):
    kw = re.sub(r"\bpower ?points?\b", "powerpoint", kw)
    toks = re.findall(r"[a-z0-9']+", kw)
    unknown = [t for t in toks if t not in GENERIC and t not in {'24','7','247','24x7'}]
    return unknown


def classify(keyword):
    kw = keyword.lower().strip()
    for pattern, reason, neg in HARD_EXCLUDES:
        if re.search(pattern, kw):
            return ("Excluded", reason, neg, pattern)

    unknown = has_unknown_token(kw)
    if unknown:
        return ("Excluded", f"unrecognised word(s) {unknown} - likely a competitor/company name or off-topic", None, "unknown-token")

    if CALC_RE.search(kw):
        if re.search(r"\bcost\b|\bprice\b|\bquote\b", kw):
            return ("Price Discovery", "", None, None)
        return ("Excluded", "non-cost calculator/estimator", None, None)

    if kw in ("electrical wiring", "skilled electrical"):
        return ("Manual Review", "bare topic/ambiguous term with real volume - could be research or hiring intent", None, None)

    if PRICE_DISCOVERY_RE.search(kw):
        if re.search(r"\bpanel\b|\bbreaker\b", kw):
            return ("Manual Review", "US-style panel/breaker wording on a price query - NZ customers usually say switchboard/fuse box, check intent", None, None)
        return ("Price Discovery", "", None, None)

    has_locality = bool(LOCALITY_RE.search(kw))
    has_entity = bool(ENTITY_RE.search(kw))
    has_hire = bool(HIRE_QUALIFIER_RE.search(kw))
    has_explicit = bool(EXPLICIT_REQUEST_RE.search(kw))
    has_noun = bool(TRADE_NOUN_RE.search(kw))
    if not (has_locality or has_entity or has_hire or has_explicit or has_noun):
        return ("Excluded", "no hiring/business signal - top-of-funnel/exploratory", None, None)

    # verb-first imperative on a stated service with no hiring signal - ambiguous
    if re.match(r"^(upgrade|upgrading|update|replace|replacing|change|changing|rewire|rewiring|install|installing)\b", kw) and not (has_locality or has_entity or has_hire or has_explicit):
        return ("Manual Review", "verb-first request with no hiring signal - could be DIY or hiring an electrician", None, None)

    # US-style "panel"/"breaker" wording - keep but flag
    if re.search(r"\belectrical panel\b|\belectric panel\b|\bpanel\b|\bbreaker\b", kw):
        return ("Manual Review", "US-style panel/breaker wording - NZ customers usually say switchboard/fuse box, check intent", None, None)

    services = [n for n, p in SERVICE_PATTERNS if p.search(kw)]
    if not services:
        service = "General Electrician"
    else:
        service = services[0]

    if has_locality and has_entity:
        tier = "A"
    elif has_locality or has_entity or has_hire or has_explicit or has_noun:
        tier = "B"
    else:
        tier = "C"
    return ("BOF", service, tier, None)


def _fmt(r, category, note=""):
    return {
        "category": category, "keyword": r["keyword"], "avg_monthly_searches": r["avg_monthly_searches"],
        "competition": r["competition"], "low_top_of_page_bid": r["low_top_of_page_bid"],
        "high_top_of_page_bid": r["high_top_of_page_bid"], "note": note,
    }


def main():
    rows_by_kw = {}
    for path in INPUTS:
        with open(path, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                k = r["keyword"].lower().strip()
                ex = rows_by_kw.get(k)
                if ex is None or int(r["avg_monthly_searches"]) > int(ex["avg_monthly_searches"]):
                    rows_by_kw[k] = r

    excluded_log, pd, manual, bof = [], [], [], []
    for r in rows_by_kw.values():
        if int(r["avg_monthly_searches"]) < MIN_SEARCHES:
            continue
        res = classify(r["keyword"])
        if res[0] == "Excluded":
            excluded_log.append({**r, "reason": res[1], "neg_type": res[2] or "", "pattern": res[3] or ""})
        elif res[0] == "Price Discovery":
            pd.append(r)
        elif res[0] == "Manual Review":
            manual.append({**r, "note": res[1]})
        else:
            bof.append({**r, "service": res[1], "tier": res[2]})

    by_service = {}
    for r in bof:
        by_service.setdefault(r["service"], []).append(r)

    tier_rank = {"A": 0, "B": 1, "C": 2}
    p1, p2 = [], []
    FLOOR = 5
    for service, items in by_service.items():
        clusters = {}
        for r in items:
            clusters.setdefault(cluster_key(r["keyword"]), []).append(r)
        reps = []
        for members in clusters.values():
            members.sort(key=lambda r: -int(r["avg_monthly_searches"]))
            reps.append(members[0])
            p2.extend(members[1:])
        reps.sort(key=lambda r: (tier_rank[r["tier"]], -int(r["avg_monthly_searches"])))
        head = reps[:FLOOR]
        for r in reps[FLOOR:]:
            # no cap: any Tier A/B keyword is Priority 1 (PROCESS.md)
            if r["tier"] in ("A", "B") or int(r["avg_monthly_searches"]) >= 20:
                head.append(r)
            else:
                p2.append(r)
        p1.extend(head)

    out = [_fmt(r, "BOF - Priority 1", note=r["service"]) for r in p1]
    out += [_fmt(r, "BOF - Priority 2", note=r["service"]) for r in p2]
    out += [_fmt(r, "Price Discovery") for r in pd]
    out += [_fmt(r, "Manual Review", note=r["note"]) for r in manual]
    out.sort(key=lambda r: (r["category"], -int(r["avg_monthly_searches"])))

    os.makedirs(OUT_DIR, exist_ok=True)
    fields = ["category", "keyword", "avg_monthly_searches", "competition", "low_top_of_page_bid", "high_top_of_page_bid", "note"]
    with open(OUT_CATEGORIZED, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(out)

    with open(OUT_EXCLUDED_LOG, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(excluded_log[0].keys()))
        w.writeheader()
        w.writerows(excluded_log)

    # account negatives: only concrete off-topic themes (PROCESS.md step 9) -
    # phrase match for recurring problem words, never the unknown-token bucket
    # (company names) or floor/no-signal drops.
    phrase_terms = {
        "cheap": ["cheap", "affordable", "free"],
        "jobs": ["apprentice", "jobs", "course", "journeyman"],
        "commercial": ["commercial", "industrial", "high voltage"],
        "diy": ["diy", "how to"],
        "adjacent": ["gate", "garage door", "generator", "hot water", "heat pump", "aircon", "ceiling fan", "alarm", "plumber", "solar", "ev charger"],
        "powerpoint software": ["ppt", "powerpoint presentation"],
        "us terms": ["gfci", "breaker box", "outlet"],
    }
    seen = set()
    neg_rows = []
    present = {r["neg_type"] for r in excluded_log if r["neg_type"]}
    for neg_type, terms in phrase_terms.items():
        if neg_type in present:
            for t in terms:
                if t not in seen:
                    seen.add(t)
                    neg_rows.append({"negative_keyword": t, "match_type": "Phrase", "source_count": sum(1 for r in excluded_log if r["neg_type"] == neg_type)})
    with open(OUT_NEGATIVES, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["negative_keyword", "match_type", "source_count"])
        w.writeheader()
        w.writerows(neg_rows)

    print(f"P1={len(p1)} P2={len(p2)} PD={len(pd)} Manual={len(manual)} Excluded={len(excluded_log)}")


if __name__ == "__main__":
    main()
