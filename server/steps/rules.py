"""Standing rules from PROCESS.md and the user's saved corrections, condensed
for Claude's system prompts. When PROCESS.md changes, update this file too."""

SCOPE_RULES = """\
SCOPE DISCIPLINE (most important):
- Only include services the business explicitly states. Never add an "obviously
  adjacent" trade (gates for a fence builder, retaining walls for a deck builder,
  staining/repair for a builder, alarms for a CCTV installer) unless it is in the
  stated services list.
- A keyword mixing a stated service with an unstated one ("fence and gate company")
  is excluded too.
- "near me" / "company" / "services" never override scope: "kitchen cabinet
  painters near me" is excluded for a house painter.
- Respect the business's scope notes (e.g. "residential only", "no roof painting").
"""

STEP1_RULES = SCOPE_RULES + """
CATEGORIES:
- B  (Bottom of Funnel): ready-to-hire searches. REQUIRES an explicit hiring/business
  signal in the keyword itself: the trade noun (painter, builder, installer...),
  a business-entity word (company/companies/contractor(s)/services), a locality
  marker (near me / in my area / nearby / local / a town name), an explicit
  have-it-done phrasing ("paint my house"), or a hiring qualifier (hire,
  professional, reputable, 0800). A bare "activity + material" phrase with none of
  these ("interior house painting", "roof respray", "painting brick homes") is
  top-of-funnel -> X.
- PD (Price Discovery): cost/price/quote questions about the SERVICE ("how much does
  it cost to build a deck", "house painting cost per m2"). Any cost/price
  "calculator" or "estimator" is always PD.
- MR (Manual Review): worth including but needs a human decision. Always give a
  short note why (e.g. "includes patio, which isn't a stated service").
- X  (Excluded): irrelevant, wrong intent or out of scope. Give a short reason.

ALWAYS EXCLUDE (X), every trade:
- "cheap", "cheapest", "affordable", "budget", "low cost", "free" - even with
  a hiring signal ("cheap house painters near me" is X).
- DIY / how-to / tutorials, jobs/careers/apprenticeships/salary, recruitment
  ("painters wanted", "subcontractors").
- "design" / "designer" terms; security gate / security fencing (unless stated);
  farm / rural / agricultural / livestock fencing.
- Product pricing rather than service pricing ("roof paint price", "5l paint
  price", "decking timber price") - the tin/material, not the job.
- Retailers / product brands that aren't mainstream NZ (overseas brands, niche
  installers like "Millboard installers"). Keep mainstream NZ: Modwood, Kwila,
  Colorbond, Resene, Dulux.
- Other cities / locations outside the service area; overseas business names.
- Brand-specific accreditation claims ("Dulux accredited painters") unless the
  business holds it.
- Narrow single-component framing that isn't how customers search for the whole
  service ("gutter painters", "trim painter").

TIER (only for B):
- A: locality marker AND business-entity word ("painting companies near me").
- B: trade noun + (locality marker OR business-entity word) ("roof painters near
  me", "painting company").
- C: bare trade noun or hiring qualifier only ("house painter", "professional painter").
When unsure whether something is genuine hiring intent, include it rather than
exclude it - dropping a real buyer keyword is the worse mistake.

NEGATIVE KEYWORDS (only for X, and only when the keyword is irrelevant/wrong
intent): suggest a negative. Use phrase match with the single problem word or
short phrase when it generalises ("staining", "design", "cheap", "diy"); exact
match with the full keyword for a one-off.
"""

AD_COPY_RULES = """\
GOOGLE ADS RESPONSIVE SEARCH AD RULES:
- Exactly 15 headlines (max 30 characters each), 4 descriptions (max 90 characters
  each), 2 display URL paths (max 15 characters each, lowercase, no spaces, use - ).
- 3 headlines are "pinned": as close to exact match as possible to this ad group's
  real highest-volume keywords (e.g. trade term + "Near Me", + the city name, + the
  region name). Title Case.
- 12 headlines are benefits. They must come ONLY from the real business facts
  given. Never invent a credential, stat, rating, award, year count, review count
  or guarantee that isn't in the facts. The only invented headlines allowed are
  generic unverifiable ones like "Free No-Obligation Quote", "Satisfaction
  Guaranteed", "Quality Workmanship", "Great Communication". 1-2 may be a specific
  real detail for this ad group's service.
- Every description must contain at least one of the ad group's actual keywords,
  verbatim or very close.
- NEVER use em dashes or en dashes, and avoid AI-slop phrasing ("elevate",
  "unlock", "seamless", "look no further", "transform your space").
- Do not use the words cheap, affordable or budget.
"""
