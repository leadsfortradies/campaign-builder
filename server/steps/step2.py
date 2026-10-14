"""Step 2 - Location-based keywords (PROCESS.md Step 2).

Claude decides whether the service area is one big metro (skip - suburb
keywords get ~zero volume) or a region of separate towns (run it). For towns,
it picks 2-5 base terms per service from the approved Priority 1 keywords;
each "<base term> <town>" phrase gets exact-phrase volume for that town.
"""

import json

from .. import gads, llm
from ..jobs import Blocked, register_step
from . import rules, store

MIN_SEARCHES = 10


def run(ctx):
    s0 = store.read(ctx.project_id, "step0") or {}
    approved = store.approved_rows(ctx.project_id, "step1")
    p1 = [r for r in approved if r.get("group") == "BOF - Priority 1"]
    if not p1:
        raise Blocked("Step 2 needs an approved Step 1 with Priority 1 keywords.")
    note = ctx.payload.get("note", "")

    top = sorted(p1, key=lambda r: -r["avg_monthly_searches"])[:80]
    plan = llm.complete_json(ctx, rules.SCOPE_RULES, f"""\
Business: {s0.get('business_name')} ({s0.get('trade', '')}), New Zealand.
Stated services: {json.dumps(s0.get('services', []))}
Service area: {json.dumps(s0.get('service_areas', []))}
{('CHANGE REQUEST FROM THE USER (apply this): ' + note) if note else ''}

Decide:
1. Is the service area a single large metro (Auckland, Wellington, Christchurch,
   Hamilton, Tauranga, Dunedin) -> "metro", or a region of genuinely separate
   towns people would type by name (e.g. Manawatu: Palmerston North, Feilding,
   Ashhurst) -> "towns"? Suburbs of one city are NOT separate towns.
2. If towns: list the towns (max 10) and, per stated service, 2-5 base terms
   (no place names, no "near me") taken from these approved keywords that
   carry most of the volume:
{chr(10).join(f"- {r['keyword']} ({r['avg_monthly_searches']})" for r in top)}

Return JSON: {{"mode": "metro"|"towns", "reason": "...", "towns": ["..."], "base_terms": ["..."]}}""",
                              max_tokens=2000)

    if plan.get("mode") != "towns" or not plan.get("towns"):
        reason = plan.get("reason") or "Single large metro - suburb keywords get near-zero volume."
        store.skip_step(ctx.project_id, "step2",
                        f"{reason} Relying on Step 1's city-wide and near-me keywords; suburb reach "
                        "is handled by the campaign's location targeting.")
        ctx.log(f"Skipped: {reason}")
        ctx.queue_next("step3")
        return

    base_terms = sorted({t.lower().strip() for t in plan.get("base_terms", []) if t.strip()})[:25]
    rows = []
    for town in plan["towns"][:10]:
        geo = gads.resolve_location(town)
        if not geo:
            ctx.log(f"Couldn't find {town} in Google's location list - skipped")
            continue
        phrases = [f"{t} {town.lower()}" for t in base_terms]
        for m in gads.historical_metrics(phrases, [geo]):
            if m["avg_monthly_searches"] >= MIN_SEARCHES:
                rows.append({**m, "group": town, "note": ""})
        ctx.log(f"{town}: checked {len(phrases)} phrases")

    if not rows:
        store.skip_step(ctx.project_id, "step2",
                        f"Checked {len(base_terms)} terms across {', '.join(plan['towns'])}: none reached "
                        f"{MIN_SEARCHES} searches/month, so no town keywords added.")
        ctx.queue_next("step3")
        return

    rows.sort(key=lambda r: (r["group"], -r["avg_monthly_searches"]))
    store.publish_step(ctx.project_id, "step2", {
        "project_id": ctx.project_id, "step": "step2", "label": store.project_label(ctx.project_id),
        "group_label": "Location", "rows": rows,
    }, row_count=len(rows))
    ctx.need_approval(f"{len(rows)} town keywords found across {len({r['group'] for r in rows})} towns.")


register_step("step2")(run)
