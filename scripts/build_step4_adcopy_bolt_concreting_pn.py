"""
Step 4 ad copy for Bolt Concreting (2026-10-14) - Bottom of Funnel and Price
Discovery campaigns.

Per ad group: 3 headlines pinned to position 1 (closest match to the ad
group's keywords), 12 benefit headlines, 4 descriptions (each containing one
of the ad group's keywords), 2 display paths, final URL from step5.json.

Benefit facts come from palmerstonnorthconcreting.co.nz (12+ years, 200+
projects, 17+ Facebook 5-star reviews, free on-site quotes within 48 hours,
one firm written price, owner does the work / no subcontracted crews, built
for Manawatu weather, guaranteed workmanship). "Fully insured" is NOT used:
not stated anywhere. Every BOF ad group states new concrete only (audit:
Bolt disputes repair/resurfacing leads).

Price Discovery pinned headlines are offer-style price prompts, not keyword
echoes (feedback_step4_price_discovery_headlines).
"""
import csv, json, sys

PROJECT = "bolt-concreting-palmerston-north"
OUT_CSV = f"output/{PROJECT}/step4_ad_copy.csv"
STEP5 = f"web/data/{PROJECT}/step5.json"

BASE = [
    "12+ Years Experience", "200+ Projects Completed", "Free On-Site Quotes", "Quote Within 48 Hours",
    "One Firm Price In Writing", "No Surprise Extras", "Owner Does The Work", "No Subcontracted Crews",
    "Built For Palmy Weather", "Workmanship Guaranteed", "5-Star Rated On Facebook", "We Pour New Concrete",
]


def b(*swaps):
    out = list(BASE)
    for old, new in swaps:
        out[out.index(old)] = new
    return out


