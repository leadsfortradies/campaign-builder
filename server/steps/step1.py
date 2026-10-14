"""Step 1 - Keyword research + classification (PROCESS.md Step 1).

1. Candidate keywords:
   - If a previous project in the same trade has an approved Step 1, reuse its
     keywords (minus that project's own place names) plus fresh seeds, and get
     real volume for THIS location via exact-phrase historical metrics.
   - Otherwise expand Claude-written seeds through Keyword Planner (NZ-wide is
     fine for a trade's first pass).
2. Hard excludes in code (cheap/affordable/free, DIY, jobs) so they can never
   slip through.
3. Claude classifies the rest (B / PD / MR / X, tier, service, negatives).
4. Priority 1 / 2 split is done here in code, following the rubric exactly:
   collapse close variants, every Tier A/B cluster winner is Priority 1 (no
   cap), Tier C only when its volume is 3x+ the service's best A/B keyword,
   and each service gets at least 5 Priority 1 keywords.
"""

import json
import re

from .. import gads, llm, projects_store
from ..jobs import Blocked, register_step
from . import rules, store

MIN_SEARCHES = 10
BATCH = 200

HARD_EXCLUDES = [
    (re.compile(r"\b(cheap|cheapest|affordable|budget|low cost|free)\b"), "price-positioning term (cheap/affordable/free) - standing exclude", "phrase"),
    (re.compile(r"\bdiy\b|^how to\b|\bhow do i\b|\byourself\b"), "DIY intent", None),
    (re.compile(r"\b(jobs?|careers?|salary|salaries|apprentice\w*|vacanc\w*|recruit\w*)\b"), "jobs/careers, not a customer", None),
]

LOCALITY = ["near me", "in my area", "nearby", "near by", "close to me", "around me", "local", "near"]
STOPWORDS = {"a", "an", "the", "for", "in", "of", "to", "my", "and", "best", "top"}


def _hard_exclude(kw):
    for pat, reason, neg in HARD_EXCLUDES:
        m = pat.search(kw)
        if m:
            word = m.group(0).strip()
            return reason, ({"term": word, "match": "phrase"} if neg else None)
    return None, None


def _cluster_key(kw):
    # Locality synonyms collapse into one marker ("near me" == "nearby"), but a
    # keyword WITH a locality marker never clusters with one without it - so a
    # Tier B "deck builder near me" can't lose its Priority 1 spot to a bare
    # Tier C "deck builder".
    k = " " + kw.lower() + " "
    for loc in LOCALITY:
        k = k.replace(f" {loc} ", " _loc_ ")
    toks = [t[:-1] if len(t) > 3 and t.endswith("s") and not t.endswith("ss") else t
            for t in k.split() if t not in STOPWORDS]
    return " ".join(sorted(toks))


def _gather(ctx, s0):
    services = s0["services"]
    areas = s0["service_areas"]

    seeds = llm.complete_json(ctx, rules.SCOPE_RULES, f"""\
Business: {s0.get('business_name')} ({s0.get('trade', '')}), New Zealand.
Stated services: {json.dumps(services)}
Service area: {json.dumps(areas)}
Scope notes: {s0.get('scope_notes', '') or 'none'}

Write Keyword Planner seed keywords for each stated service: 6-12 short,
high-intent seeds per service as NZ customers would type them (e.g. "deck
builder", "deck builders near me", "deck building company", "deck cost").
Include 1-3 cost/price seeds per service. Stay strictly inside the stated
services. Return JSON: {{"seeds": {{"<service>": ["seed", ...]}}}}""", max_tokens=3000)["seeds"]
    seed_list = sorted({s.lower().strip() for v in seeds.values() for s in v if s.strip()})
    ctx.log(f"{len(seed_list)} seed keywords")

    geo_ids = [g for g in (gads.resolve_location(a) for a in areas) if g]
    ctx.log(f"Service area geo targets: {geo_ids or 'none resolved'}")

    prior = _prior_keywords(ctx, s0)
    if prior and geo_ids:
        candidates = sorted(set(prior) | set(seed_list))
        ctx.log(f"Reusing {len(prior)} keywords from earlier {s0.get('trade')} projects; "
                f"looking up local volume for {len(candidates)} candidates")
        raw = [r for r in gads.historical_metrics(candidates, geo_ids)
               if r["avg_monthly_searches"] >= MIN_SEARCHES]
        source = "prior-research + local volume"
    else:
        ctx.log("No earlier project in this trade - expanding seeds NZ-wide")
        raw = gads.keyword_ideas(seed_list, [gads.NZ_GEO_ID], MIN_SEARCHES)
        source = "NZ-wide idea expansion"
    ctx.log(f"{len(raw)} keywords at {MIN_SEARCHES}+ searches/month ({source})")
    return {"source": source, "seeds": seeds, "geo_ids": geo_ids, "keywords": raw}


