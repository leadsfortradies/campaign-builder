"""Step 4 - Ad copy for BOF - Priority 1 ad groups (PROCESS.md Step 4).

Claude writes each ad group's RSA; code then checks every hard rule (counts,
character limits, no dashes, a keyword in every description) and sends
violations back for a fix. Anything still wrong after that is flagged on the
ad group rather than silently trimmed.
"""

import json
import re

from .. import llm
from ..jobs import Blocked, register_step
from . import rules, store

CAMPAIGN = "BOF - Priority 1"
FACT_FIELDS = ("business_name", "trade", "services", "service_areas", "years_experience",
               "completed_projects", "certifications", "other_info", "scope_notes")
BANNED = re.compile(r"[—–]|\b(cheap|affordable|budget)\b", re.I)
# "near me" is a searcher's phrase: fine in pinned keyword headlines, wrong in
# sentences the business writes about itself ("Need a plumber near you?" instead).
NEAR_ME = re.compile(r"\bnear\s*me\b|\bnearby me\b", re.I)


def _norm(s):
    return re.sub(r"[^a-z0-9 ]", "", s.lower())


def _tokens(s):
    """Lowercased, singularised word set - so "deck builders near me" counts as
    containing the keyword "deck builder near me" (Google treats them as close variants)."""
    s = re.sub(r"\bnear you\b", "near me", s, flags=re.I)  # "near you" satisfies a "near me" keyword
    return {t[:-1] if len(t) > 3 and t.endswith("s") and not t.endswith("ss") else t for t in _norm(s).split()}


def validate(ad, keywords):
    problems = []
    pinned, benefit = ad.get("headlines_pinned", []), ad.get("headlines_benefit", [])
    descs, paths = ad.get("descriptions", []), ad.get("paths", [])
    if len(pinned) != 3:
        problems.append(f"need exactly 3 pinned headlines, got {len(pinned)}")
    if len(benefit) != 12:
        problems.append(f"need exactly 12 benefit headlines, got {len(benefit)}")
    if len(descs) != 4:
        problems.append(f"need exactly 4 descriptions, got {len(descs)}")
    if len(paths) != 2:
        problems.append(f"need exactly 2 paths, got {len(paths)}")
    heads = pinned + benefit
    for h in heads:
        if len(h) > 30:
            problems.append(f'headline over 30 chars ({len(h)}): "{h}"')
    if len({_norm(h) for h in heads}) != len(heads):
        problems.append("duplicate headlines")
    kw_tokens = [_tokens(k) for k in keywords]
    for d in descs:
        if len(d) > 90:
            problems.append(f'description over 90 chars ({len(d)}): "{d}"')
        if not any(k and k <= _tokens(d) for k in kw_tokens):
            problems.append(f'description has none of the ad group keywords: "{d}"')
    for p in paths:
        if len(p) > 15 or " " in p:
            problems.append(f'path must be max 15 chars, no spaces: "{p}"')
    for text in benefit + descs:
        if NEAR_ME.search(text):
            problems.append(f'use "near you" (singular noun, with an article), not "near me", in: "{text}"')
    for text in heads + descs + paths:
        if BANNED.search(text):
            problems.append(f'banned dash/word in: "{text}"')
    return problems


PD_RULE = ("This is a PRICE DISCOVERY ad group (people asking what the service costs). The 3 pinned "
           "headlines must be offer-style price prompts like \"Get A Price For Your Deck\", \"Need A Price "
           "For Your Deck?\", \"Get Your New Deck Priced\", NOT echoes of the cost keywords. Descriptions "
           "may still contain the cost keyword.")


def ad_group_sets(project_id):
    """{ad group name: (campaign, theme, rows)} for every campaign that gets ad copy.
    The main BOF campaign keeps the bare theme as its name (as before); other
    campaigns use "Campaign — theme" so names never collide."""
    campaigns = store.ad_copy_campaigns(project_id) or [CAMPAIGN]
    out = {}
    for r in store.approved_rows(project_id, "step3"):
        camp, _, theme = r.get("group", "").partition(" — ")
        if theme and camp in campaigns:
            name = theme if camp == campaigns[0] else f"{camp} — {theme}"
            out.setdefault(name, (camp, theme, []))[2].append(r)
    return out


