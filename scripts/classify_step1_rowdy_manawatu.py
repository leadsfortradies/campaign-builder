"""
Step 1 classification for Rowdy Builders (palmydecksandfences.co.nz) -
Manawatu rebuild, 2026-10-13.

Scope (confirmed in chat 2026-10-13): decks, fences (timber is the bulk of
the work but all fence types are fine), pergolas, pool fencing, deck
roofs/covers. Not stated, so excluded: gates, fence/deck repairs, painting/
staining, retaining walls, patios as a standalone service, carports.

Prior same-trade research: deck-fence-auckland (approved Step 3). Its
BOF-vs-Price-Discovery call is reused as the prior for any keyword it
covered; standing rules (cheap/free, design, gates, repairs) still override.
Volume: historical metrics against the account's 9 target locations, close
variants mapped (output/rowdy-builders-manawatu/historical_local.csv).
"""

import csv
import json
import os
import re
from collections import Counter

MIN_SEARCHES = 10
IN_PATH = "output/rowdy-builders-manawatu/historical_local.csv"
OUT_DIR = "output/rowdy-builders-manawatu"
OUT_CATEGORIZED = f"{OUT_DIR}/step1_categorized.csv"
OUT_NEGATIVES = f"{OUT_DIR}/step1_negative_keywords.csv"
OUT_EXCLUDED_LOG = f"{OUT_DIR}/step1_excluded_log.csv"

LOCAL_PLACES = r"palmerston north|palmy|feilding|manawatu|ashhurst|levin|marton|bulls|sanson|woodville|rangitikei"
OTHER_PLACES = r"auckland|christchurch|wellington|hamilton|tauranga|dunedin|nelson|napier|hastings|whanganui|wanganui|kapiti|australia|usa"

# (regex, reason, negative term or None = no negative)
HARD_EXCLUDES = [
    (r"\bcheap(est)?\b|\baffordable\b|\bbudget\b|\blow cost\b|\bdiscount\b", "cheap/affordable price-positioning - standing exclude", "cheap"),
    (r"\bfree\b", "free price-positioning term", "free"),
    (rf"\b({OTHER_PLACES})\b", "outside service area", "place"),
    (r"\bbunnings\b|\bmitre ?10\b|\btrade ?me\b", "retailer/marketplace", "retail"),
    (r"\bdiy\b|\bhow to\b|\bkits?\b|\bplans\b|\bbuild your own\b|\bpost (depth|spacing|concrete)\b|\bhow deep\b|\bhow many palings\b|\bmaterials calculator\b|\bwood (deck )?(price |cost )?calculator\b|\bwood cost calculator\b|\bpanels\b", "DIY/materials intent", "diy"),
    (r"\bdesigns?\b|\bdesigner\b|\bideas\b|\bstyles\b|\btypes\b|\bcolou?rs?\b|\binspiration\b", "design/ideas research - standing exclude", "design"),
    (r"\bgates?\b", "gates - not a stated service", "gate"),
    (r"\brepairs?\b|\brestoration\b|\bleaning\b|\brotten\b|\bpost replacement\b|\bremoval\b", "repair/removal - not a stated service (prior Auckland run excluded repair too)", "repair"),
    (r"\bpaint(ing|s)?\b|\bstain(ing)?\b", "painting/staining - not a stated service", "paint"),
    (r"\bact\b|\blaws?\b|\brules\b|\bregulations?\b|\brequirements?\b|\bnotice\b|\bheight\b|\binspection\b|\bconsent\b|\bwho pays\b", "rules/regulations research - informational", "rules"),
    (r"\bper square foot\b|\bsquare feet\b|\bper foot\b|\blabor\b", "US units/spelling - not NZ searcher", None),
    (r"\btimber deck prices\b|\bdecking timber\b|\btimber prices\b", "product (timber) pricing, not service pricing", None),
    (r"^fence fence companies$", "garbled duplicate phrasing", None),
    (r"\bfarm\b|\brural\b|\blivestock\b|\belectric\b|\bsecurity\b", "farm/rural/security fencing - standing exclude", "farm"),
]

MANUAL_REVIEW_RULES = [
    (r"\blouvre", "louvre roof systems are usually a specialist product (supply + install by the brand's dealer) - confirm Guy builds/installs these"),
    (r"\bveranda|\bverandah\b", "veranda - overlaps deck roofs/covers, but often means a house verandah (part of the house build); confirm"),
    (r"^(covered patio|patio roof|patio covers?|covered outdoor area|outdoor shelter)$", "roof/cover over a patio rather than a deck - close to deck roofs/covers but patio isn't a stated service"),
    (r"^manawatu fencing$", "could be a competitor's business name (Manawatu Fencing) as much as a generic local search"),
    (r"^(fence calculator|fence calculator nz|fencing calculator nz|paling fence calculator|timber paling fence calculator)$", "calculator with no cost/price word - often a DIY materials calculator (palings/posts), not a job price"),
    (r"^(pergola|pergolas|fences|covered deck|deck roof|pool fence|pool fencing|fencing nz)$", "bare product term, no hiring signal - decent local volume but mostly browsing/research intent"),
]