def _prior_keywords(ctx, s0):
    """Approved Step 1 keywords from other projects in the same trade, with
    that project's own place names stripped out."""
    trade = (s0.get("trade") or "").strip().lower()
    if not trade:
        return []
    out = set()
    for p in projects_store.load():
        if p["id"] == ctx.project_id or p.get("steps", {}).get("step1", {}).get("status") != "approved":
            continue
        other = store.read(p["id"], "step0") or {}
        if (other.get("trade") or "").strip().lower() != trade:
            continue
        places = [w.lower() for a in other.get("service_areas", []) for w in re.split(r"[\s,]+", a) if len(w) > 3]
        places += [w.lower() for w in re.split(r"[\s\-]+", p["label"].split(" - ")[-1]) if len(w) > 3]
        for r in store.approved_rows(p["id"], "step1"):
            kw = r["keyword"].lower()
            if r.get("group", "").startswith(("BOF", "Price", "Bottom")) and not any(pl in kw for pl in places):
                out.add(kw)
    return sorted(out)


def _classify(ctx, s0, keywords, note):
    services = s0["services"]
    system = rules.STEP1_RULES
    results = {}
    for start in range(0, len(keywords), BATCH):
        batch = keywords[start:start + BATCH]
        listing = "\n".join(f"{i}|{r['keyword']}|{r['avg_monthly_searches']}" for i, r in enumerate(batch))
        user = f"""\
Business: {s0.get('business_name')} ({s0.get('trade', '')}), service area {json.dumps(s0['service_areas'])}, New Zealand.
Stated services: {json.dumps(services)}
Scope notes: {s0.get('scope_notes', '') or 'none'}
{('CHANGE REQUEST FROM THE USER (apply this): ' + note) if note else ''}

Classify each keyword (format: index|keyword|monthly searches):
{listing}

Return JSON: {{"r": [[index, "B"|"PD"|"MR"|"X", tier "A"|"B"|"C"|"", service (one of the stated services, or "General"), note_or_reason, negative_term_or_empty, "phrase"|"exact"|""], ...]}}
Every index must appear exactly once. note_or_reason is empty for B/PD."""
        out = llm.complete_json(ctx, system, user, max_tokens=16000)["r"]
        for row in out:
            try:
                i = int(row[0])
            except (ValueError, TypeError, IndexError):
                continue
            if 0 <= i < len(batch):
                results[batch[i]["keyword"]] = row
        missing = [r["keyword"] for r in batch if r["keyword"] not in results]
        if missing:
            # Never silently drop: anything Claude skipped goes to Manual Review.
            for kw in missing:
                results[kw] = [0, "MR", "", "General", "not classified automatically - please check", "", ""]
        ctx.log(f"Classified {min(start + BATCH, len(keywords))}/{len(keywords)}")
    return results


def _split_priority(bof_rows):
    """bof_rows: dicts with keyword, avg_monthly_searches, tier, service.
    Returns set of keywords that go to Priority 1."""
    p1 = set()
    by_service = {}
    for r in bof_rows:
        by_service.setdefault(r["service"], []).append(r)
    tier_rank = {"A": 0, "B": 1, "C": 2}
    for rows in by_service.values():
        clusters = {}
        for r in rows:
            clusters.setdefault(_cluster_key(r["keyword"]), []).append(r)
        winners = []
        for members in clusters.values():
            members.sort(key=lambda r: (-r["avg_monthly_searches"], tier_rank.get(r["tier"], 1), len(r["keyword"])))
            winners.append(members[0])
        ab = [w for w in winners if w["tier"] in ("A", "B", "")]  # unknown tier = include
        best_ab = max([w["avg_monthly_searches"] for w in ab] or [0])
        chosen = {w["keyword"] for w in ab}
        chosen |= {w["keyword"] for w in winners
                   if w["tier"] == "C" and w["avg_monthly_searches"] >= 3 * max(best_ab, 1)}
        if len(chosen) < 5:
            rest = sorted([r for r in rows if r["keyword"] not in chosen],
                          key=lambda r: (tier_rank.get(r["tier"], 1), -r["avg_monthly_searches"]))
            chosen |= {r["keyword"] for r in rest[:5 - len(chosen)]}
        p1 |= chosen
    return p1