def _write_group(ctx, facts, name, keywords, note, previous, campaign=CAMPAIGN, theme=None):
    kw_lines = "\n".join(f"- {k['keyword']} ({k['avg_monthly_searches']}/mo)" for k in keywords[:40])
    prev = f"\nPrevious version (revise it per the change request):\n{json.dumps(previous)}" if previous else ""
    user = f"""\
Business facts (the ONLY facts you may use for benefit headlines):
{json.dumps(facts, indent=1)}

Campaign: {campaign}
Ad group: {theme or name}
{PD_RULE if campaign == "Price Discovery" else ""}
Keywords (by search volume):
{kw_lines}
{('CHANGE REQUEST FROM THE USER (apply this): ' + note) if note else ''}{prev}

Return JSON: {{"headlines_pinned": [3], "headlines_benefit": [12], "descriptions": [4], "paths": [2]}}"""
    ad = llm.complete_json(ctx, rules.AD_COPY_RULES, user, max_tokens=3000)
    kw_texts = [k["keyword"] for k in keywords]
    for _ in range(2):
        problems = validate(ad, kw_texts)
        if not problems:
            break
        ctx.log(f"{name}: fixing {len(problems)} rule problems")
        ad = llm.complete_json(ctx, rules.AD_COPY_RULES, user + "\n\nYour previous answer:\n" + json.dumps(ad)
                               + "\n\nFix these problems and return the full corrected JSON:\n- "
                               + "\n- ".join(problems), max_tokens=3000)
    problems = validate(ad, kw_texts)
    return {
        "name": name,
        "campaign": campaign,
        "theme": theme or name,
        "final_url": (previous or {}).get("final_url", ""),
        "headlines_pinned": ad.get("headlines_pinned", []),
        "headlines_benefit": ad.get("headlines_benefit", []),
        "descriptions": ad.get("descriptions", []),
        "paths": ad.get("paths", []),
        "warnings": problems,
    }


def run(ctx):
    s0 = store.read(ctx.project_id, "step0") or {}
    # Ad copy needs real facts about the business - never invented. The logo
    # isn't needed here (that's for landing pages).
    detail_fields = ("years_experience", "completed_projects", "certifications", "other_info")
    if not s0.get("business_name") or not any(s0.get(f) for f in detail_fields):
        raise Blocked(
            "I can't write the ad copy yet - I need the business information (business name plus "
            "real details like years trading, jobs completed, reviews, guarantees or certifications). "
            "Add it under 'Business info' and this step will restart automatically.")
    facts = {k: s0[k] for k in FACT_FIELDS if s0.get(k)}
    note = ctx.payload.get("note", "")

    sets = ad_group_sets(ctx.project_id)
    if not sets:
        raise Blocked("Ad copy needs an approved Step 3 with ad groups in the chosen campaigns.")

    previous = {g["name"]: g for g in (store.read(ctx.project_id, "step4") or {}).get("ad_groups", [])} if note else {}
    ad_groups = []
    for name, (camp, theme, kws) in sets.items():
        kws.sort(key=lambda r: -r["avg_monthly_searches"])
        g = _write_group(ctx, facts, name, kws, note, previous.get(name), camp, theme)
        g["keywords"] = sorted(k["keyword"] for k in kws)  # lets "Update Ad Copy" spot changed ad groups
        ad_groups.append(g)
        ctx.log(f"Wrote ad copy for {name}")

    items = sum(len(g["headlines_pinned"]) + len(g["headlines_benefit"]) + len(g["descriptions"]) + len(g["paths"])
                for g in ad_groups)
    store.publish_step(ctx.project_id, "step4", {
        "project_id": ctx.project_id, "step": "step4", "label": store.project_label(ctx.project_id),
        "ad_groups": ad_groups,
    }, row_count=items)
    flagged = [g["name"] for g in ad_groups if g["warnings"]]
    ctx.need_approval(f"Ad copy ready for {len(ad_groups)} ad groups."
                      + (f" Check flagged: {', '.join(flagged)}." if flagged else ""))


register_step("step4")(run)
