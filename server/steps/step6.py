"""Step 5 in the web app (job key "step6") - sitelinks, callouts and structured
snippets (PROCESS.md Step 6).

Runs straight after ad copy; it no longer waits for landing pages. Each ad
group gets the same 6 sitelinks, pointed at that ad group's final URL (from the
approved ad copy) plus a section anchor. Claude writes the copy from real
business facts only; code then checks every limit and rule and sends
violations back for a fix.
"""

import json
import re

from .. import db, llm
from ..jobs import Blocked, register_step
from . import store

FACT_FIELDS = ("business_name", "trade", "services", "service_areas", "years_experience",
               "completed_projects", "certifications", "guarantee", "reviews", "differentiators",
               "other_info", "scope_notes")
# Sections present on every landing page of the LFT template.
ANCHORS = ("quote", "reviews", "work", "why-us", "how-it-works", "service-area")
LIMITS = {"text": 35, "description": 25, "callout": 25, "snippet": 25}
BANNED = re.compile(r"[—–]|\b(cheap|affordable|budget|free)\b(?! (on-site |no-obligation )?(quote|measure|estimate))", re.I)

RULES = f"""\
GOOGLE ADS EXTENSION RULES (NZ trades):
- Exactly 6 sitelinks. Per sitelink: "text" (max {LIMITS['text']} chars), "description_1" and
  "description_2" (max {LIMITS['description']} chars each), and "anchor", one of {list(ANCHORS)}
  (the page section it jumps to). Use a different anchor for each sitelink.
- Exactly 6 callouts (max {LIMITS['callout']} chars each), account-wide, benefit focused.
- 1 structured snippet: "header" must be one of Google's headers (Services, Types, Brands,
  Styles, Amenities, Courses, Models, Neighborhoods, Service catalog, Destinations,
  Insurance coverage, Featured hotels, Degree programs, Shows); "values": 4 to 8 items, max
  {LIMITS['snippet']} chars each, taken from the services actually offered.
- Everything must come ONLY from the business facts given. Never invent a credential, stat,
  rating, year count, review count, guarantee or service. Generic unverifiable lines like
  "Free On-Site Quote" or "Fully Insured" (only if insured is in the facts) are fine.
- Style examples: "5-Star Rated", "See Our Work", "Free Measure & Quote", "Fully Licensed".
- NEVER use em dashes or en dashes, and avoid AI-slop phrasing. Never use the words
  cheap, affordable or budget. Title Case. Say "near you", never "near me".
"""


def validate(data):
    problems = []
    sl = data.get("sitelinks", [])
    if len(sl) != 6:
        problems.append(f"need exactly 6 sitelinks, got {len(sl)}")
    texts = []
    for s in sl:
        for key, limit in (("text", LIMITS["text"]), ("description_1", LIMITS["description"]),
                           ("description_2", LIMITS["description"])):
            v = s.get(key, "")
            texts.append(v)
            if not v or len(v) > limit:
                problems.append(f'sitelink {key} must be 1-{limit} chars ({len(v)}): "{v}"')
        if s.get("anchor") not in ANCHORS:
            problems.append(f'sitelink anchor must be one of {list(ANCHORS)}: "{s.get("anchor")}"')
    callouts = data.get("callouts", [])
    if len(callouts) != 6:
        problems.append(f"need exactly 6 callouts, got {len(callouts)}")
    for c in callouts:
        texts.append(c)
        if not c or len(c) > LIMITS["callout"]:
            problems.append(f'callout must be 1-{LIMITS["callout"]} chars ({len(c)}): "{c}"')
    snip = data.get("structured_snippet") or {}
    values = snip.get("values", [])
    if not snip.get("header"):
        problems.append("structured_snippet needs a header")
    if not 4 <= len(values) <= 8:
        problems.append(f"structured snippet needs 4 to 8 values, got {len(values)}")
    for v in values:
        texts.append(v)
        if not v or len(v) > LIMITS["snippet"]:
            problems.append(f'snippet value must be 1-{LIMITS["snippet"]} chars ({len(v)}): "{v}"')
    for t in texts:
        if BANNED.search(t):
            problems.append(f'banned dash/word in: "{t}"')
        if re.search(r"\bnear me\b", t, re.I):
            problems.append(f'use "near you", not "near me", in: "{t}"')
    return problems