LOCALITY_RE = re.compile(rf"near me|in my area|nearby|close to me|\blocal\b|\b({LOCAL_PLACES})\b")
ENTITY_RE = re.compile(r"\bcompan(y|ies)\b|\bco\b|\bcontractors?\b|\bservices?\b|\bspecialists?\b|\binstallers?\b|\bbusiness\b|\bfirms?\b")
TRADE_NOUN_RE = re.compile(r"\bbuilders?\b|\bfencers?\b")
HIRE_RE = re.compile(r"\bhire\b|\bprofessional\b|\breputable\b|\bbest\b|\bresidential\b|\bcustom\b|\bbuild me\b|\bget a\b|\bbuilt\b|\bbuild a deck near me\b")
JOB_RE = re.compile(r"\binstall(ation|ed|ing)?\b|\bconstruction\b|\breplacement\b")
PRICE_RE = re.compile(r"\bhow much\b|\bcosts?\b|\bprices?\b|\bpricing\b|\bquot(e|es|ation)\b|\bestimat(e|or)\b|\bcalculator\b|\bper (metre|m2|meter)\b")

SERVICES = [
    ("Pool Fencing", re.compile(r"\bpool\b|\bspa\b")),
    ("Deck Roofs & Covers", re.compile(r"\broof\b|\bcover(ed|s)?\b|\bcanopy\b|\bshelter\b")),
    ("Pergolas", re.compile(r"\bpergolas?\b")),
    ("Decks", re.compile(r"\bdeck(s|ing)?\b")),
    ("Fences", re.compile(r"\bfenc(e|es|ing|ers?)\b|\bpaling|\bpailing\b|\bpicket\b")),
]

LOCALITY_WORDS = {"near", "me", "in", "my", "area", "nearby", "close", "to", "local"}


def service_for(kw):
    hits = [name for name, pat in SERVICES if pat.search(kw)]
    if "Decks" in hits and "Fences" in hits:
        return "Decks & Fences"
    if "Pergolas" in hits and "Decks" in hits:
        return "Pergolas"
    return hits[0] if hits else None


def cluster_key(kw):
    words = re.findall(r"[a-z]+", kw.lower())
    norm = []
    for w in words:
        if w in LOCALITY_WORDS:
            continue
        w = {"aluminum": "aluminium", "fencing": "fence", "decking": "deck", "pailing": "paling",
             "co": "company", "wooden": "wood", "timber": "wood"}.get(w, w)
        if len(w) > 3 and w.endswith("ies"):
            w = w[:-3] + "y"
        elif len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]
        norm.append(w)
    return tuple(sorted(set(norm))) + (("__loc__",) if any(w in LOCALITY_WORDS for w in words) else ())


def auckland_prior():
    prior = {}
    for r in json.load(open("web/data/deck-fence-auckland/step3.json"))["rows"]:
        kw = re.sub(r"\s+", " ", re.sub(r"\b(west |north |south |east )?auckland\b", "", r["keyword"])).strip()
        prior[kw] = "Price Discovery" if r["group"].startswith("Price Discovery") else "BOF"
    return prior


def classify(kw, prior):
    for pattern, reason, neg in HARD_EXCLUDES:
        if re.search(pattern, kw):
            return ("Excluded", reason, neg)
    for pattern, note in MANUAL_REVIEW_RULES:
        if re.search(pattern, kw):
            return ("Manual Review", note, None)

    service = service_for(kw)
    if service is None:
        return ("Excluded", "doesn't name a stated service", None)

    is_price = bool(PRICE_RE.search(kw))
    if kw in prior:
        if prior[kw] == "Price Discovery" or is_price:
            return ("Price Discovery", service, None)
    elif is_price:
        return ("Price Discovery", service, None)

    loc, ent, trade = bool(LOCALITY_RE.search(kw)), bool(ENTITY_RE.search(kw)), bool(TRADE_NOUN_RE.search(kw))
    if loc and (ent or trade):
        return ("BOF", service, "A")
    if loc or ent or trade or HIRE_RE.search(kw) or JOB_RE.search(kw):
        return ("BOF", service, "B")
    if kw in prior:
        return ("BOF", service, "C")
    return ("Excluded", "no hiring/business signal - bare product/style search", None)