def run(ctx):
    s0 = store.read(ctx.project_id, "step0") or {}
    if not s0.get("services") or not s0.get("service_areas"):
        raise Blocked("I can't start keyword research yet - I need the services the business offers and "
                      "where it works. Add them under 'Business info' and this step will restart automatically.")
    note = ctx.payload.get("note", "")

    raw = store.read(ctx.project_id, "step1_raw") if ctx.job["kind"] == "revise_step" else None
    if raw is None:
        raw = _gather(ctx, s0)
        store.write(ctx.project_id, "step1_raw", raw)
    else:
        ctx.log("Re-classifying the saved keyword list with your change request")

    rows, excluded, negatives = [], [], {}
    to_classify = []
    for r in raw["keywords"]:
        reason, neg = _hard_exclude(r["keyword"].lower())
        if reason:
            excluded.append({**r, "reason": reason})
            if neg:
                negatives.setdefault((neg["term"], neg["match"]), 0)
                negatives[(neg["term"], neg["match"])] += 1
        else:
            to_classify.append(r)
    ctx.log(f"{len(excluded)} removed by standing excludes, {len(to_classify)} sent to Claude")

    labels = _classify(ctx, s0, to_classify, note)

    bof = []
    for r in to_classify:
        _, cat, tier, service, why, neg_term, neg_match = (list(labels[r["keyword"]]) + [""] * 7)[:7]
        cat = (cat or "MR").upper()
        if cat == "B":
            bof.append({**r, "tier": (tier or "").upper(), "service": service or "General"})
        elif cat == "PD":
            rows.append({**r, "group": "Price Discovery", "note": ""})
        elif cat == "X":
            excluded.append({**r, "reason": why})
            if neg_term:
                key = (neg_term.lower().strip(), "exact" if neg_match == "exact" else "phrase")
                negatives[key] = negatives.get(key, 0) + 1
        else:
            rows.append({**r, "group": "Manual Review", "note": why or "needs a decision"})

    p1 = _split_priority(bof)
    for r in bof:
        group = "BOF - Priority 1" if r["keyword"] in p1 else "BOF - Priority 2"
        rows.append({k: r[k] for k in ("keyword", "avg_monthly_searches", "competition", "low_bid", "high_bid")}
                    | {"group": group, "note": "", "service": r["service"]})

    order = {"BOF - Priority 1": 0, "BOF - Priority 2": 1, "Price Discovery": 2, "Manual Review": 3}
    rows.sort(key=lambda r: (order.get(r["group"], 9), -r["avg_monthly_searches"]))
    neg_list = sorted(({"negative_keyword": t, "match_type": m.title(), "source_count": c}
                       for (t, m), c in negatives.items()), key=lambda n: -n["source_count"])

    store.write(ctx.project_id, "step1_excluded", excluded)
    store.write(ctx.project_id, "step1_negatives", neg_list)
    store.publish_step(ctx.project_id, "step1", {
        "project_id": ctx.project_id,
        "step": "step1",
        "label": store.project_label(ctx.project_id),
        "group_label": "Category",
        "rows": rows,
        "negatives": neg_list,
        "source": raw["source"],
    }, row_count=len(rows))
    counts = {g: sum(1 for r in rows if r["group"] == g) for g in order}
    ctx.log(f"Result: {counts}, {len(excluded)} excluded, {len(neg_list)} negatives")
    ctx.need_approval(f"Keyword research ready: {counts['BOF - Priority 1']} Priority 1, "
                      f"{counts['BOF - Priority 2']} Priority 2, {counts['Price Discovery']} Price Discovery, "
                      f"{counts['Manual Review']} to check.")


register_step("step1")(run)
