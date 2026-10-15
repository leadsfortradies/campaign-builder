# Campaign Build Process

This is the process to follow when asked to "build a Google Ads campaign for
<business>". Work through the steps in order; stop for review/approval where
noted. The user interacts in plain business language only — never ask them
for technical IDs or API parameters; resolve those internally.

**Scope discipline:** only research/include services the user explicitly
states for that business. Never add an "obviously adjacent" trade on your own
judgment (e.g. gates for a fence builder, retaining walls for a deck/fence
builder, staining/repair for a builder) unless the user names it. A keyword
that mixes a named service with an unstated one (e.g. "fence and gate
company") gets excluded too, not kept because half the phrase matches. Each
client gets their own Ads account, so scope creep here means wasted spend on
services that client can't fulfil.

## Step 0 - Setup (business info) — IMPLEMENTED

Collected through the web app's "New campaign" form (new.html, added
2026-10-15 for phone use - logo/photos upload from the phone's camera roll)
and editable any time from the project page's "Business info" link. The
older chat-based route below still works.

1. Collect as much of the following as is available. **Only services and
   service area are required to start a build** (decided 2026-10-15 - the user
   is often on their phone without a logo or business details to hand, and a
   build should still start without them). Everything else is optional; a
   missing item blocks only the step that actually needs it, and the user is
   told which one and why:
   - **Services** and **service area/s** - needed for Step 1 keyword research
     (a build can't start without them).
   - **Business name** plus real details (years of experience, estimated
     number of completed projects, certifications, guarantees, reviews,
     awards, other reasons to choose them) - needed for Step 4 ad copy, which
     must never invent facts. If missing when Step 4 is reached, stop and
     tell the user the ad copy can't be written without the business info.
   - **Business logo** and **photos** (completed work, team) - needed to
     finish Step 5 landing pages. Landing pages can still be built without
     them, but flag clearly that they're incomplete until the logo/photos
     are added.
   - Business phone number and email (NZ number) - used for lead delivery
     later, not Step 4/5 copy.
2. The user can hand all of this over in one go, or piecemeal across the
   conversation - there's no form to fill in, so just keep track of what's
   been given and what's still missing.
3. Any image file (logo, work photos, team photos) the user shares in chat
   gets copied into `web/data/<project-id>/assets/` (not left wherever the
   user originally dropped it) so it's still there when Step 4/5 need it.
4. Persist everything collected so far with
   `scripts/lib/webapp_export.py`'s `write_step0_business_info()` (or via
   `scripts/webapp_sync.py step0 <project-id> "<label>" <info.json>`) -
   writes `web/data/<project-id>/step0.json`. Safe to call repeatedly as
   more info comes in; re-run it to fill in gaps rather than overwriting
   with incomplete data.
5. Don't re-ask for anything already sitting in `step0.json` - read it
   first. If the starred fields are still missing when Step 4 or Step 5
   comes up, that's the point to ask, not before (no need to interrupt
   Step 1-3's keyword work for info that isn't needed yet).

## Step 1 - Keyword Research (Keyword Planner) — IMPLEMENTED

**Reuse prior keyword research for the same industry** (added 2026-10-07,
revised 2026-10-07 after the Taupo painting run) - if this trade has already
been through Step 1 for a different location (e.g. a deck builder in
Auckland, now doing a deck builder in Christchurch), check that project's
approved `web/data/<project-id>/step1.json` first. The core keyword set for
a given trade is largely location-independent - same services, same
customer search behaviour, same classification calls already made and
user-corrected - so the prior run's classification (BOF Priority 1/2 vs
Price Discovery vs Manual Review vs Excluded, and the account-specific
negative list) is a strong prior for this run, not a from-scratch judgment
call. Cross-check new results against the prior run's categorization before
presenting for review, and flag anywhere the new run disagrees with how the
same keyword was classified before.

**Getting volume for the new location - do not default to nationwide**
(added 2026-10-07, Taupo painting run): the instinct when a small location's
own geo-targeted Keyword Planner numbers come back flat (everything floored
at the 10/mo minimum via `GenerateKeywordIdeas`) is to fall back to running
research NZ-wide instead. **Don't** - nationwide idea-generation pulls in a
huge amount of genuinely irrelevant long-tail (other-city keywords, overseas
brand names, unrelated trades picked up by semantic expansion) that reads as
plausible but will never get searched from the actual service area, and
inflates Priority 1 with junk. Instead:
1. Build the candidate keyword list from the prior same-industry project's
   already-approved keywords (see above) plus, for any service that prior
   project doesn't cover, a tight manually-reasoned seed list for just that
   service (not a broad nationwide idea-generation pull).
2. Look up **real volume for the new location** via exact-phrase
   `GenerateKeywordHistoricalMetrics` against that candidate list and the
   new location's own geo target constant (same technique as Step 2 -
   `scripts/lib/keyword_planner.py`'s `get_keyword_historical_metrics`) -
   not idea-generation, since the candidate list is already known.
3. **A low-population location's historical metrics will often only return
   a binary signal** - 0, or the 10/mo floor, with nothing in between (true
   for Taupo, pop. ~25k) - rather than a genuinely differentiated number.
   That's still real and worth having: it tells you whether Google has
   *any* recorded search presence for that exact phrase in that location,
   which is what actually matters for a small-town campaign, even though it
   can't rank keywords against each other by volume the way a bigger city's
   numbers can. Treat **0 at the new location as "no verified local demand -
   leave it out of the build"**, not as a negative-keyword-worthy
   irrelevance signal (it's a data-quality gap, same as the existing
   10/mo-floor rule in item 7 below) - and don't fall back to the nationwide
   number to rescue it.
4. When volume can't differentiate within the "has signal" group (the usual
   case for a small town), fall back to intent-tier alone (see the Priority
   1/2 rubric below) to rank/split - and remember **Priority 1 has no hard
   cap regardless of how volume behaves** - a keyword with genuine Tier A/B
   signal goes to Priority 1 even when every keyword in the set is tied at
   the same reported volume. When unsure whether to include a high-intent
   keyword, include it - excluding a real buyer-intent keyword is the worse
   mistake, not the safer one.