def main():
    prior = auckland_prior()
    rows = [r for r in csv.DictReader(open(IN_PATH)) if int(r["avg_monthly_searches"]) >= MIN_SEARCHES]

    out, excluded, bof = [], [], []
    for r in rows:
        kw = r["keyword"]
        cat, a, b = classify(kw, prior)
        base = {"keyword": kw, "avg_monthly_searches": int(r["avg_monthly_searches"]), "competition": r["competition"],
                "low_top_of_page_bid": r["low_bid"], "high_top_of_page_bid": r["high_bid"]}
        if cat == "Excluded":
            excluded.append({**base, "reason": a, "neg": b or ""})
        elif cat == "BOF":
            bof.append({**base, "service": a, "tier": b})
        elif cat == "Manual Review":
            out.append({"category": "Manual Review", "service": service_for(kw) or "", **base, "note": a})
        else:
            out.append({"category": cat, "service": a, **base, "note": ""})

    # Priority 1/2: every Tier A/B keyword goes to P1 - no cap, and no
    # close-variant demotion (locality/entity/hire signal alone = P1, see
    # PROCESS.md + the Taupo/Hamilton corrections). Only bare Tier C terms
    # collapse into close-variant clusters, filling a service's floor of 5.
    by_service = {}
    for r in bof:
        by_service.setdefault(r["service"], []).append(r)
    for service, items in by_service.items():
        ab = [r for r in items if r["tier"] in ("A", "B")]
        for r in ab:
            out.append({"category": "BOF - Priority 1", "service": service,
                        **{k: r[k] for k in r if k not in ("service", "tier")}, "note": ""})
        clusters = {}
        for r in items:
            if r["tier"] == "C":
                clusters.setdefault(cluster_key(r["keyword"]), []).append(r)
        reps = []
        for members in clusters.values():
            members.sort(key=lambda r: (-r["avg_monthly_searches"], len(r["keyword"])))
            reps.append(members[0])
            for m in members[1:]:
                out.append({"category": "BOF - Priority 2", "service": service,
                            **{k: m[k] for k in m if k not in ("service", "tier")}, "note": ""})
        reps.sort(key=lambda r: -r["avg_monthly_searches"])
        for i, r in enumerate(reps):
            cat = "BOF - Priority 1" if len(ab) + i < 5 else "BOF - Priority 2"
            out.append({"category": cat, "service": service,
                        **{k: r[k] for k in r if k not in ("service", "tier")}, "note": ""})

    # Flag disagreements with the Auckland prior
    for r in out:
        p = prior.get(r["keyword"])
        if p and r["category"] in ("Manual Review",):
            r["note"] += " (approved in the Auckland build)"
    for r in excluded:
        if prior.get(r["keyword"]):
            r["reason"] += " (was approved in the Auckland build - overridden by a standing rule/scope)"

    out.sort(key=lambda r: (r["category"], r["service"], -r["avg_monthly_searches"], r["keyword"]))
    with open(OUT_CATEGORIZED, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["category", "service", "keyword", "avg_monthly_searches", "competition",
                                          "low_top_of_page_bid", "high_top_of_page_bid", "note"])
        w.writeheader()
        w.writerows(out)
    with open(OUT_EXCLUDED_LOG, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["keyword", "avg_monthly_searches", "reason", "neg"])
        w.writeheader()
        for r in sorted(excluded, key=lambda r: (r["reason"], r["keyword"])):
            w.writerow({k: r[k] for k in ["keyword", "avg_monthly_searches", "reason", "neg"]})

    # Account negatives: phrase for recurring themes, exact for one-offs.
    # "No hiring signal" exclusions aren't irrelevant, just not bid on - no negative.
    PHRASE = {
        "cheap": ["cheap", "cheapest", "affordable", "budget", "low cost", "discount"],
        "free": ["free"],
        "place": OTHER_PLACES.split("|"),
        "retail": ["bunnings", "mitre 10", "trade me"],
        "diy": ["diy", "how to", "kit", "kits", "plans", "build your own", "panels"],
        "design": ["design", "designs", "designer", "ideas", "styles", "types", "colours", "colors"],
        "gate": ["gate", "gates"],
        "repair": ["repair", "repairs", "restoration", "removal"],
        "paint": ["paint", "painting", "stain", "staining"],
        "rules": ["rules", "regulations", "requirements", "law", "fencing act", "consent", "inspection"],
        "farm": ["farm", "rural", "livestock", "electric", "security"],
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
    for r in excluded:
        if r["keyword"] in covered or not r["neg"] and r["reason"].startswith(("no hiring", "doesn't name")):
            continue
        neg_rows.append({"negative_keyword": f"[{r['keyword']}]", "match_type": "Exact", "source_count": 1})
        covered.add(r["keyword"])
    with open(OUT_NEGATIVES, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["negative_keyword", "match_type", "source_count"])
        w.writeheader()
        w.writerows(neg_rows)

    print(Counter(r["category"] for r in out), "| excluded", len(excluded), "| negatives", len(neg_rows))
    print(Counter((r["category"], r["service"]) for r in out if r["category"].startswith("BOF")))


if __name__ == "__main__":
    main()
