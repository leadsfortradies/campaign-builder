"""
Step 3: organise the approved Step 1 (+ Step 2, if run) keyword list into
Single Themed Ad Groups (STAGs). Classification is a judgment call made by
reading the keywords against the themes below - this script just joins that
judgment back onto the real volume/competition/bid numbers and checks every
approved keyword got assigned somewhere (PROCESS.md Step 3 rule #2).

Usage:
    venv/bin/python scripts/compile_step3_adgroups.py output/test_deck_fence_auckland/step1_approved.json
"""

import json
import sys

OUT_CSV = "output/test_deck_fence_auckland/step3_adgroups.csv"

AD_GROUPS = {
    "Deck Builder - General": [
        "deck builder", "deck builder near me", "deck contractors near me",
        "deck building companies near me", "deck installation", "deck building company",
        "deck companies near me", "deck installation near me", "deck construction near me",
        "deck contractors", "affordable deck builders near me", "best deck builders near me",
        "local deck builders", "deck builders in my area", "custom deck builders near me",
        "deck contractors in my area", "deck building contractors near me",
        "outdoor deck builders near me", "custom decks near me", "deck construction companies near me",
        "decking specialists near me", "deck installation companies", "local deck builders near me",
        "deck installation companies near me", "decking builders", "deck experts near me",
        "best deck companies near me", "build a deck near me", "outdoor deck installers near me",
        "contractors for decks near me", "deck makers near me", "deck installers in my area",
        "small deck builders near me", "decking companies in my area", "build me a deck",
        "best deck builders", "home deck builders", "deck construction company",
        "local deck contractors near me", "affordable deck builders", "deck builders around me",
        "deck places near me", "deck building contractor", "professional deck builders near me",
        "deck construction contractors", "custom deck builder", "deck installation service",
        "local deck builder near me", "new deck builder", "deck installation contractor",
        "outdoor deck installation",
        "how much does it cost to build a deck", "deck cost calculator", "deck cost estimator",
        "labor cost to build a deck calculator", "deck price calculator", "how much is it to build a deck",
        "cost to build a deck calculator", "how much does it cost to have a deck built",
        "how much it cost to build a deck", "deck building estimator",
        "how much does it cost to get a deck built", "how much does it cost to build a small deck",
        "cost of a new deck calculator", "how much does it cost to install a deck",
        "how much does it cost to build a new deck", "deck price estimator", "deck estimate near me",
        "how much will it cost to build a deck", "how much does it cost to make a deck",
        "deck installation cost calculator", "decking estimate cost calculator",
        "floating deck cost calculator", "estimated cost to build a deck",
        "how much does it cost for a new deck", "deck building price calculator",
        "deck construction cost estimator", "how much does it cost for decking",
        "how much do it cost to build a deck", "how expensive is it to build a deck",
        "how much it cost to build deck", "cost estimate deck construction",
        "decking costs per square foot", "how much should it cost to build a deck",
        "deck price per m2", "how much does it cost to do a deck",
        "how much does it cost to have a deck installed", "how does it cost to build a deck",
        "how much does it cost to build a 6x6 deck", "new deck cost calculator",
        "how much does it cost to build an outdoor deck", "how much does it cost to build a front deck",
        "how much does it cost to get decking done", "how much does it cost for decking to be installed",
        "how much would it cost to build a small deck", "how much does it cost to put a deck in",
        "how much does it cost to have deck built", "how much does it cost to do decking",
        "deck construction cost calculator", "concrete deck cost calculator",
    ],
    "Timber Decks": [
        "timber deck builder", "wood deck builders near me", "wood deck contractors near me",
        "wood deck installers near me", "timber decking contractors", "timber decking installers near me",
        "timber decking installation", "kwila decking installation", "wood deck installation",
        "wood deck price calculator", "deck wood cost calculator", "timber decking cost calculator",
    ],
    "Composite Decks": [
        "composite decking installation", "composite deck builder", "composite decking installers near me",
        "composite decking installation near me", "composite decking companies near me",
        "composite deck companies", "composite decking company near me", "composite decking installer near me",
        "composite deck experts", "composite deck cost calculator", "composite decking per m2",
        "composite decking price calculator", "composite deck estimate", "estimate composite deck cost",
        "how much does it cost for composite decking", "how much does it cost for a composite deck",
        "how much does it cost to install composite decking", "price per square foot composite decking",
    ],
    "Pool Decks": [
        "pool deck installers near me", "pool deck contractors", "pool deck builders", "pool deck companies",
    ],
    "Deck Replacement & Renovation": [
        "deck replacement contractors", "deck replacement contractors near me", "handyman deck builders",
        "deck remodeling contractors near me", "deck remodeling contractors",
        "how much does it cost to replace a deck", "how much does it cost to replace an existing deck",
        "how much does it cost to rebuild a deck", "how much does it cost to redo a deck",
        "how much does it cost to renovate a deck", "how much does it cost to extend a deck",
        "deck builders and repair near me", "deck repair cost calculator", "deck replacement cost calculator",
        "deck replacement cost estimator",
    ],
    "Deck + Outdoor Living (Patio/Pergola)": [
        "deck and patio contractors near me", "deck and patio builders near me",
        "patio and deck builders near me", "patio and deck contractors near me",
        "deck and pergola builders near me", "deck and patio contractors", "patio deck contractors near me",
        "patio decking installers near me", "deck and porch contractors near me", "deck patio builders",
    ],
    "Deck Features & Add-ons": [
        "how much does it cost to build a covered deck", "deck and stair builders near me",
        "outdoor stairs installation", "covered deck cost calculator", "deck railing cost calculator",
        "deck railing estimator", "deck stairs cost calculator",
    ],
    "Fence Builder - General": [
        "fencing contractors near me", "fencing co near me", "fencing business near me",
        "fencing contractors", "fence company near me", "fence co near me", "fence companies close to me",
        "fence builder", "fence builders", "fence co", "fence fence companies", "fence builder near me",
        "fencing company", "fence installation near me", "fence contractors near me", "fencing services",
        "fencing co", "best fence company near me", "local fence companies", "local fencing companies",
        "residential fence company near me", "best fencing companies near me", "local fence installers",
        "fence installation companies near me", "premier fence company", "fence companies in my area",
        "affordable fence company", "cheap fence company near me", "top rated fence companies near me",
        "highest rated fence companies near me", "good fencing companies near me", "best fencing company",
        "quality fencing company", "local fencing company near me", "reliable fence company near me",
        "residential fencing companies near me", "backyard fencing companies near me",
        "home fencing companies near me", "custom fences near me", "local fence builders",
        "local fence builders near me", "fencing builders near me", "fencing builders",
        "how much does it cost to build a fence", "fencing cost calculator", "fence installation cost",
        "fence cost estimator", "fencing cost", "how much does it cost to put up a fence",
        "how much does it cost to install a fence", "how much does it cost to fence a yard",
        "average fence cost", "cost to install fence per foot", "how much does it cost to get a fence installed",
        "how much does it cost to have a fence installed", "how much is it to build a fence",
        "how much is it to put up a fence", "how much is it to install a fence",
        "how much does it cost for a fence", "how much does it cost to put in a fence", "build a fence cost",
        "cost to put up a fence", "cost to put in a fence", "how much would it cost to build a fence",
        "how much does it cost to get a fence built", "cost of fences and installation",
        "fence installation price", "fence installation quote", "fencing quote calculator",
        "fencing price calculator", "fencing price estimator", "online fence quote calculator",
        "free fence estimate", "online fence estimator", "estimate for fence installation",
        "how much does it cost to have a fence built", "cost to have fence installed",
        "average cost of fencing per foot", "average cost of fencing per metre",
        "average price for fence installation", "typical fence cost", "typical price for fence installation",
        "average cost to build fence", "average cost to install privacy fence", "average price of fence",
        "average cost of new fence", "fence replacement cost calculator", "average cost to replace a fence",
        "fence cost calculator", "fence price calculator", "fence price estimator",
    ],
    "Timber & Wood Fences": [
        "wood fence company near me", "wood fence builders near me", "wood fence builders",
        "wood fence builder", "timber fence company", "timber fencing contractors near me",
        "timber fencing contractors", "timber fence contractors near me", "timber fence contractors",
        "wood fence cost calculator", "wood fence installation cost", "wood fence cost", "wood fence prices",
        "timber fence cost calculator", "timber fencing calculator", "how much does it cost to build a wooden fence",
        "how much does it cost for a wooden fence", "average cost of wood fence", "average cost to install wood fence",
    ],
    "Colorbond Fences": [
        "colorbond fence contractors", "colorbond fencing installation near me",
        "cost of colorbond fence per metre", "cost of colorbond fencing per metre",
        "colorbond fencing prices per metre", "colorbond fence price calculator", "colorbond fencing cost",
        "colorbond fence installation cost", "colorbond fence cost calculator", "colorbond fencing calculator",
    ],
    "Pool Fencing": [
        "pool fence company", "pool fencing company", "pool fence builder", "pool fencing contractors",
        "pool fence contractors", "pool fencing contractors near me", "pool fence contractors near me",
        "pool fencing installers near me", "pool fence installation", "pool safety fence installation",
        "swimming pool fence installation", "glass pool fence installation", "glass fence installation",
        "glass pool fencing installation", "best pool safety fence", "pool fencing cost",
        "pool fencing cost per metre installed", "pool safety fence cost", "pool fence installation cost",
    ],
    "Aluminium Fencing": [
        "aluminium fence installation", "aluminum fence installation", "aluminium fence builders",
        "aluminum fence cost calculator", "average cost of aluminum fence",
    ],
    "Picket Fencing": [
        "picket fence company", "picket fence builder", "picket fence cost",
    ],
    "Paling Fencing": [
        "timber paling fence calculator", "paling fence calculator", "pailing fence calculator",
    ],
    "Garden & Boundary Fencing": [
        "garden fencing companies near me", "garden fence company near me",
        "garden fencing contractors near me", "garden fence contractors near me",
        "boundary fencing contractors", "boundary fence contractors",
    ],
    "Deck & Fence Combo": [
        "deck and fence company", "deck and fence company near me", "fence and deck company near me",
        "deck and fence builders near me", "fence and deck builders near me", "deck and fencing companies near me",
        "deck and fence builders", "fencing and deck companies near me", "deck & fence company",
        "fence and deck companies", "decking and fencing companies near me", "deck and fence installers near me",
        "deck and fencing company near me", "fence and deck builders", "patio deck fence builders",
    ],
}