NEW_ONLY = "New concrete only, no repairs or resurfacing."
AD_GROUPS = {
 # ---------------- Bottom of Funnel ----------------
 "Driveway Replacement": dict(
   pinned=["Driveway Replacement", "Replace Concrete Driveway", "New Concrete Driveway"],
   benefits=b(("Built For Palmy Weather", "Old Driveway Carted Away"), ("No Subcontracted Crews", "Falls Set To Drain Away")),
   descriptions=[
     "Concrete driveway replacement in Palmerston North. Old surface broken out and carted away.",
     "Replace driveway with new concrete. Free on-site quote, firm written price in 48 hours.",
     "New driveway poured by the owner, not a subcontracted crew. 12+ years laying concrete.",
     "Replace driveway the right way: correct base, mesh and falls. Workmanship guaranteed."],
   paths=["Driveways", "Replacement"]),
 "Driveway Contractors": dict(
   pinned=["Concrete Driveway Contractors", "Driveway Contractors Near Me", "Concrete Driveway Installers"],
   benefits=b(("Built For Palmy Weather", "Falls Set To Drain Away"), ("No Subcontracted Crews", "Old Surface Carted Away")),
   descriptions=[
     "Concrete driveway contractors in Palmerston North. Free on-site quote, price in 48 hours.",
     "Driveway contractors near me: plain, coloured and exposed aggregate. One firm price.",
     "Concrete driveway installers with 200+ projects completed. The owner does the work.",
     "New concrete driveway installation done properly. 5-star rated on Facebook."],
   paths=["Driveways", "Palmerston-Nth"]),
 "Concrete Patios": dict(
   pinned=["Concrete Patio Contractors", "Concrete Patio Near Me", "Concrete Patio Installers"],
   benefits=b(("Built For Palmy Weather", "Levels And Falls Set Right"), ("No Subcontracted Crews", "Joins Your Existing Concrete")),
   descriptions=[
     "Concrete patio contractors in Palmerston North. Free on-site quote, price in 48 hours.",
     "Concrete patio installers near me. Broom, coloured or exposed aggregate finishes.",
     "New concrete patio installation joined cleanly to your house. One firm price in writing.",
     "Concrete patio installation by the owner, not a subcontracted crew. 200+ projects."],
   paths=["Patios", "Palmerston-Nth"]),
 "Concrete Paths": dict(
   pinned=["Concrete Path Installation", "Concrete Path Palmerston North", "Concrete Pathway Installation"],
   benefits=b(("Built For Palmy Weather", "Safe Grip Broom Finish"), ("No Subcontracted Crews", "Old Path Carted Away")),
   descriptions=[
     "Concrete path installation in Palmerston North. Free on-site quote, price in 48 hours.",
     "Concrete pathway installation that drains properly through wet Manawatū winters.",
     "Concrete path installation by the owner. One firm price in writing, no surprise extras.",
     "Concrete paths Palmerston North: neat edges, correct falls. Workmanship guaranteed."],
   paths=["Concrete-Paths", "Palmerston-Nth"]),
 "Concrete Slabs & Pads": dict(
   pinned=["Concrete Slab Contractors", "Concrete Slab Installation", "Concrete Pad Contractors"],
   benefits=b(("Built For Palmy Weather", "Correct Mesh And Thickness"), ("No Subcontracted Crews", "Sub-Base Done Properly")),
   descriptions=[
     "Concrete slab contractors in Palmerston North. Free on-site quote, price in 48 hours.",
     "Concrete slab installation for sheds, garages and sleepouts. One firm price in writing.",
     "Concrete pad contractors near me. Boxed, meshed and poured by the owner.",
     "Concrete slab installation on a proper base. 200+ projects completed, 12+ years."],
   paths=["Concrete-Slabs", "Palmerston-Nth"]),
 "Concrete Floors": dict(
   pinned=["Concrete Floor Contractors", "Concrete Floor Installation", "Floor Contractors Near Me"],
   benefits=b(("Built For Palmy Weather", "Level, Even Slab Finish"), ("No Subcontracted Crews", "Sub-Base Done Properly")),
   descriptions=[
     "Concrete floor contractors in Palmerston North. Free on-site quote, price in 48 hours.",
     "Concrete floor installation for garages, sheds and workshops. One firm written price.",
     "Concrete floor contractors near me: new floors poured and finished by the owner.",
     "Concrete floor installation on a proper base. 12+ years experience, guaranteed."],
   paths=["Concrete-Floors", "Palmerston-Nth"]),
 "Concrete Layers & Placers": dict(
   pinned=["Concrete Layers Near Me", "Concrete Placers", "Concrete Finishers Near Me"],
   benefits=b(("Built For Palmy Weather", "Boxed, Meshed And Poured"), ("No Subcontracted Crews", "Crisp Edges, Clean Site")),
   descriptions=[
     "Concrete layers near me in Palmerston North. Free on-site quote, price in 48 hours.",
     "Concrete placers and finishers for driveways, paths, patios and slabs. " + "One firm price.",
     "Concrete finishers near me. The person who quotes your job pours and finishes it.",
     "Local concrete layers with 200+ projects completed. Workmanship guaranteed."],
   paths=["Concrete-Layers", "Palmerston-Nth"]),
 "Concreters Palmerston North": dict(
   pinned=["Concrete Palmerston North", "Concrete Contractors Palmy", "Concrete Feilding"],
   benefits=b(("Built For Palmy Weather", "Palmerston North Concrete Pros"), ("No Subcontracted Crews", "Feilding And Manawatū Too")),
   descriptions=[
     "Concrete Palmerston North: driveways, paths, patios and slabs. Free on-site quote.",
     "Concrete contractors Palmerston North, 12+ years experience. Price within 48 hours.",
     "Concrete Feilding and Manawatū. The owner quotes it and does the work. One firm price.",
     "Concrete services Palmerston North: 200+ projects completed, 5-star rated on Facebook."],
   paths=["Concrete", "Palmerston-Nth"]),
 "Concrete Contractors": dict(
   pinned=["Concrete Contractors Near Me", "Concrete Company Near Me", "Concreters Near Me"],
   benefits=b(("Built For Palmy Weather", "Driveways, Paths & Patios"), ("No Subcontracted Crews", "Boutique Local Team")),
   descriptions=[
     "Concrete contractors near me in Palmerston North. Free on-site quote, price in 48 hours.",
     "Concrete company near me: driveways, paths, patios and slabs. One firm written price.",
     "Concreters near me who turn up and do the job properly. 5-star rated on Facebook.",
     "Concrete contractors with 12+ years experience. New concrete only, no repairs."],
   paths=["Concrete", "Contractors"]),
 "Exposed Aggregate": dict(
   pinned=["Exposed Aggregate Driveways", "Aggregate Concrete Driveway", "Exposed Aggregate Patio"],
   benefits=b(("Built For Palmy Weather", "Exposed Aggregate Finish"), ("No Subcontracted Crews", "Sharp, Low-Maintenance Look")),
   descriptions=[
     "Exposed aggregate driveways in Palmerston North. Free on-site quote, price in 48 hours.",
     "Exposed aggregate patio and path finishes that hide marks. One firm written price.",
     "Aggregate concrete driveway poured and finished by the owner. 200+ projects completed.",
     "Exposed aggregate driveway installers with 12+ years experience. Workmanship guaranteed."],
   paths=["Aggregate", "Driveways"]),
 "Coloured Concrete": dict(
   pinned=["Coloured Concrete Driveways", "Coloured Concrete Patio", "Coloured Driveways"],
   benefits=b(("Built For Palmy Weather", "Coloured Concrete Options"), ("No Subcontracted Crews", "Samples Shown At Quote")),
   descriptions=[
     "Coloured concrete driveways in Palmerston North. Free on-site quote, price in 48 hours.",
     "Coloured concrete patio and path options. We show you examples at the on-site quote.",
     "Coloured driveways poured and finished by the owner. One firm price in writing.",
     "Coloured concrete driveway installers. 200+ projects completed, 5-star rated."],
   paths=["Coloured", "Concrete"]),
 "Foundations": dict(
   pinned=["Concrete Foundations", "Concrete Foundations Near Me", "Concrete Slab Foundation"],
   benefits=b(("Built For Palmy Weather", "Sub-Base Done Properly"), ("No Subcontracted Crews", "Correct Mesh And Thickness")),
   descriptions=[
     "Concrete foundations in Palmerston North. Free on-site quote, firm price in 48 hours.",
     "Concrete foundations near me: formed, meshed and poured by the owner. 12+ years.",
     "Concrete slab foundation work with a firm written price. No surprise extras.",
     "Concrete foundation contractors with 200+ projects completed. " + "Guaranteed."],
   paths=["Foundations", "Palmerston-Nth"]),
 "Carports & Garage Slabs": dict(
   pinned=["Concrete Carport Slab", "Concrete Carport", "Concrete Slab For Garage"],
   benefits=b(("Built For Palmy Weather", "Garage And Carport Slabs"), ("No Subcontracted Crews", "Sub-Base Done Properly")),
   descriptions=[
     "Concrete carport slab in Palmerston North. Free on-site quote, price in 48 hours.",
     "Concrete slab for garage: boxed, meshed and poured properly. One firm written price.",
     "Concrete carport slabs poured by the owner, not a subcontracted crew. 12+ years.",
     "Concrete carport and garage slab work. 200+ projects completed, workmanship guaranteed."],
   paths=["Carport-Slabs", "Palmerston-Nth"]),
 "Concrete Steps": dict(
   pinned=["Concrete Garden Steps", "Concrete Outdoor Steps", "Concrete Path Steps"],
   benefits=b(("Built For Palmy Weather", "Even Rises, Crisp Edges"), ("No Subcontracted Crews", "Formed And Finished By Hand")),
   descriptions=[
     "Concrete garden steps in Palmerston North. Free on-site quote, price in 48 hours.",
     "Concrete outdoor steps with even rises and a safe, grippy finish. One firm written price.",
     "Concrete path steps formed and finished by hand by the owner. 200+ projects completed.",
     "Concrete garden steps built to join your existing path or patio. Workmanship guaranteed."],
   paths=["Concrete-Steps", "Palmerston-Nth"]),
 # ---------------- Price Discovery ----------------
 "Driveway Costs": dict(
   pinned=["Get A Price For Your Driveway", "Need A Price For A Driveway?", "Get Your Driveway Priced"],
   benefits=b(("Built For Palmy Weather", "Priced By Size And Finish")),
   descriptions=[
     "Concrete driveway cost depends on size, base and finish. We price yours on site, free.",
     "How much does a concrete driveway cost? Get a firm written price within 48 hours.",
     "Concrete driveway cost per m2 varies with access and finish. One firm price, no extras.",
     "Cost of a concrete driveway in Palmerston North, in writing. 200+ projects completed."],
   paths=["Driveway", "Cost"]),
 "Driveway Replacement Costs": dict(
   pinned=["Price To Replace A Driveway", "Need Your Driveway Replaced?", "Replacement Driveway Price"],
   benefits=b(("Built For Palmy Weather", "Old Driveway Carted Away")),
   descriptions=[
     "Cost to replace driveway concrete includes breaking out and cartage. Priced on site.",
     "Concrete driveway replacement cost in writing, free and with no obligation.",
     "Cost to replace a driveway depends on size and access. Firm price within 48 hours.",
     "Driveway replacement cost for Palmerston North homes. One firm price, no surprise extras."],
   paths=["Driveway", "Replace-Cost"]),
 "Exposed Aggregate Costs": dict(
   pinned=["Get An Exposed Aggregate Price", "Aggregate Driveway Price?", "Get Your Aggregate Priced"],
   benefits=b(("Built For Palmy Weather", "Exposed Aggregate Finish")),
   descriptions=[
     "Exposed aggregate driveway cost depends on size and finish. We price yours on site.",
     "Cost of exposed aggregate concrete in writing within 48 hours. Free, no obligation.",
     "Exposed aggregate driveway price in Palmerston North. One firm price, no extras.",
     "Aggregate driveway cost from a builder with 200+ projects completed. Free quote."],
   paths=["Aggregate", "Cost"]),
 "Path Costs": dict(
   pinned=["Get A Price For Your Path", "Need A Price For A Path?", "Get Your Concrete Path Priced"],
   benefits=b(("Built For Palmy Weather", "Priced By Length And Width")),
   descriptions=[
     "Concrete path cost depends on length, width and access. We price yours on site, free.",
     "Concrete path cost in Palmerston North, in writing within 48 hours.",
     "Concrete pathway cost with one firm price and no surprise extras. Free on-site quote.",
     "Cost of concrete path from a 5-star rated Palmy concreter. Get a firm written price."],
   paths=["Concrete-Path", "Cost"]),
 "Patio Costs": dict(
   pinned=["Get A Price For Your Patio", "Need A Price For A Patio?", "Get Your Concrete Patio Priced"],
   benefits=b(("Built For Palmy Weather", "Priced By Size And Finish")),
   descriptions=[
     "Concrete patio cost depends on size, access and finish. We price yours on site, free.",
     "Cost of a concrete patio in Palmerston North, in writing within 48 hours.",
     "Concrete patio cost with one firm price and no surprise extras. Free on-site quote.",
     "Cost to concrete a patio from a builder with 200+ projects completed. No obligation."],
   paths=["Concrete-Patio", "Cost"]),
 "Slab & Pad Costs": dict(
   pinned=["Get A Price For Your Slab", "Need A Price For A Slab?", "Get Your Concrete Pad Priced"],
   benefits=b(("Built For Palmy Weather", "Priced By Size And Thickness")),
   descriptions=[
     "Concrete slab cost depends on size, thickness and access. We price yours on site, free.",
     "Concrete pad cost for sheds, garages and sleepouts, in writing within 48 hours.",
     "Cost of a concrete slab in Palmerston North with one firm price and no extras.",
     "How much for a concrete slab? Free on-site quote from a 5-star rated Palmy concreter."],
   paths=["Concrete-Slab", "Cost"]),
 "Concrete Floor Costs": dict(
   pinned=["Get A Price For Your Floor", "Need A Concrete Floor Price?", "Get Your Floor Priced"],
   benefits=b(("Built For Palmy Weather", "Priced By Size And Thickness")),
   descriptions=[
     "Concrete floor cost depends on size, thickness and access. We price yours on site, free.",
     "Concrete garage floor cost in writing within 48 hours. Free, no obligation.",
     "Concrete floor slab cost with one firm price and no surprise extras. Palmerston North.",
     "Concrete floor cost from a builder with 12+ years experience. Free on-site quote."],
   paths=["Concrete-Floor", "Cost"]),
 "Concrete Costs": dict(
   pinned=["Get A Price For Your Concrete", "Need A Concrete Price?", "Get Your Concrete Job Priced"],
   benefits=b(("Built For Palmy Weather", "Priced By Size And Finish")),
   descriptions=[
     "Concrete cost per m2 depends on the job, base and finish. We price yours on site, free.",
     "Concrete laying cost for driveways, paths, patios and slabs. Firm price in 48 hours.",
     "Cost to pour concrete in Palmerston North, in writing. One firm price, no extras.",
     "Concrete quote from the owner, not a subcontracted crew. 200+ projects completed."],
   paths=["Concrete", "Cost"]),
}
BANNED = ["—", "–", "!"]
KW_FILE = f"output/{PROJECT}/step3_adgroups.csv"


