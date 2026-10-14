"""Step 3 - Single Themed Ad Groups, split by campaign (PROCESS.md Step 3).

Campaign comes from each keyword's Step 1 category, never merged across
campaigns: BOF - Priority 1 / BOF - Priority 2 / Price Discovery. Step 2's town
keywords go to Priority 1. Kept Manual Review keywords default to Priority 2,
explicit cost questions to Price Discovery. Claude only picks the theme
(ad group) - one shared theme list across all three campaigns.
"""

import json
import re

from .. import llm
from ..jobs import Blocked, register_step
from . import rules, store

CAMPAIGNS = store.ALL_CAMPAIGNS + (store.MERGED_CAMPAIGN,)
COST_WORDS = re.compile(r"\b(cost|costs|price|prices|pricing|quote|quotes|how much|rates?|per m2|per square)\b")
BATCH = 250


def _campaign(row, from_step2):
    if from_step2:
        return "BOF - Priority 1"
    g = row.get("group", "")
    if g in CAMPAIGNS:
        return g
    return "Price Discovery" if COST_WORDS.search(row["keyword"].lower()) else "BOF - Priority 2"


def run(ctx):
    s0 = store.read(ctx.project_id, "step0") or {}
    kws = {}
    for r in store.approved_rows(ctx.project_id, "step1"):
        kws[r["keyword"]] = {**r, "campaign": _campaign(r, False)}
    for r in store.approved_rows(ctx.project_id, "step2"):
        kws.setdefault(r["keyword"], {**r, "campaign": _campaign(r, True)})
    choice = store.campaign_choice(ctx.project_id)
    # Keywords in a campaign the user didn't pick are left out; Priority 1 and 2
    # become one campaign when they asked for that.
    kws = {k: v for k, v in kws.items() if v["campaign"] in choice["campaigns"]}
    if choice["merge_bof"]:
        for v in kws.values():
            if v["campaign"] in ("BOF - Priority 1", "BOF - Priority 2"):
                v["campaign"] = store.MERGED_CAMPAIGN
    if not kws:
        raise Blocked("Step 3 needs approved keywords from Step 1 in at least one of the chosen campaigns.")
    note = ctx.payload.get("note", "")
    previous = store.read(ctx.project_id, "step3") if note else None

    keywords = sorted(kws.values(), key=lambda r: -r["avg_monthly_searches"])
    themes = {}
    theme_names = []
    for start in range(0, len(keywords), BATCH):
        batch = keywords[start:start + BATCH]
        listing = "\n".join(f"{i}|{r['keyword']}" for i, r in enumerate(batch))
        prev = ""
        if previous:
            prev = "Previous ad groups (keep unless the change request says otherwise):\n" + "\n".join(
                f"- {r['keyword']} -> {r['group'].split(' — ', 1)[-1]}" for r in previous["rows"]
                if r["keyword"] in {b["keyword"] for b in batch})
        out = llm.complete_json(ctx, rules.SCOPE_RULES, f"""\
Business: {s0.get('business_name')} ({s0.get('trade', '')}), stated services {json.dumps(s0.get('services', []))}.
{('CHANGE REQUEST FROM THE USER (apply this): ' + note) if note else ''}

Group these keywords into Single Themed Ad Groups (STAGs): one tight theme per
ad group, usually one per stated service or sub-service (e.g. "Timber Decks",
"Composite Decks", "Interior Painting", "General House Painting"). Use short
Title Case names, no campaign or location names. Reuse existing theme names
where they fit: {json.dumps(theme_names)}
{prev}

Keywords (index|keyword):
{listing}

Return JSON: {{"a": [[index, "Theme Name"], ...]}} - every index exactly once.""", max_tokens=8000)["a"]
        for pair in out:
            try:
                i, name = int(pair[0]), str(pair[1]).strip()
            except (ValueError, TypeError, IndexError):
                continue
            if 0 <= i < len(batch) and name:
                themes[batch[i]["keyword"]] = name
                if name not in theme_names:
                    theme_names.append(name)
        ctx.log(f"Grouped {min(start + BATCH, len(keywords))}/{len(keywords)}")

    rows = []
    for r in keywords:
        theme = themes.get(r["keyword"], "General")  # never drop a keyword
        rows.append({
            "group": f"{r['campaign']} — {theme}",
            "keyword": r["keyword"],
            "avg_monthly_searches": r["avg_monthly_searches"],
            "competition": r.get("competition", ""),
            "low_bid": r.get("low_bid", 0),
            "high_bid": r.get("high_bid", 0),
            "note": "",
        })
    rows.sort(key=lambda r: (CAMPAIGNS.index(r["group"].split(" — ")[0]), r["group"], -r["avg_monthly_searches"]))
    store.publish_step(ctx.project_id, "step3", {
        "project_id": ctx.project_id, "step": "step3", "label": store.project_label(ctx.project_id),
        "group_label": "Campaign — Ad Group", "rows": rows,
    }, row_count=len(rows))
    groups = {r["group"] for r in rows}
    ctx.need_approval(f"{len(rows)} keywords in {len(groups)} ad groups.")


register_step("step3")(run)