# Campaigns are the top-level container in Google Ads, above ad groups - a
# single ad group can't belong to more than one. Every STAG theme above
# therefore splits into up to three versions based on each keyword's actual
# category: BOF - Priority 1, BOF - Priority 2, Price Discovery.
#
# Keywords originally categorized "BOF - Priority 1" / "BOF - Priority 2" /
# "Price Discovery" in Step 1 map straight across. "Manual Review" keywords
# were never given any of those labels - they need individual judgment here.
# Default is BOF - Priority 2 (most kept Manual Review items are
# service/hiring intent, but weren't confirmed as core Priority 1 keywords);
# only the explicit cost-questions below go to Price Discovery.
MANUAL_REVIEW_TO_PRICE_DISCOVERY = {
    "how much does it cost to build a covered deck",
    "how much does it cost to replace a deck",
    "how much does it cost to replace an existing deck",
    "how much does it cost to rebuild a deck",
    "how much does it cost to redo a deck",
    "how much does it cost to renovate a deck",
    "how much does it cost to extend a deck",
    "average cost to replace a fence",
}


def assign_campaign(row):
    if row["category"] in ("BOF - Priority 1", "BOF - Priority 2", "Price Discovery"):
        return row["category"]
    if row["category"] == "Manual Review":
        if row["keyword"] in MANUAL_REVIEW_TO_PRICE_DISCOVERY:
            return "Price Discovery"
        return "BOF - Priority 2"
    sys.exit(f"ERROR: unexpected category '{row['category']}' for '{row['keyword']}'")