def main():
    urls = {g["name"]: g["url"] for g in json.load(open(STEP5))["ad_groups"]}
    kws = {}
    for r in csv.DictReader(open(KW_FILE)):
        kws.setdefault(r["ad_group"], []).append(r["keyword"])
    approved = {k["keyword"] for k in json.load(open(f"output/{PROJECT}/step3_approved.json"))["kept_keywords"]}
    approved_groups = {k["group"].split(" — ", 1)[1] for k in json.load(open(f"output/{PROJECT}/step3_approved.json"))["kept_keywords"]}
    errors = []
    if set(AD_GROUPS) != approved_groups:
        errors.append(f"ad group mismatch vs approved step3: {set(AD_GROUPS) ^ approved_groups}")
    rows = []
    for name, ag in AD_GROUPS.items():
        if name not in urls or not urls[name]:
            errors.append(f"{name}: no final URL in step5.json")
        hl = ag["pinned"] + ag["benefits"]
        if len(ag["pinned"]) != 3 or len(ag["benefits"]) != 12 or len({h.lower() for h in hl}) != 15:
            errors.append(f"{name}: need 3 pinned + 12 unique benefit headlines")
        if len(ag["descriptions"]) != 4 or len(ag["paths"]) != 2:
            errors.append(f"{name}: need 4 descriptions, 2 paths")
        for text, lim, kind in [(h, 30, "headline") for h in hl] + [(d, 90, "description") for d in ag["descriptions"]] + [(p, 15, "path") for p in ag["paths"]]:
            if len(text) > lim:
                errors.append(f"{name}: {kind} too long ({len(text)}>{lim}): {text}")
            if any(x in text for x in BANNED):
                errors.append(f"{name}: banned char in {kind}: {text}")
        for p in ag["paths"]:
            if " " in p:
                errors.append(f"{name}: space in path {p}")
        # every description should echo one of the ad group's keywords (close match)
        group_kws = [k for k in kws.get(name, [])]
        for d in ag["descriptions"]:
            dl = d.lower()
            if not any(k in dl for k in group_kws):
                errors.append(f"{name}: description has no ad group keyword: {d}")
        rows += [(name, "Headline", f"H{i+1} (pinned to position 1)", t) for i, t in enumerate(ag["pinned"])]
        rows += [(name, "Headline", f"Benefit {i+1} (unpinned)", t) for i, t in enumerate(ag["benefits"])]
        rows += [(name, "Description", f"D{i+1}", t) for i, t in enumerate(ag["descriptions"])]
        rows += [(name, "Display Path", f"Path {i+1}", t) for i, t in enumerate(ag["paths"])]
        rows.append((name, "Final URL", "Final URL", urls.get(name, "")))
    if errors:
        sys.exit("\n".join(errors))
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ad_group", "field_type", "slot", "text", "char_count"])
        for r in rows:
            w.writerow([*r, len(r[3])])
    print(f"Wrote {len(rows)} rows for {len(AD_GROUPS)} ad groups to {OUT_CSV}")


if __name__ == "__main__":
    main()
