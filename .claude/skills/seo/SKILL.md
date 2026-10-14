---
name: seo
description: SEO keyword research + page plan for a NZ trades business - outputs a spreadsheet of service pages and content pages to build, each with its target keywords in priority order. Use when the user types /seo <trade> in <location>, or asks for SEO keyword research / an SEO page plan / "what pages should I build to rank".
argument-hint: <trade/services> in <location>   e.g. fence builder in palmerston north
---

# SEO page plan

Input: `$ARGUMENTS` - a trade (optionally a list of services) and a location,
e.g. `fence builder in palmerston north`, `concrete - driveways, paths, slabs, patios in manawatu`.

Output: `output/<trade>-<region>-seo/<trade>-seo-page-plan-<region>.xlsx` with
four tabs (Read Me, Page Plan, Keywords by Page, Excluded & Why) - same format
as `output/deck-builder-manawatu-seo/` and `output/concrete-manawatu-seo/`.

The user speaks plain business language. Never ask them for IDs, geo codes or
API details - resolve those yourself. Only ask if the trade or location is
genuinely ambiguous.

Run everything from the project root
(`/Users/liamemery/Desktop/Work Shit/Google Ads Campaign Builder`).
Scripts that hit Google Ads use `venv/bin/python`; `build_plan.py` uses
system `python3` (it has openpyxl, the venv doesn't). Write working files
(seeds/candidates/plan JSON) to the scratchpad or the output folder, not the repo root.

## Step 1 - Check for prior work on this trade

- `ls output/*-seo/` - if this trade (or a close one) already has an SEO plan,
  open its xlsx and reuse its page structure and keyword list as the starting
  point. Only the volume pull needs redoing for the new location.
- Also check `examples/` in this skill (the concrete run) for the shape of a
  finished seeds/candidates/plan set.

## Step 2 - Resolve the location

Known IDs: Palmerston North City `9117710`, Manawatu District `9117711`,
NZ `2554`. For anything else:
`venv/bin/python scripts/resolve_location.py "<place>"` - pick the City/District
entries. Combine a city with its surrounding district when the business serves
both (as Palmy + Manawatu does). Max 10 geo IDs.

## Step 3 - Discovery pull (see what people actually search)

Write `seeds.json` - one group per service, 4-7 seeds each, mixing
"<service>", "<service> near me", "<trade> <city>", cost and ideas phrasing.
Example: `examples/concrete-manawatu.seeds.json`.

```
venv/bin/python .claude/skills/seo/scripts/pull_ideas.py output/<proj> seeds.json --geo <ids> --match "<regex of trade words>"
```

Expect most local numbers to be floored at 10 and a lot of US junk
("per square foot", US-only terms). This step is only for discovering
phrasing and sub-services - **do not** use nationwide idea generation and
do not treat this output as the keyword list.

## Step 4 - Build a curated candidate list, grouped by planned page

Write `candidates.json`: `{"page group": [keywords...]}`. Draw from the
discovery output plus NZ phrasing you know people use (m2 not sq ft, "nz"
suffix, local council names, NZ products/systems). Per group include:
- core service terms + plurals/synonyms + "near me" / "contractors" / "company"
- `<term> <city>` / `<term> <nearby town>` combos (for possible location pages)
- cost terms ("cost nz", "cost per m2", "price", "quote")
- ideas/design, "vs" comparisons, how-long/how-thick/care questions, consent/council questions
Typically 400-700 candidates. Example: `examples/concrete-manawatu.candidates.json`.

```
venv/bin/python .claude/skills/seo/scripts/pull_volumes.py output/<proj> candidates.json --geo <ids>
```

Prints `keyword local/nz` per group (`cv` = Google merged it as a close variant).

## Step 5 - Design the page plan

Write `plan.json` (schema in `scripts/build_plan.py`'s docstring; full example
in `examples/concrete-manawatu.plan.json`).

**Scope**
- Services the user named -> P1 service pages.
- Other sub-services of the *same* trade (e.g. exposed aggregate, vehicle
  crossings for a concreter) -> P2/P3 service pages with a
  "Confirm they do X" note. Never add a different trade (gates for a fence
  builder, retaining walls/pavers for a concreter) as a page - list it in
  Excluded & Why as "not stated - add only if the client does this".
- Always exclude cheap/affordable/budget/free terms, retailer/product/supplier
  searches, US-only phrasing, other cities, DIY how-to with no buyer angle,
  jobs/training.

**Pages**
- Service pages: home page (`<trade> <city>`), one per main service, extras
  for sub-services. A town location page only if that town has recorded
  searches (>0) - otherwise just mention towns in copy.
- Content pages: cost/price guides (the most valuable - people pricing are
  close to buying), calculators if search volume exists, comparisons ("X vs Y"),
  ideas/gallery pages, council/consent guides, care/how-long/what's-normal
  guides. Write how-to topics as "what a good <trade> does / what to check in
  a quote" so they still sell.

**Keywords**
- Each keyword on exactly one page (the build script enforces this).
- Order within a page: rank 1 = primary (title/H1) - the most specific
  high-intent term for that page, usually the service term with the best NZ
  volume (or the `<trade> <city>` term for the home page). Then by local
  volume, then NZ volume, then intent.
- Drop 0/0 keywords unless they're the obvious local phrasing worth using in
  copy - list those in `keep_zero`.

**Priority**
- P1: home, every named service, the main cost guide(s), and any content page
  with standout local volume.
- P2: secondary services and the stronger supporting content.
- P3: services that need confirming as specialist/side work, and
  low-volume authority content.

**Notes column**: what to confirm with the client, what the page needs
(real prices, project photos, suburb names), which service page a content page
should link to.

## Step 6 - Build and check

```
python3 .claude/skills/seo/scripts/build_plan.py output/<proj> plan.json
```

It fails if a keyword is on two pages or wasn't in the volume pull - fix
the plan.json and re-run. Keep plan.json/candidates.json/seeds.json in the
output folder so the plan can be edited and rebuilt later.

Before reporting, check: every named service has a P1 page; every page has a
primary keyword; nothing in Excluded & Why also appears on a page; no
cheap/affordable terms anywhere.

## Step 7 - Report back

Short summary in chat (plain business language, no IDs):
- link to the xlsx and the page count
- P1 pages as a table (page | primary keyword), then P2 and P3 in brief
- 2-4 real insights from the data (biggest local term, thin local volume,
  which towns had searches, standout local angle)
- pages that depend on confirming services with the client
- what was deliberately left out