def main():
    if len(sys.argv) != 2:
        sys.exit("Usage: compile_step3_adgroups.py <path to step1_approved.json>")

    with open(sys.argv[1], encoding="utf-8") as f:
        approved = json.load(f)

    by_keyword = {r["keyword"]: r for r in approved}

    assigned = set()
    out_rows = []
    for ad_group, keywords in AD_GROUPS.items():
        for kw in keywords:
            if kw in assigned:
                sys.exit(f"ERROR: '{kw}' assigned to more than one ad group")
            row = by_keyword.get(kw)
            if not row:
                sys.exit(f"ERROR: '{kw}' not found in approved list (typo?)")
            assigned.add(kw)
            campaign = assign_campaign(row)
            out_rows.append(
                {
                    "campaign": campaign,
                    "ad_group": ad_group,
                    "section": f"{campaign} — {ad_group}",
                    **row,
                }
            )

    missing = [r["keyword"] for r in approved if r["keyword"] not in assigned]
    if missing:
        print(f"ERROR: {len(missing)} approved keywords not assigned to any ad group:")
        for m in missing:
            print(f"  {m}")
        sys.exit(1)

    out_rows.sort(key=lambda r: (r["campaign"], r["ad_group"], -r["avg_monthly_searches"]))

    import csv

    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
        writer.writeheader()
        writer.writerows(out_rows)

    print(f"Wrote {len(out_rows)} rows across {len(AD_GROUPS)} ad group themes (x2 campaigns) to {OUT_CSV}\n")
    campaign_counts = {}
    for r in out_rows:
        campaign_counts[r["campaign"]] = campaign_counts.get(r["campaign"], 0) + 1
    for c, n in campaign_counts.items():
        print(f"Campaign: {c} - {n} keywords")
    print()
    counts = {}
    for r in out_rows:
        r["ad_group"] = r["section"]  # downstream summary groups by section, not bare ad_group
        counts[r["ad_group"]] = counts.get(r["ad_group"], 0) + 1
    for ag, n in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {ag}: {n}")


if __name__ == "__main__":
    main()