1. User describes the business: what services it offers, and where (e.g. "a
   deck/fence/retaining wall builder in Auckland").
2. Derive seed keywords per service and run them through Keyword Planner
   (`scripts/keyword_research.py`, via `scripts/lib/keyword_planner.py`).
   Find high-intent, bottom-of-funnel keywords, e.g.:
   - deck builder near me
   - deck building company auckland
   - fence builder near me
3. Split these into **"BOF - Priority 1"** and **"BOF - Priority 2"** (see
   "Bottom of Funnel: Priority 1 vs Priority 2 split" below) rather than one
   flat "Bottom of Funnel" bucket.
4. Also find price-discovery keywords, e.g.:
   - how much does it cost to build a deck
   - deck build cost calculator
5. Label these **"Price Discovery"**.
6. Anything else worth including that doesn't fit cleanly goes in a separate
   **"Manual Review"** bucket. Campaigns must stay focused and relevant to the
   specific business — exclude top-of-funnel/educational keywords (e.g. "how
   to build my own deck", "bunnings decking timber").
7. Minimum 10 average monthly searches to keep a keyword
   (`--min-searches 10`).
8. Exclude keywords that are irrelevant to the core service or clearly DIY,
   e.g.:
   - deck staining near me (not relevant to deck *building*)
   - how to repair my deck (DIY)
   - how to build a deck (DIY)
9. **Every keyword excluded for being irrelevant/wrong-intent (step 8 above,
   plus the "Standing classification rules" below - DIY, wrong trade/service,
   design, security gate, farm/rural/ag fencing, cheap/affordable, product-
   price-not-service-price, etc.) goes onto this account's own Negative
   Keyword list** - added 2026-10-07, so this traffic gets blocked at the
   account level instead of just silently not being bid on. This is **separate
   from and in addition to** the standing cross-client list at
   `data/global_negative_keywords.csv` (see Step 8) - that file is generic
   terms that apply to every account regardless of trade (jobs/careers,
   training/DIY, retailers, wrong location, etc.); this account-specific list
   is the irrelevant terms that actually surfaced *for this business* during
   this KWR pass. Don't add keywords dropped only for missing the 10/mo
   search-volume floor (step 7) - that's a data-quality cutoff, not a sign the
   query itself is irrelevant, so it doesn't belong in a negative list.
   Judgement call on match type, same as the global CSV's convention: phrase
   match (quoted) when several excluded keywords share one problem word/phrase
   worth blocking broadly (e.g. "staining", "design", "security gate"), exact
   match for a one-off irrelevant phrase that doesn't generalize. Save this
   list alongside the rest of this step's output so Step 8 can pick it up.
10. **Stop and present the categorized list for the user's review and
   approval before moving to Step 2.** Output includes a `note` column: blank
   for Bottom of Funnel / Price Discovery rows, filled in for every Manual
   Review row explaining why it needs a human decision (e.g. "includes patio,
   which isn't a stated service", "repair intent, not new build"). The
   account-specific negative keyword list from step 9 is included in this
   review too.

### Bottom of Funnel: Priority 1 vs Priority 2 split (added 2026-10-06)

Local-service BOF keyword lists blow out to 200-300+ entries, almost all
long-tail wording variants sitting at the 10/mo search-volume floor. That's
unnecessary bloat, especially since Google Ads exact match already matches
close variants - an exact-match keyword "house painter" already triggers for
"house painter near me" and similar phrasing, so keeping both as separate
keywords adds no incremental reach, just campaign clutter. Nothing gets
deleted though - every BOF keyword that clears the normal Step 1 bar still
ends up in the final list, just split into two priority tiers instead of one
flat bucket:

- **BOF - Priority 1** - the core, highest-intent set. Launched first.
- **BOF - Priority 2** - every other real BOF keyword. Launched later, once
  Priority 1 is proven, to pick up additional volume.

This split is a judgment call made while reading the raw Keyword Planner
data, the same way Bottom of Funnel vs Price Discovery vs Manual Review
classification already is - not a rigid scoring script. Apply this rubric:

1. **Group by service.** Use the services the user actually stated for the
   business (e.g. house painting / interior / exterior / roof). A keyword
   that doesn't name a specific sub-service (e.g. "painting companies near
   me") counts toward the general/umbrella service.
2. **Collapse close-variant clusters before ranking.** Keywords that differ
   only by a locality synonym ("near me" / "in my area" / "nearby" / "close
   to me" / "local"), pluralization, word order, or a minor function word are
   the same underlying query intent - Google's close-variant matching
   already bridges them. Only the best-volume phrasing in a cluster competes
   for Priority 1; the rest of the cluster falls to Priority 2 rather than
   being kept as separate near-duplicate Priority 1 entries.
3. **Score the survivors by intent tier:**
   - **Tier A** (strongest): locality marker *and* a business-entity word
     ("company/companies/contractor(s)/services") both present - e.g.
     "painting companies near me".
   - **Tier B**: trade noun + one of (locality marker OR business-entity
     word) - e.g. "roof painters near me", "painting company".
   - **Tier C**: bare trade noun or a hiring qualifier only ("professional
     painter", "house painter").
4. **Rank Tier A > B > C within a service, except volume can override
   tier** when the gap is large (roughly 3x+) - e.g. "house painter" (300
   searches/mo) beats "house painter near me" (10 searches/mo) despite
   scoring a lower tier.
5. **Fill Priority 1 per service**, floor of 5 keywords minimum. Beyond the
   floor there's no hard cap - use judgment on where genuine hiring-intent
   quality tapers off into redundant/low-value long tail. As a rough
   starting guideline this tends to land around 10-12 per service, but let
   actual data quality decide rather than forcing a number; a business with
   more stated services naturally ends up with a larger Priority 1 set in
   total, not squeezed to fit a fixed ceiling. **This means literally no
   cap, ever, in code or in judgment** - every Tier A or Tier B keyword
   belongs in Priority 1 regardless of volume, even if that makes a service's
   Priority 1 set much bigger than "10-12". Corrected 2026-10-07 (Taupo
   painting run) after a scripted version of this rubric imposed a 12-per-
   service cap and silently bumped "house painters near me" / "home painters
   near me" (880 searches/mo, the two highest-volume keywords in the entire
   dataset) down to Priority 2 - caught and corrected by the user, who was
   explicit: **when unsure whether a keyword belongs in Priority 1, include
   it rather than exclude it.** The cost of a too-big Priority 1 is trivial
   (the user trims it in the web app review); the cost of silently dropping
   a genuine high-intent keyword is not.
6. **Everything else stays Bottom of Funnel but goes to Priority 2** -
   never dropped, never moved to Manual Review or Excluded for this reason
   alone.

### Review happens in the web app, not raw CSV

Review happens in a **local-only** web app (switched from Netlify to a local
Python server 2026-10-06 - no more deploy credits burned per update, no more
Netlify MCP round-trip to read an approval). Run it with
`venv/bin/python scripts/local_server.py` (default port 8787) and open
`http://localhost:8787`. It's a **multi-project app**:

- `index.html` - Projects list. Each card is one business/campaign, with a
  status badge per step (not started / pending_review / approved / skipped).
- `project.html?id=<project-id>&step=<step>` - a project's detail page, with
  tabs across whichever steps have data. Same grouped-review-table UI is
  reused for Step 1 (grouped by category) and Step 3 (grouped by ad group) -
  `web/js/review.js` is the generic renderer, driven by a `group` field in
  the row data so neither step needed its own UI code. A skipped step (e.g.
  Step 2 for a big metro) shows a plain note card instead of a table.
- User clicks X to exclude keywords, then **"Approve this step"**, which
  POSTs the kept list as JSON to `/approve` on the local server.

**To pick up an approval:** `scripts/local_server.py` writes each approval
straight to `web/approvals/<project-id>__<step>__<timestamp>.json` - just
read that file directly (`project_id` / `step` say which project/step,
`kept_keywords` is the approved list). No MCP calls, no jq workaround.
Delete or move the file once picked up so it doesn't get re-processed.

**To push a new or updated step's results into the web app:**
`venv/bin/python scripts/webapp_sync.py step1 <project-id> "<label>" <csv>`
(or `step2`/`step3`, or `skip <project-id> "<label>" <step> "<note>"`) - this
writes `web/data/<project-id>/<step>.json` and updates `web/projects.json`.
Nothing to deploy - the local server reads straight off disk, so a browser
refresh picks up the change immediately.

### Standing classification rules (apply every run, don't re-ask)

- **Cost/price calculators and estimators are always Price Discovery**, never
  Manual Review - any keyword containing "calculator" or "estimator" where
  the subject is cost/price/budget/quote (e.g. "deck railing cost
  calculator", "fence replacement cost estimator").
- **Exclude anything about "design"/"designer"** (e.g. "deck designers near
  me", "composite deck designer") - not relevant to a builder.
- **Exclude security gate / security fencing terms** - not a stated service
  unless the user names security fencing explicitly.
- **Exclude farm / rural / agricultural / livestock fencing terms** - wrong
  customer segment for an urban residential fence/deck builder. Boundary
  fencing is fine to keep (applies to residential properties too), it's only
  the farm/rural/ag/livestock-specific terms that go.
- **Exclude niche/unfamiliar product-brand install terms** unless the brand
  is mainstream and NZ-relevant (keep Modwood, Kwila, Colorbond; drop things
  like "Millboard installers" - unclear relevance, delete rather than
  Manual Review).
- These rules came from user corrections on the first test run (deck/fence
  builder, Auckland, 2026-10-05) - see git history / PROCESS.md changes for
  context, but apply them going forward without re-litigating.
- **Bottom of Funnel requires an explicit hiring/business signal in the
  keyword itself** - the trade noun ("painter(s)", "builder(s)"), a
  business-entity word ("company/companies/contractor(s)/services"), a
  locality marker ("near me/in my area/nearby/local"), an explicit
  request-to-have-it-done phrasing ("paint my house", "get your house
  painted"), or a hiring qualifier ("hire", "professional", "handyman",
  "reputable", "0800", etc - but NOT "cheap"/"affordable", see below). A
  bare "activity + surface/
  material" description with **none** of these (e.g. "painting brick
  homes", "interior house painting", "repaint brick house", "roof
  respray") is top-of-funnel/exploratory by default - it reads as the
  searcher researching the topic, not ready to hire - and gets Excluded,
  not Bottom of Funnel. Don't default-include a generic head term just
  because it's on-topic; the signal word has to actually be present. Caught
  on the painting/Canterbury test run (2026-10-05) after wrongly bucketing
  "painting brick homes" and "painting walls white" as Bottom of Funnel.
- **"Near me" / "company" / "services" etc. don't override the scope
  rule** - a keyword can carry a hiring signal and still be excluded if the
  service itself isn't stated (e.g. "kitchen cabinet painters near me",
  "floor painters near me", "epoxy painters near me", "drywall and painting
  contractor near me", "paint stripping companies near me" for a painting
  company that was only described as doing exterior/interior/roof work).
  Check scope before counting the hiring signal.
- **Never include "cheap" / "affordable" / "cheapest" / "budget" /
  "low cost" / "free" price-positioning terms, in any category, for any
  trade.** Exclude outright (e.g. "cheap house painters", "affordable roof
  painting", "affordable exterior painters near me", "free installation
  home security system") rather than treating the hiring signal
  (painter/company/near me/installer) as enough to keep them. Standing rule
  from 2026-10-05 ("cheap"/"affordable"/"budget"/"low cost"), extended to
  "free" 2026-10-09 (security + data cabling / Hamilton run) - don't
  re-ask, applies to every future build regardless of trade. When writing a
  one-off classify script for a new trade rather than reusing an existing
  one, build this in explicitly near the top of the hard-excludes - it
  doesn't reliably fall out of the other exclusion rules on its own (missed
  once on the Hamilton run, letting "cheap cctv camera installation"
  through to Priority 2).
- **Painting-specific scope excludes** (added 2026-10-07, Taupo run - same
  "near me doesn't override scope" principle as above, specific themes worth
  naming so they're not re-derived from scratch each time): **road/line
  marking** ("road painting", "line painting", "curb painting" - a different
  trade entirely); **concrete/epoxy/garage-floor coatings** and **floor
  painting generally** - different trade/material scope from house/deck/
  fence painting, exclude even when phrased as "X painters near me", not
  just "X painting"; **paint stripping/removal** (removal, not application -
  different job); **paint matching/mixing services** (a retail paint-shop
  counter service, not a painting contractor's job); **overseas paint brand
  names** (Nippon, Asian Paints, Berger, Benjamin Moore, Sherwin Williams -
  not NZ-relevant, almost always keyword-planner noise from semantic
  expansion); **brand-specific accreditation claims** ("Dulux accredited
  painters" etc.) unless the business actually holds that accreditation -
  risk of an implied claim the business can't back up; **narrow single-
  building-component framing** ("gutter painters", "shutter painters",
  "trim painter", "room painter") - grammatically on-topic but not how a
  real customer searches for a whole-house painting company, reads as
  long-tail noise rather than genuine intent; **subcontractor/trade-
  recruitment phrasing** ("painters wanted", "looking for painters",
  "contractors looking for painters") - a business or tradesperson, not a
  homeowner-customer.
- **Nationwide Keyword Planner data pulls in a lot of this kind of junk
  that a tighter, location-scoped pull wouldn't** - see "Getting volume for
  the new location" above. These examples came from a nationwide NZ pull
  for a small town (Taupo) specifically because the broad semantic expansion
  surfaces things a tight, prior-research-reused candidate list wouldn't.
  **Never go nationwide unless the user explicitly asks for it** (the web
  app only does so if the scope notes/change request say "NZ-wide" or
  "nationwide"; otherwise it researches the service area only and blocks if
  the area can't be matched to a location). When it is asked for,
  **scrutinize classification harder**, since more junk will be mixed in
  with genuine signal.
- **Distinguish paint product pricing from service pricing.** "cost to
  paint X" / "X painting cost" / "quote for painting X" = Price Discovery.
  Bare "<material> paint price/prices" (e.g. "roof paint price", "metal
  roof paint price", "5l roof paint price") is someone pricing the tin of
  paint, not the job - exclude it as a product query, not Price Discovery.

## Step 2 - Location-Based Keywords — IMPLEMENTED

1. For each main service offering, identify the 2-5 keywords responsible for
   the bulk of search volume (e.g. "deck builders near me" -> base term
   "deck builder").
2. Identify the specific locations within the target region (resolve via
   `scripts/resolve_location.py` - user gives plain place names, Claude
   derives the actual list and IDs, doesn't ask the user for IDs).
3. Build location-specific keyword variants (e.g. "deck builders palmerston
   north") and pull **exact-phrase** search volume via
   `scripts/step2_location_keywords.py` (uses
   `GenerateKeywordHistoricalMetrics`, not idea-expansion, since we already
   know the exact phrases we want - `lib/keyword_planner.py`'s
   `get_keyword_historical_metrics`). Max 10 geo_target_constants per API
   call and metrics aggregate across whatever locations are passed together,
   so the script calls once per location to get a true per-location
   breakdown.

### Big single metro vs. distinct towns (decided 2026-10-05, Auckland test run)

Suburb-level exact-phrase keywords return near-zero volume for a single big
metro (tested: 16 Auckland suburbs x 7 base terms = 109 phrases, only 1 had
any measurable volume). This isn't a bug - people searching locally mostly
type "deck builder near me" or just the city name, not "deck builder
albany". The Manawatu example in this doc works because those are
**separate, distinct towns/cities** (Palmerston North, Feilding, Ashhurst),
not suburbs of one metro - people do type the town name there.

**Rule:** before running step 2's suburb/location expansion, judge whether
the target area is (a) a single large metro (Auckland, Wellington,
Christchurch) - in which case **skip suburb-keyword expansion entirely**.
Rely on the city-wide + "near me" terms already produced by Step 1, and
handle suburb-level reach through the Google Ads campaign's own
location-targeting settings (not keyword text) when the account gets built.
Or (b) a region made up of genuinely separate towns (like Manawatu) - in
which case run step 2 as designed, it'll show real volume per town.

## Step 3 - Organise Keywords into Ad Groups (STAGs) — IMPLEMENTED

0. **Campaigns step (before ad groups).** After Step 2 is approved the app asks
   which campaigns to build (BOF - Priority 1, BOF - Priority 2, Price Discovery)
   and whether Priority 1 + 2 are combined into one campaign ("BOF - Priority 1
   & 2"). Keywords in unchosen campaigns are left out of Step 3; Step 4 writes
   ad copy for the combined campaign, else Priority 1, else Priority 2.

1. **There are three campaigns: BOF - Priority 1, BOF - Priority 2, and
   Price Discovery** (updated 2026-10-06 - was two campaigns before the
   Priority 1/2 split existed). Campaigns are the top-level container in
   Google Ads, above ad groups - a single ad group cannot belong to more
   than one. Every STAG theme therefore splits into up to three versions
   based on each keyword's actual category from Step 1, even though they
   share the same theme name (e.g. "Timber Decks" can exist as its own ad
   group under *all three* campaigns, scoped separately - that's normal, ad
   groups are scoped within their parent campaign so there's no naming
   conflict). **Do not merge keywords from different campaigns into one ad
   group** - this was a real mistake caught by the user on 2026-10-05, see
   `scripts/compile_step3_adgroups.py`'s `assign_campaign()`. The intent
   behind three campaigns instead of one Bottom-of-Funnel campaign: launch
   Priority 1 first (core, highest-intent keywords), then Priority 2 once
   Priority 1 is proven out, then Price Discovery - cheapest/highest-intent
   keywords first, broaden from there.
2. Within each campaign: Single Themed Ad Groups (STAGs) - one tightly-scoped
   theme per ad group. E.g. "Timber Decks" ad group: timber deck builder,
   timber decks near me. "Composite Decks" ad group: composite decking
   installation, composite deck builder.
3. Keywords originally labeled "BOF - Priority 1" / "BOF - Priority 2" /
   "Price Discovery" in Step 1 map straight to their matching campaign. Kept
   "Manual Review" keywords were never given any of those labels, so each
   needs individual judgment: default to **BOF - Priority 2** (most are
   service/hiring intent, but weren't confirmed as core Priority 1 keywords),
   explicit cost-questions go to Price Discovery - see
   `MANUAL_REVIEW_TO_PRICE_DISCOVERY` in the script for the exact list and
   reasoning.
4. Every keyword from Steps 1-2 must end up assigned to an ad group (within
   the correct campaign).

## Step 4 - Writing The Ad Copy — IMPLEMENTED

1. **Never use em-dashes or other classic AI-slop tell-tales** in ad copy.
2. Unless the user explicitly says otherwise, only write ad copy for **BOF -
   Priority 1** - that's the campaign that actually launches first.
3. Per ad group: 15 headlines (max 30 chars), 4 descriptions (max 90 chars),
   2 display URL paths (max 15 chars).
4. **3 of the 15 headlines are pinned to position 1** and written to be as
   close to exact-match as possible against that ad group's keywords (for
   quality score and CTR) - e.g. trade term + "near me" / + the city name /
   + the region name, picked from the ad group's actual highest-volume
   keyword phrasing.
5. **The other 12 headlines are benefit-oriented** and must come from real
   input the user has given about the business (years trading, project
   count, review count/rating, insurance, press features, process
   differentiators, service area, etc.) - never invent a qualification,
   credential, or stat. The only headlines that can be invented are generic,
   unverifiable ones like "Satisfaction Guaranteed" or "Free No-Obligation
   Quote". Business-level trust signals like these are shared across all ad
   groups in the campaign (they're facts about the business, not the
   keyword); 1-2 per ad group can be swapped for a more specific real detail
   when the business has one for that service (e.g. "Rust Treated & Primed"
   for a roof-painting ad group instead of a generic prep line).
5b. **"Near me" only appears in the 3 pinned keyword headlines.** In
   descriptions and benefit headlines write it naturally: "Need a bathroom
   contractor near you? LBP licensed, Site Safe, 10 years of experience." -
   never "Need bathroom contractors near me?" (enforced in
   `server/steps/step4.py`'s `validate()`; "near you" still counts as matching
   a "near me" keyword for rule 6).
6. **Every description must include at least one of that ad group's actual
   keywords** (verbatim or very close to it), not just generic sales copy.
7. Before writing any of this, get the real business facts from the user -
   check this project's `web/data/<project-id>/step0.json` (Step 0) first.
   If it's missing or incomplete on the starred fields (business name,
   logo, service areas), or thin on the optional ones (years trading,
   review count, credentials, guarantees), ask the user directly for what's
   missing (or pull from the business's live website if the user points to
   one) rather than guessing or inventing it - then save the answer back to
   `step0.json` so it's there for Step 5 and any future ad-copy refresh.
8. Source: checked against the live business website on the date of the
   build - re-verify stats like review count against the business's current
   Google listing before reusing an older ad-copy build, since review counts
   and project counts climb over time.

> **Order change (2026-10-15):** in the web app, Sitelinks/Callouts/Snippets now
> run as **Step 5** and Landing Pages as **Step 6** (sitelinks no longer wait for
> landing pages). Internal keys/files are unchanged: `step6.json` = sitelinks,
> `step5.json` = landing pages. Step 5 (sitelinks) has an "Export To PDF" button
> that bundles ad copy + extensions for client approval.

> **Auto-link (2026-10-15):** when landing pages are approved in the web app,
> a background job (`server/steps/link_urls.py`) copies each ad group's URL into
> the ad copy's final URL (`step4.json`) and into that ad group's sitelinks
> (`step6.json`, keeping each #anchor). No review needed.

## Step 5 - Landing Pages (shown as **Step 6** in the web app) — IMPLEMENTED

(Numbering note: the web app shows Sitelinks/Callouts/Snippets as Step 5 and
Landing Pages as Step 6. Data keys are unchanged: `step6.json` = sitelinks,
`step5.json` = landing pages.)

1. Covers whichever campaign's ad groups currently have ad copy (currently
   **BOF - Priority 1**, same scope as Step 4).
2. The web app's Landing Pages tab offers three options per project:
   - **Option 1 - "Build from scratch"** (`build_template`): the app builds
     every landing page from the LFT site template, **plus privacy, terms and
     index from the template**. Template styling is untouched.
   - **Option 2 - "Build with the client's branding"** (`build_designed`): the
     same template pages, restyled with the client's logo, fonts and colours
     read from their website (link entered in the tab, saved as
     `design_source_url`). Landing pages and index only; **privacy and terms are
     copied straight from the client's site** (never from the template).
   - **Option 3 - "I already have the links"** (`urls`): a text input per ad
     group for that ad group's landing page URL. Nothing is built.
3. Options 1 and 2 run as a background job (`server/steps/step5.py`, started by
   `POST /api/landing/start`). It: clones the template repo
   (`leadsfortradies/site-template`, the GitHub copy is the source of truth);
   groups the ad groups into landing pages (one page per service plus one
   general page); has Claude caption the client's photos and write the page copy
   from Step 0 facts only; fills the template's `content/lp-master.html`
   (`server/steps/lp_site.py`); checks no template-client text or missing image
   survives; pushes to a new private GitHub repo (`<project-id>-landing-pages`)
   and deploys to a new Netlify site; then publishes the links for review.
   Needs `GITHUB_TOKEN` and `NETLIFY_AUTH_TOKEN` (see DEPLOY.md).
4. Reviews and approval happen in the web app. **Approving the landing pages
   runs the background `link_landing_pages` job**, which copies each ad group's
   URL into the ad copy final URL and into that ad group's sitelinks (keeping
   each #anchor). No further review needed.
5. Option 2 subdomain: the user enters the live address in the tab (optional);
   the app attaches it to the Netlify site and shows the CNAME to add. **The
   user does the DNS by hand.** The tab shows two link sets: the Netlify links
   (for review) and the final domain links. **Ad copy and sitelinks ALWAYS use
   the final domain links, never the Netlify ones** - even before DNS resolves.
   The tab asks "Is the final domain connected?" and **no campaign is uploaded
   (Step 8) until the user confirms it there** (`domain_connected` in step5.json;
   `step8_upload_campaign.py` refuses otherwise). Brand fonts and dark colours are
   read from the client's CSS (not picked by Claude); the favicon is the live
   site's own; a light logo gets a dark nav.
6. Required before a build: business name, services, service area, phone and a
   logo, plus at least 3 job photos (option 2 falls back to the client site's
   images). A missing item blocks with a notification. Reviews, GTM container
   ID and rating line are used only if supplied in Step 0 (`review_quotes`,
   `gtm_container_id`, ...); otherwise the section is removed, never invented.
7. **Never use em-dashes or other classic AI-slop tell-tales** in landing page
   copy (the build strips them).
9. **Plan before build (2026-10-16):** the tab first shows the list of landing
   pages it will build and which ad groups go on each (`plan` in `step5.json`,
   made by a `{"plan": true}` job). Nothing is built until the user presses
   "Build these landing pages"; "Re-plan" regroups with a note. The build uses
   the saved plan (deleted ad groups dropped, new ones go on the general page).
10. **Editing ad groups (Step 3, 2026-10-16):** keywords can be dragged or moved
   by dropdown within a campaign, and an ad group can be deleted with all its
   keywords. Once ad copy exists, an "Update Ad Copy" button appears next to
   "Reset exclusions". It re-approves Step 3 as edited (no regeneration), then
   runs `sync_ad_copy`: deleted ad groups are removed from ad copy, extensions
   and the landing page list; new ad groups get fresh copy; ad groups whose
   keywords changed are rewritten; the rest is untouched. `step3.json` is
   updated to the approved rows (original saved as `step3_original.json`)
   because the upload reads it. Ad copy and extensions return to review.
8. **Chat for revisions (2026-10-16):** once pages are built, the tab has an "Ask
   for changes" chat (`POST /api/landing/revise`). Each message is saved in
   `step5.json` (`chat`, `revision_notes`) and queues a rebuild that applies
   every note so far, so earlier changes are never lost. The Rebuild button and
   the toolbar's "Ask for changes" also apply the saved notes.

## Step 6 - Writing Sitelinks, Callouts & Structured Snippets Copy For Google Ads — NOT YET IMPLEMENTED

Uses the landing page URLs stored in Step 5 (plus browsing the business's own
site) to write sitelink, callout, and structured snippet ad extension copy.
Not built yet - revisit once Step 5 has real URLs to work from.

### Sitelinks

1. Each ad group gets its own set of 6 sitelinks. In general the sitelink
   copy itself can stay the same across ad groups within a campaign - it's
   the **Final URL** that needs to differ, linking to that ad group's
   specific landing page (from Step 5).
2. Per sitelink:
   - **Sitelink text**: 35 characters max.
   - **2 descriptions**: 25 characters max each.
   - **Final URL**: that ad group's Step 5 landing page with an anchor
     appended (e.g. `#reviews`, `#gallery`, `#contact`).
3. Style examples to follow (use judgment for better CTR ideas too):
   - Fences That Last
   - 5-Star Rated
   - See Our Work
   - 100% Free Quotes
   - Free Measure & Quote
   - Fully Licensed
   - Fully Insured
4. **Stop and wait for the user to review and approve the sitelinks before
   moving on** (to callouts/structured snippets, or the next step).

### Callouts

6. Write 6 callouts, account-wide (shared across every campaign/ad group).
   25 characters max each. Focus on benefits - use judgment for ideas beyond
   the examples below if they'd lift CTR:
   - Affordable Pricing
   - Locally Owned & Operated
   - 10+ Years Experience
   - Many Happy Customers
   - 5-Star Rated
   - 332 Reviews
   - Free Measure & Quote

### Structured Snippets

7. Add one structured snippet with header **"Service Catalog"**, filled in
   with the business's actual stated services (scope discipline from the top
   of this doc still applies - only list services the user named). E.g. for a
   concrete company:
   - Concrete Driveways
   - Concrete Patios
   - Concrete Paths
   - (and so on, per the business's actual stated services)

## Step 7 - Lead Capture (Airtable Webhook + Automation) — IMPLEMENTED

Wires a client's live landing page(s) to the agency's "Pay Per Lead" Airtable
base so form submissions land as leads automatically. Done per-domain, once
the landing page(s) from Step 5 are live on Netlify.

1. Base: **"Pay Per Lead"** (`search_bases`/`list_tables_for_base` via the
   Airtable MCP tools - don't hardcode the base ID, look it up).
2. **Websites table** - check for an existing record matching the current
   domain (bare domain, no `https://`/`www.` - e.g. `canterburypainting.co.nz`,
   matching the convention of every existing row). Create one with just the
   `Name` field if missing; leave everything else blank.
3. **Client List table** - also create a record here (added 2026-10-07):
   - `Name` -> business name.
   - `Client Status` -> **Trial**.
   - `Contact name` -> leave empty.
   - `Contact email` -> business email (from Step 0).
   - `Phone number` -> business phone number (from Step 0).
   - `Website` -> linked to the Websites record created in item 2 above.
   - `Cost per lead` -> leave empty.
   - `Account owner` -> **Liam Emery**.
4. **Before creating a new automation, check if one already exists** for this
   client (`list_automations` filtered to `genericWebhookReceived`) - the
   agency sometimes pre-creates the automation + wires the Netlify env var
   ahead of the rest of the build. Reuse it rather than creating a duplicate
   (caught during the first run of this step, 2026-10-06 - Canterbury
   Painters already had an undeployed automation and a Netlify
   `AIRTABLE_WEBHOOK_URL` env var pointing at it).
5. New automation (if one doesn't already exist): trigger = **"When webhook
   received"** (`genericWebhookReceived`). `create_automation` requires at
   least one node to validate, so create it with a throwaway placeholder
   `createRecord` node, then `get_automation` to read the `webhookUrl`.
   Add/confirm that URL as the Netlify env var **`AIRTABLE_WEBHOOK_URL`** on
   that client's Netlify site (`netlify-project-services-updater`,
   `manage-env-vars`) - this is the variable the landing page's own code
   reads at build/runtime to know where to POST leads.
6. **Send a real test submission** from one of the live landing pages before
   building the Create Record field mapping - the webhook only infers its
   payload schema (`webhookSchema`/`webhookSchemaIsSet`) from an actual POST,
   and the exact field names vary per site (e.g. `phone` vs `Phone-number`,
   whether a `Message`/`Budget` field exists at all). Use the built-in
   browser to fill and submit the real form with obviously-fake data (e.g.
   name "TEST LEAD - please ignore") rather than guessing the payload shape.
   The automation is undeployed/off at this point, so the POST only captures
   the schema - it does not create a real record or send real email yet.
7. **Action 1 - Create Record**, in **All Leads**:
   - `Website` -> linked to the Step 2 website record (static, this
     automation is one-per-domain).
   - `Billable?` -> **Yes**, `Lead Type` -> **Form Submission** (standing
     rule for every client, confirmed 2026-10-06).
   - `Lead Source` -> left for Action 4's conditional (don't set it here).
   - Everything else maps straight off the captured webhook payload by name
     (Name, Email, Phone Number, Project Type, Timeline, Landing Page, etc.)
     - only map fields that actually exist in that site's payload. Ask the
     user rather than guess when a mapping is ambiguous (e.g. the payload
     carries its own `source` field that doesn't obviously map to the
     `Lead Source` select options - that one turned out to be superseded by
     Action 4 below).
8. **Action 2 - Gmail > Send Email** (new-lead notification), via the
   **"LFT Lead Notifications"** connected Gmail account
   (`list_external_accounts` to get its `externalAccountId` - don't
   hardcode it, it can change):
   - To: the business's own email from Step 0 (`step0.json`) if one was
     collected, since that's the whole point of gathering it - leads forward
     straight to the client. Falls back to `liam@leadsfortradies.co.nz` (the
     standing default while in testing) if Step 0 doesn't have one yet.
   - From name: **"New Lead"** (standing rule for every client, confirmed
     2026-10-06 - missed on the first pass of this step, don't drop it
     again).
   - Reply-To: the form's submitted email, so replying goes straight to the
     lead.
   - BCC: `liam@leadsfortradies.co.nz` (standing rule added 2026-10-07, every
     client, so every new-lead notification is also visible to this inbox).
   - Subject: `New Lead - <Business Name>` (plain business name, not the
     domain or legal suffix - e.g. "AMS Decorators", not
     "AMS Decorators Ltd" or "canterburypainting.co.nz").
   - Body: plain HTML, one `<br>`-separated line per field that exists in
     this site's payload (Name / Phone number / Email / Project Type /
     Timeline / Budget) - **omit any line whose field isn't present for this
     particular site** (e.g. most sites don't have a Budget field - don't
     invent one).
9. **Action 3 - Gmail > Send Email** (dispute window), same Gmail account:
   - To: `liam@leadsfortradies.co.nz`.
   - Subject: `LFT: Lead Dispute <Name>`.
   - Body: fixed dispute-instructions text + Name/Phone/Email, plus the
     **Lead ID** pulled from Action 1's `createRecord` output
     (`{"$ref":"<createRecordKey>","path":["id"]}`).
10. **Action 4 - Conditional (final node)** sets `Lead Source` on the same
   record (`updateRecord`, `rowId` = Action 1's output id again): if the
   submitted landing-page URL **contains `/quote/`** -> `Google Ads`,
   else -> `SEO`. This is why Action 1 leaves `Lead Source` unset - this
   conditional is the only thing that sets it.
11. `create_automation`/`update_automation` only ever save a **draft** - the
    automation stays off until the user turns it on themselves in the
    Airtable UI (a deliberate human-review gate). Always end this step by
    telling the user it's off and linking the `automationUrl` so they can
    review and enable it - never assume it's live.

## Step 8 - Upload The Campaign Into Google Ads — NOT YET IMPLEMENTED

Takes the approved Step 1-6 output and actually builds the live (paused)
campaign in the client's Google Ads account, including conversion tracking
via Google Tag Manager.

0. **If the landing pages use a final domain, the user must have confirmed in the
   app that it's connected** ("Is the final domain connected?"); ask them if it
   isn't confirmed. The upload script refuses until it is.
1. **Get the correct Google Ads account ID from the user first** - never
   guess or reuse another client's account.
2. **Always upload the campaign paused.** Never let it go live during this
   step. "Paused" applies to the **campaign entity only** - ad groups,
   keywords, and ads underneath it get uploaded as **ENABLED**. The paused
   campaign already stops everything from serving, so there's no need to
   also pause every child entity; this way the account is ready to go the
   moment the user unpauses the campaign, instead of needing every ad
   group/keyword/ad individually enabled first.
3. **Only ever upload BOF - Priority 1, unless the user explicitly says
   otherwise.** If ad copy/sitelinks/etc. have also been prepared for BOF -
   Priority 2 and/or Price Discovery (i.e. Step 4-6 were run for them too),
   it's fine to ask the user whether they want those uploaded as well this
   time - but default to Priority 1 only, don't assume the others should go
   up just because they exist.
4. **Upload everything that's been prepared for the campaign(s) in scope** -
   keywords, ad groups, campaigns, ad copy, sitelinks, callouts, structured
   snippets. Not a partial upload.
5. **Upload negative keywords - both lists, every build** (added
   2026-10-07):
   - This account's own negative list from Step 1 (step 9 there) - the
     irrelevant/wrong-intent keywords that surfaced for this specific
     business during KWR.
   - The standing cross-client list at `data/global_negative_keywords.csv` in
     this repo - generic junk (jobs/careers, training/DIY, retailers/
     marketplaces, wrong-intent, wrong-location) that applies to every
     account regardless of trade. Upload this file as-is for every client,
     not just when something relevant turns up in Step 1.
   - Both go into **one shared negative keyword list, attached to every
     campaign in the account** so it behaves as "account-wide" even though
     there's no true customer-level attachment for keyword-based negative
     lists (confirmed live 2026-10-07 on painting-canterbury -
     `CustomerNegativeCriterion.negative_keyword_list` exists in the API
     schema but returns `NEGATIVE_KEYWORD_SHARED_SET_DOES_NOT_EXIST` even
     against a confirmed-ENABLED shared set - matches the Ads UI, which also
     only lets you attach a negative list to specific campaigns, never the
     whole account directly). When a new campaign launches later (Priority
     2 / Price Discovery), re-run the attach step so it picks up the same
     shared list - it won't inherit it automatically.
   - **Before uploading, check the global CSV's terms against this
     account's own kept/approved keyword list for collisions** (a term
     meant to be generic can still block a real wanted keyword for a given
     trade - caught on painting-canterbury 2026-10-07: the global CSV had a
     bare "hire" entry aimed at equipment-hire searches, but "hire" is also
     a hiring-qualifier word per Step 1's Standing Classification Rules, so
     it collided with legitimate "hire a painter near me"-style BOF
     keywords - every client of this agency is itself a trade/service
     business, so a bare "hire" negative was unsafe account-wide and got
     removed from `data/global_negative_keywords.csv` rather than patched
     per-client. Keep checking for this class of collision on every build
     - `step8_upload_negatives.py --skip-terms` exists for a one-off case
     that's unsafe for one specific account but still fine to keep in the
     master file for everyone else; if a term is unsafe for every client
     (like "hire" was), fix the master CSV instead, same as this one was).
   - Only add a keyword to the project's own Step 1 negative list when
     there's a concrete, identifiable reason it's off-topic (DIY, wrong
     trade/service, product/brand browsing, wrong location, cheap/
     affordable, job-seeking). A keyword that still carries a real hiring
     signal (locality marker, business-entity word, trade noun) but simply
     didn't make the original BOF/Price Discovery list isn't automatically
     "irrelevant" - it may just be a close-variant duplicate that Google's
     own matching already covers via an approved keyword. Flag anything
     like that to the user instead of silently blocking it as a negative.
6. **Budget: $50/day.**
7. **Location targeting** is outlined in the setup phase (Step 0, service
   area/s). If you don't have it or you're unsure, stop and get the user to
   clarify rather than guessing. Set the location option to **Presence**
   (people in or regularly in your targeted locations) - not "Presence or
   interest".
8. **Disable Search Partners and Display Network** - search-only.
9. **Do not enable EU political ads** - standing rule, this agency doesn't
   run EU political advertising, every client, every build.
10. **Bidding: Manual CPC.** All keywords can be set to first page CPC bids.
11. **Conversion tracking setup (form submissions):**
   1. Create a new conversion action in Google Ads for form submissions,
      method = **Google Tag**.
   2. Use the **Tag Manager API** for the GTM side (updated 2026-10-07 - the
      API has no "create account" operation, so the user creates the GTM
      **account** and **container** themselves, both named after the
      client's domain, before this point - don't try to create them via the
      GTM MCP tools). Everything downstream of that (snippet install, tags,
      triggers, publish) is done through the Tag Manager API/MCP tools
      against the account+container the user already created.
   3. Install the GTM snippet on every page of the site.
   4. Create a new **Google Tag** in GTM using the Tag ID Google Ads
      generates for this conversion action.
   5. Publish the GTM container, then verify the tag install in Google Ads.
   6. Google Ads then issues a **conversion ID and conversion label** for
      form submissions - capture both.
   7. In GTM, create a **Form Submission trigger** (or a custom trigger that
      detects form submissions, if that's a better fit for the site's form).
   8. Create a **Google Ads Conversion Tracking tag** in GTM using that
      conversion ID/label, firing on the trigger above.
   9. Create a **Conversion Linker tag** in GTM.
   10. Publish, then run a live test to confirm the conversion tag actually
       fires on a real form submission.
   11. Confirm the conversion action shows as working/verified in Google
       Ads.
   12. **Tell the user it's complete and that you've verified it's working**
       - don't report this step done without that verification.
   13. **If the site has a CSP (`Content-Security-Policy`) header** (check
       `public/_headers`, `netlify.toml`, or a response header), the
       `connect-src` directive needs `https://www.googleadservices.com` and
       `https://googleads.g.doubleclick.net` or the conversion ping request
       is silently dropped by the browser (CSP violation, no console error
       visible to page JS) even though `gtm.js` itself loads fine and
       `script-src` already allows those hosts - the gap is specifically in
       `connect-src`. Symptom: GTM's Form Submission trigger never pushes
       `gtm.formSubmit` to `dataLayer` and the "Google Tag" entity's own
       `gtag/js` request never fires either, so it initially looks like a
       GTM config problem rather than a CSP one. Verify with
       `performance.getEntriesByType('resource')` in the browser looking for
       `googleadservices.com`/`doubleclick.net` request entries after a real
       test submission - don't trust an absence of console errors as proof
       nothing's blocked. Caught on the Canterbury Painters test run
       (2026-10-06) - the site's `public/_headers` CSP had a stock template
       `connect-src` that was missing these two hosts despite having them in
       `script-src`.
12. **Call extension:** use the business phone number from Step 0
    (`step0.json`) if one was collected, and add it as an account-wide call
    extension. Always a New Zealand number.

## Step 9 - Phone Number Creation In Delacon — NOT YET IMPLEMENTED

Added 2026-10-07. Orders a NZ call-tracking number for this client in
Delacon. Done in the Delacon web UI, no API/MCP integration yet.

1. Click the dropdown top-left beneath the logo and go to **"Services"**.
2. Top right: **"Order Number"**.
3. Country: **New Zealand**.
4. What the number is used for: **"Web"**.
5. Number type: select the correct **location**.
6. Quantity: leave as **1**.
7. Call recording and call feedback survey: leave **disabled**.
8. Rebilling: leave as **"assign later"**, then click next.
9. Business name: the **domain**.
10. Business category: **Google Ads**.
11. Tracking type: **all references**.
12. Business number and termination number: Liam's personal number for now
    (`0278246725`) - this is only temporary, until call tracking is wired up
    in Make.com (Step 10).
13. Notification email: `liam@leadsfortradies.co.nz` (same as the
    submission email).
14. **Numbers aren't provisioned immediately.** Tell the user this step is
    complete and wait for them to confirm the number has been provisioned
    before moving on - don't assume it's ready right away.

## Step 10 - Adding The Phone Number To The Website, Ad Account & Make.com — NOT YET IMPLEMENTED

Added 2026-10-07. Once Delacon has provisioned the number (Step 9), there
are manual steps the user does themselves, then one Airtable follow-up
Claude does once those are confirmed.

1. **Manual steps the user does** (not Claude):
   1. Get the phone number from their email.
   2. Install the dynamic number insertion code via Google Tag Manager.
   3. Set up the call tracking webhook in Make.com.
   4. Add the tracking number as a call extension in Google Ads.
   5. Link Delacon and Google Ads so conversion data uploads.
2. **Once the user confirms all of the above is done**, Claude's follow-up:
   1. In Airtable, go to the **Phone Call Dispute Emails** automation.
   2. Add another conditional action: if `Lead Type` = **Phone Call** and
      `Client name` matches the client just created, send the lead dispute
      email (copy the email body from Step 7's dispute-email action) - just
      update the **To** address to that client's email from the **Client
      List** table.

## Step 11 - Trello Task Creation & Manual Review — NOT YET IMPLEMENTED

Added 2026-10-07. Final step of the build - creates the human QA checklist.

1. Create a new Trello task on the **"Sales"** board, if one doesn't already
   exist for this business. Name it `<Business Name>`.
2. Add a checklist to the card with the following items:
   1. Confirm the budget.
   2. Confirm the keywords are good and appropriate max CPCs are set.
   3. Confirm the location is correct and it's set to Presence in.
   4. Confirm the bidding strategy.
   5. Confirm negative keywords have been added.
   6. Confirm sitelinks are added.
   7. Confirm structured snippets are added.
   8. Confirm callouts are added.
   9. Confirm call extensions are added.
   10. Confirm conversion tracking for forms has been added.
   11. Confirm conversion tracking for phone calls has been added.
   12. Confirm ad copy looks good.
   13. Confirm ads are going to the correct landing pages.
   14. Confirm form submissions are going to the business owner email.
   15. Confirm phone calls are going to the business owner phone.
   16. Confirm each of the landing pages has the right content.
   17. Confirm the dynamic number insertion is working on the landing page.

## Current build status

- Steps 9-11 (Delacon phone number, wiring it up across site/Ads/Make.com,
  Trello QA checklist) added to this doc 2026-10-07 - chat/manual process
  only, nothing scripted yet. Step 9 is done in the Delacon web UI, Step 10
  is mostly manual steps the user does themselves plus one Airtable
  conditional Claude adds afterward, Step 11 is a Trello checklist Claude
  creates via the Trello MCP/API once everything else above is done.
- `data/global_negative_keywords.csv` added 2026-10-07 - the standing
  cross-client negative keyword list (jobs/careers, training/DIY, retailers/
  marketplaces, wrong-intent, wrong-location terms), uploaded account-wide
  for every client per Step 8 item 5. Keyword column already carries Google
  Ads match-type syntax (quoted = phrase match), so upload as-is rather than
  reformatting.
- Step 0 (business info) added 2026-10-06 - chat-only, no web app UI.
  `scripts/lib/webapp_export.py`'s `write_step0_business_info()` persists
  whatever's been collected to `web/data/<project-id>/step0.json`; image
  assets (logo, work photos, team photos) get copied into
  `web/data/<project-id>/assets/`. Step 4 and Step 5 read this instead of
  asking the user cold.
- Google Cloud project has Basic access (post Sept 2026 developer-token
  sunset - access level lives on the Cloud project, not a developer token;
  see README.md).
- OAuth + credentials working end-to-end (`google-ads.yaml`).
- `scripts/keyword_research.py` - pulls real Keyword Planner data (seed
  keywords and/or URL, locations, min search volume filter).
- `scripts/resolve_location.py` - resolves plain place names to geo target
  IDs internally.
- Classification into BOF - Priority 1 / BOF - Priority 2 / Price Discovery /
  Manual Review / Excluded is a judgment call Claude makes by reading the raw
  results against the rules above - not automated in code.
- Review happens on a deployed web app (lftcampaignbuilder.netlify.app,
  password-protected) with per-keyword exclude buttons; approval is
  submitted via a Netlify Form and read back through the Netlify MCP tools -
  see "Review happens in the web app" above.
- `scripts/step2_location_keywords.py` - step 2's location-keyword pull,
  exact-phrase volume via historical metrics. Judgment call before running it:
  skip for single big metros (see "Big single metro vs. distinct towns"
  above), run it for regions of genuinely separate towns.
- `scripts/compile_step3_adgroups.py` - organizes an approved Step 1 list
  into STAGs. Theme assignment is a judgment call (like Step 1's
  classification) made by reading the keywords - the script just joins that
  judgment onto the real numbers and errors out if any approved keyword
  didn't get assigned anywhere.
- Web app (`web/`) is a multi-project app as of 2026-10-05: projects list +
  per-project step tabs, generic review-table UI shared across Step 1/3,
  approvals via Netlify Form. See "Review happens in the web app" above.
  `scripts/webapp_sync.py` pushes a step's CSV output into it.
- Step 4 (ad copy) is a judgment call Claude makes by reading the approved
  Step 3 ad groups plus real business facts (from the user or their live
  site) - not automated in code. Output saved as
  `output/<project-id>/step4_ad_copy.csv`. No web app review step built for
  it yet - reviewed directly in chat.
- Step 5 (landing pages) added 2026-10-06 -
  `web/js/landingpages.js` + `scripts/lib/webapp_export.py`'s
  `write_step5_landing_pages()`. Web app tab offers "I'll provide the URLs"
  (per-ad-group URL inputs, ad group list seeded from Step 4) vs. build from the site
  template vs. build with an existing site's design system (2026-10-15: now
  three options; see Step 5 above).
  Claude can also write URLs straight into
  `web/data/<project-id>/step5.json` when given them in chat, bypassing the
  web approval round-trip. Feeds Step 6 (sitelinks, not yet implemented).
- Step 7 (lead capture) added 2026-10-06 - not scripted, done directly
  through the Airtable and Netlify MCP tools per client/domain. No code in
  this repo; see "Step 7 - Lead Capture" above for the full per-domain
  procedure (Websites record, webhook automation, Netlify env var, test
  submission, Create Record + 2 Gmail actions + Lead Source conditional).
  First real run: canterburypainting.co.nz (Canterbury Painters - Form Subs
  automation in the "Pay Per Lead" base) - built on top of an automation +
  env var the user had already partially set up, which is why step 3 above
  (check for an existing automation first) exists.
- Step 8 (upload campaign to Google Ads + GTM conversion tracking) -
  IMPLEMENTED 2026-10-06, first real run on painting-canterbury. Campaign
  upload is scripted: `scripts/step8_upload_campaign.py <project-id>
  <customer_id> --geo-target-id <id> [--daily-budget 50] [--validate-only]`
  - reads the approved step1-6 JSON, builds one atomic GoogleAdsService
  mutate (campaign budget, campaign, location criterion, ad groups, exact-
  match keywords with first-page bid data pulled from step1/step2, RSAs,
  per-ad-group sitelinks, account-wide callouts, campaign-level structured
  snippet). **Negative keyword upload (Step 8 item 5) is scripted
  separately** - `scripts/step8_upload_negatives.py <project-id> <customer_id>
  [--skip-terms "term1,term2"] [--validate-only]` (added 2026-10-07, first
  real run on painting-canterbury) - reads
  `output/<project-id>/step1_negative_keywords.csv` plus
  `data/global_negative_keywords.csv`, creates one shared NEGATIVE_KEYWORDS
  set named `"<project-id> - Negative Keywords"`, adds every keyword to it as
  a `SharedCriterion`, then attaches that set to every campaign currently in
  the account via `CampaignSharedSet` (`CustomerNegativeCriterion` looks like
  the account-wide path in the API schema but doesn't actually work - see
  Step 8 item 5 above for the confirmed-live finding). Two **sequential**
  atomic mutates, not one - attaching the set in the same mutate that
  creates it is rejected
  (`NEGATIVE_KEYWORD_SHARED_SET_DOES_NOT_EXIST`) even under
  `--validate-only`, and there's also real backend lag afterward (a few
  minutes on painting-canterbury's first run, for ~1000 criteria) before the
  second mutate can see the set - the script retries the attach step with
  backoff, and `--attach-only <shared_set_resource_name>` lets you re-run
  just that step without recreating the list if the retries still aren't
  enough or the process got interrupted between the two mutates. Not folded
  into `step8_upload_campaign.py`'s mutate - run as a separate script after
  it. `--skip-terms` drops specific literal keyword text from both source
  files before upload - use it for a term that's only unsafe for one
  specific account (the global CSV's bare "hire" entry turned out to be
  unsafe for every account, since every client here is a trade/service
  business where "hire" is a hiring-qualifier word - that one got fixed in
  `data/global_negative_keywords.csv` itself instead, see Step 8 item 5
  above). Always run with `--validate-only` first. Only the campaign itself
  uploads as PAUSED - ad groups,
  keywords, and ads upload as ENABLED (updated 2026-10-07, see Step 8 item
  2 above). CPC bid micros must be rounded to the nearest cent
  (`micros()` helper) or the API rejects non-multiple-of-billable-unit
  values. Always run with `--validate-only` first. GTM setup (account
  creation, container, tags, triggers, publish) is NOT scripted - the GTM
  API has no "create account" operation (confirmed via the MCP tool's
  action enum: get/list/update only), so a GTM account must be created by
  the user in the tagmanager.google.com UI first; everything downstream
  (container, Google Tag, Form Submission trigger, Google Ads Conversion
  Tracking tag, Conversion Linker, publish) can be done through the GTM
  UI in the browser pane once that account exists. The GTM API's daily
  query quota is easy to exhaust mid-build (ran out during this first run)
  - if that happens, fall back to driving tagmanager.google.com directly in
  the browser pane rather than waiting on API quota reset. See item 13
  under "Conversion tracking setup" above for the CSP `connect-src` gotcha
  that silently breaks conversion firing even after everything else is
  configured correctly - verify with real network requests, not just
  "no console errors".