def _final_urls(project_id, ad_groups):
    """Approved final URLs per ad group (latest step4 approval), else whatever step4.json holds."""
    urls = {g["name"]: g.get("final_url", "") for g in ad_groups}
    rows = db.query("SELECT payload FROM approvals WHERE project_id=? AND step='step4' ORDER BY id DESC LIMIT 1",
                    (project_id,))
    if rows:
        for name, url in (json.loads(rows[0]["payload"]).get("final_urls") or {}).items():
            if url:
                urls[name] = url
    return urls


def _join(base, anchor):
    return f"{base.rstrip('/')}#{anchor}" if base else f"#{anchor}"


def run(ctx):
    s0 = store.read(ctx.project_id, "step0") or {}
    s4 = store.read(ctx.project_id, "step4") or {}
    if not s4.get("ad_groups"):
        raise Blocked("Sitelinks need approved ad copy first - finish the Ad Copy step.")
    detail_fields = ("years_experience", "completed_projects", "certifications", "guarantee", "reviews",
                     "differentiators", "other_info")
    if not s0.get("business_name") or not any(s0.get(f) for f in detail_fields):
        raise Blocked("I can't write the sitelinks yet - I need the business information (name plus real "
                      "details like years trading, jobs completed, reviews or guarantees). Add it under "
                      "'Business info' and this step will restart automatically.")
    facts = {k: s0[k] for k in FACT_FIELDS if s0.get(k)}
    note = ctx.payload.get("note", "")
    previous = store.read(ctx.project_id, "step6") if note else None

    groups = [g["name"] for g in s4["ad_groups"]]
    user = f"""\
Business facts (the ONLY facts you may use):
{json.dumps(facts, indent=1)}

Ad groups these extensions serve: {json.dumps(groups)}
{('CHANGE REQUEST FROM THE USER (apply this): ' + note) if note else ''}
{('Previous version (revise it): ' + json.dumps({k: previous.get(k) for k in ('callouts', 'structured_snippets')})) if previous else ''}

Return JSON: {{"sitelinks": [{{"text": "", "description_1": "", "description_2": "", "anchor": ""}}] (6),
"callouts": [6], "structured_snippet": {{"header": "", "values": []}}}}"""
    data = llm.complete_json(ctx, RULES, user, max_tokens=3000)
    for _ in range(2):
        problems = validate(data)
        if not problems:
            break
        ctx.log(f"fixing {len(problems)} rule problems")
        data = llm.complete_json(ctx, RULES, user + "\n\nYour previous answer:\n" + json.dumps(data)
                                 + "\n\nFix these problems and return the full corrected JSON:\n- "
                                 + "\n- ".join(problems), max_tokens=3000)
    problems = validate(data)

    urls = _final_urls(ctx.project_id, s4["ad_groups"])
    base_fallback = f"https://{s0['domain']}" if s0.get("domain") and not str(s0["domain"]).startswith("http") \
        else s0.get("domain", "")
    ad_groups = []
    for name in groups:
        base = urls.get(name) or base_fallback
        warnings = list(problems) if name == groups[0] else []
        if not urls.get(name):
            warnings.append("No landing page URL yet - links point at the site's domain (or just the anchor) "
                            "until landing pages are built; update the URLs then.")
        ad_groups.append({
            "name": name,
            "sitelinks": [{"text": s["text"], "description_1": s["description_1"],
                           "description_2": s["description_2"], "url": _join(base, s["anchor"])}
                          for s in data.get("sitelinks", [])],
            "warnings": warnings,
        })

    snip = data.get("structured_snippet") or {}
    count = (sum(len(g["sitelinks"]) for g in ad_groups) + len(data.get("callouts", []))
             + len(snip.get("values", [])))
    store.publish_step(ctx.project_id, "step6", {
        "project_id": ctx.project_id, "step": "step6", "label": store.project_label(ctx.project_id),
        "ad_groups": ad_groups, "callouts": data.get("callouts", []),
        "structured_snippets": {"header": snip.get("header", ""), "values": snip.get("values", [])},
    }, row_count=count)
    ctx.need_approval(f"Sitelinks, callouts and snippets ready for {len(ad_groups)} ad groups."
                      + (" Some lines are flagged." if problems else ""))


register_step("step6")(run)
