"""
One-off: takes the raw keyword_research.py CSV output and a hand-classified
keyword->category mapping, and produces the final categorized CSV for user
review (step 1.9 of PROCESS.md). Classification itself is a judgment call
made by reading the raw data against PROCESS.md's rules - this script just
joins that judgment back onto the real volume/competition/bid numbers so
nothing gets retyped by hand.
"""

import csv
import sys

DECK_CSV = "output/test_deck_fence_auckland/deck.csv"
FENCE_CSV = "output/test_deck_fence_auckland/fence.csv"
OUT_CSV = "output/test_deck_fence_auckland/step1_categorized.csv"

BOF_DECK = [
    "deck builder", "deck builder near me", "deck contractors near me",
    "deck building companies near me", "deck installation",
    "composite decking installation", "deck building company",
    "timber deck builder", "composite deck builder", "deck companies near me",
    "deck installation near me", "deck construction near me",
    "deck contractors", "affordable deck builders near me",
    "best deck builders near me", "composite decking installers near me",
    "local deck builders", "deck and fence company", "deck builders in my area",
    "custom deck builders near me",
    "wood deck builders near me", "deck contractors in my area",
    "deck and fence company near me", "deck building contractors near me",
    "fence and deck company near me", "outdoor deck builders near me",
    "custom decks near me", "wood deck contractors near me",
    "deck construction companies near me", "decking specialists near me",
    "deck installation companies", "local deck builders near me",
    "deck installation companies near me", "composite decking installation near me",
    "deck and fence builders near me", "decking builders", "deck experts near me",
    "best deck companies near me", "composite decking companies near me",
    "build a deck near me", "outdoor deck installers near me",
    "contractors for decks near me", "deck makers near me",
    "fence and deck builders near me", "composite deck companies",
    "deck installers in my area", "small deck builders near me",
    "decking companies in my area", "wood deck installers near me",
    "build me a deck", "best deck builders", "deck and fencing companies near me",
    "home deck builders", "deck and fence builders", "deck construction company",
    "fencing and deck companies near me", "local deck contractors near me",
    "affordable deck builders", "composite decking company near me",
    "deck & fence company",
    "deck builders around me", "deck places near me", "deck building contractor",
    "deck carpenter", "professional deck builders near me",
    "composite decking installer near me", "deck construction contractors",
    "custom deck builder", "deck installation service", "fence and deck companies",
    "decking and fencing companies near me", "local deck builder near me",
    "new deck builder", "timber decking contractors",
    "timber decking installers near me", "deck and fence installers near me",
    "composite deck experts", "deck and fencing company near me",
    "deck installation contractor",
]

PRICE_DECK = [
    "how much does it cost to build a deck", "deck cost calculator",
    "deck cost estimator", "labor cost to build a deck calculator",
    "composite deck cost calculator", "deck price calculator",
    "how much is it to build a deck", "cost to build a deck calculator",
    "how much does it cost to have a deck built", "how much it cost to build a deck",
    "composite decking per m2", "composite decking price calculator",
    "deck building estimator", "composite deck estimate",
    "how much does it cost to get a deck built", "how much does it cost to build a small deck",
    "cost of a new deck calculator", "how much does it cost to install a deck",
    "how much does it cost to build a new deck", "deck price estimator",
    "deck estimate near me", "how much will it cost to build a deck",
    "estimate composite deck cost", "how much does it cost to make a deck",
    "deck installation cost calculator", "decking estimate cost calculator",
    "floating deck cost calculator", "estimated cost to build a deck",
    "how much does it cost for a new deck", "deck building price calculator",
    "deck construction cost estimator", "how much does it cost for composite decking",
    "how much does it cost for decking", "how much do it cost to build a deck",
    "wood deck price calculator", "how expensive is it to build a deck",
    "how much it cost to build deck", "how much does it cost for a composite deck",
    "cost estimate deck construction", "decking costs per square foot",
    "how much does it cost to install composite decking",
    "price per square foot composite decking", "how much should it cost to build a deck",
    "deck price per m2", "how much does it cost to do a deck",
    "how much does it cost to have a deck installed", "how does it cost to build a deck",
    "deck wood cost calculator", "how much does it cost to build a 6x6 deck",
    "new deck cost calculator", "how much does it cost to build an outdoor deck",
    "how much does it cost to build a front deck", "how much does it cost to get decking done",
    "how much does it cost for decking to be installed",
    "how much would it cost to build a small deck", "how much does it cost to put a deck in",
    "how much does it cost to have deck built", "how much does it cost to do decking",
    "timber decking cost calculator", "deck construction cost calculator",
    "deck repair cost calculator", "deck replacement cost calculator",
    "deck replacement cost estimator", "concrete deck cost calculator",
    "covered deck cost calculator", "deck railing cost calculator",
    "deck railing estimator", "deck stairs cost calculator",
]

REVIEW_DECK = [
    ("deck maker", "ambiguous - also a common term for card/board game deck-building tools"),
    ("deckbuilder", "ambiguous - 'deckbuilder' is also a board game genre term"),
    ("ekodeck installation", "narrow brand-specific install term, unclear if worth bidding on"),
    ("ekodeck installers", "narrow brand-specific install term, unclear if worth bidding on"),
    ("replacing a deck board", "repair/maintenance intent, not a new deck build"),
    ("deck and patio contractors near me", "includes patio, which isn't a stated service"),
    ("deck and patio builders near me", "includes patio, which isn't a stated service"),
    ("patio and deck builders near me", "includes patio, which isn't a stated service"),
    ("patio and deck contractors near me", "includes patio, which isn't a stated service"),
    ("deck repair contractors near me", "repair intent, not new build - confirm if in scope"),
    ("deck replacement contractors", "replacement/repair work, not a new build"),
    ("deck replacement contractors near me", "replacement/repair work, not a new build"),
    ("handyman deck builders", "'handyman' signals lower-budget/DIY-adjacent lead quality"),
    ("deck railing installers near me", "component-only (railing), not a full deck build"),
    ("deck railing contractors near me", "component-only (railing), not a full deck build"),
    ("deck railing companies near me", "component-only (railing), not a full deck build"),
    ("pool deck installers near me", "niche (pool decks specifically) - confirm in scope"),
    ("pool deck contractors", "niche (pool decks specifically) - confirm in scope"),
    ("pool deck builders", "niche (pool decks specifically) - confirm in scope"),
    ("pool deck companies", "niche (pool decks specifically) - confirm in scope"),
    ("deck and pergola builders near me", "pergola isn't a stated service"),
    ("deck remodeling contractors near me", "remodel/repair work, not new build"),
    ("deck remodeling contractors", "remodel/repair work, not new build"),
    ("deck and roof contractors near me", "roofing isn't a stated service, different trade"),
    ("concrete deck contractors", "different material scope, may be a different trade (concrete vs timber/composite)"),
    ("concrete deck installation", "different material scope, may be a different trade (concrete vs timber/composite)"),
    ("timber decking installation", "generic 'installation' phrasing - ambiguous DIY vs hire intent"),
    ("modwood decking installation", "NZ-relevant brand but 'installation' phrasing is ambiguous DIY vs hire intent"),
    ("kwila decking installation", "NZ-relevant brand but 'installation' phrasing is ambiguous DIY vs hire intent"),
    ("wpc decking installation", "generic material term, ambiguous DIY vs hire intent"),
    ("how much does it cost to build a covered deck", "covered/roofed deck is a different structure scope - confirm offered"),
    ("deck and stair builders near me", "stairs-specific - unclear if sold as a standalone service"),
    ("outdoor stairs installation", "component-only, ambiguous DIY vs hire intent"),
    ("patio deck fence builders", "mixes patio (not a stated service) with deck/fence"),
    ("deck patio builders", "mixes patio (not a stated service) with deck"),
    ("how much does it cost to replace a deck", "replacement pricing, not a new build"),
    ("how much does it cost to replace an existing deck", "replacement pricing, not a new build"),
    ("how much does it cost to rebuild a deck", "rebuild/renovation pricing, not a new build"),
    ("how much does it cost to redo a deck", "rebuild/renovation pricing, not a new build"),
    ("how much does it cost to renovate a deck", "renovation pricing, not a new build"),
    ("how much does it cost to extend a deck", "extension/modification pricing, not a new build"),
    ("deck constructor", "vague generic phrasing, unclear real search intent"),
    ("decking fitting", "vague generic phrasing, ambiguous DIY vs hire intent"),
    ("deck and patio contractors", "includes patio, which isn't a stated service"),
    ("patio deck contractors near me", "includes patio, which isn't a stated service"),
    ("patio decking installers near me", "includes patio, which isn't a stated service"),
    ("deck and porch contractors near me", "porch (US term) isn't a stated service"),
    ("wood deck installation", "generic 'installation' phrasing - ambiguous DIY vs hire intent"),
    ("outdoor deck installation", "generic 'installation' phrasing - ambiguous DIY vs hire intent"),
    ("deck builders and repair near me", "mixes new-build intent with repair work"),
]

BOF_FENCE = [
    "fencing contractors near me", "fencing co near me", "fencing business near me",
    "fencing contractors", "fence company near me", "fence co near me",
    "fence companies close to me", "fence builder", "fence builders", "fence co",
    "fence fence companies", "fence builder near me", "fencing company",
    "fence installation near me", "fence contractors near me", "fencing services",
    "fencing co", "best fence company near me", "local fence companies",
    "wood fence company near me", "local fencing companies",
    "residential fence company near me", "best fencing companies near me",
    "local fence installers", "fence installation companies near me",
    "premier fence company", "fence companies in my area", "affordable fence company",
    "cheap fence company near me", "top rated fence companies near me",
    "highest rated fence companies near me", "good fencing companies near me",
    "best fencing company", "quality fencing company", "local fencing company near me",
    "reliable fence company near me", "deck and fence company near me",
    "deck and fence company", "fence and deck company near me",
    "fence and deck builders near me", "deck and fencing companies near me",
    "deck and fencing company near me", "fence and deck builders",
    "fence and deck companies", "fencing and deck companies near me",
    "residential fencing companies near me", "backyard fencing companies near me",
    "garden fencing companies near me", "home fencing companies near me",
    "custom fences near me", "local fence builders", "local fence builders near me",
    "fencing builders near me", "fencing builders",
    "wood fence builders near me", "wood fence builders", "wood fence builder",
    "timber fence company", "timber fencing contractors near me",
    "timber fencing contractors", "timber fence contractors near me",
    "timber fence contractors", "colorbond fence contractors",
    "colorbond fencing installation near me", "pool fence company",
    "pool fencing company", "pool fence builder", "pool fencing contractors",
    "pool fence contractors", "pool fencing contractors near me",
    "pool fence contractors near me", "pool fencing installers near me",
]

PRICE_FENCE = [
    "how much does it cost to build a fence", "fence cost calculator",
    "fence price calculator", "fence price estimator", "fencing cost calculator",
    "fence installation cost", "fence cost estimator", "fencing cost",
    "wood fence cost calculator", "how much does it cost to put up a fence",
    "how much does it cost to install a fence", "wood fence installation cost",
    "how much does it cost to fence a yard", "average fence cost",
    "cost to install fence per foot", "how much does it cost to get a fence installed",
    "how much does it cost to have a fence installed", "how much is it to build a fence",
    "how much is it to put up a fence", "how much is it to install a fence",
    "how much does it cost for a fence",
    "how much does it cost to put in a fence", "build a fence cost",
    "cost to put up a fence", "cost to put in a fence",
    "how much would it cost to build a fence", "how much does it cost to get a fence built",
    "how much does it cost to build a wooden fence", "cost of fences and installation",
    "picket fence cost", "wood fence cost", "wood fence prices",
    "cost of colorbond fence per metre", "cost of colorbond fencing per metre",
    "colorbond fencing prices per metre", "colorbond fence price calculator",
    "colorbond fencing cost", "colorbond fence installation cost",
    "colorbond fence cost calculator", "colorbond fencing calculator",
    "timber fence cost calculator", "timber fencing calculator",
    "timber paling fence calculator", "paling fence calculator", "pailing fence calculator",
    "aluminum fence cost calculator", "fence installation price", "fence installation quote",
    "fencing quote calculator", "fencing price calculator", "fencing price estimator",
    "online fence quote calculator", "free fence estimate", "online fence estimator",
    "estimate for fence installation", "how much does it cost to have a fence built",
    "how much does it cost for a wooden fence", "cost to have fence installed",
    "average cost of wood fence", "average cost to install wood fence",
    "average cost of fencing per foot", "average cost of fencing per metre",
    "average price for fence installation", "typical fence cost",
    "typical price for fence installation", "average cost to build fence",
    "average cost to install privacy fence", "average price of fence",
    "average cost of aluminum fence", "average cost of new fence",
    "pool fencing cost", "pool fencing cost per metre installed",
    "pool safety fence cost", "pool fence installation cost",
    "fence replacement cost calculator",
]

REVIEW_FENCE = [
    ("commercial fence company near me", "commercial vs residential scope unclear - may be wrong customer segment"),
    ("fence suppliers near me", "supplier/materials search, not necessarily installation/hire intent"),
    ("commercial fencing companies near me", "commercial vs residential scope unclear - may be wrong customer segment"),
    ("metal fence company near me", "material scope unclear - confirm business works with metal"),
    ("aluminium fence builders", "material scope - confirm business works with aluminium"),
    ("aluminium fence installation", "material scope + generic 'installation' phrasing ambiguous DIY vs hire"),
    ("aluminum fence installation", "material scope + generic 'installation' phrasing ambiguous DIY vs hire"),
    ("pool fence installation", "generic 'installation' phrasing ambiguous DIY vs hire (pool fencing itself is a real NZ service)"),
    ("pool safety fence installation", "generic 'installation' phrasing ambiguous DIY vs hire"),
    ("swimming pool fence installation", "generic 'installation' phrasing ambiguous DIY vs hire"),
    ("glass pool fence installation", "different material/trade - glass fencing is often subcontracted"),
    ("glass fence installation", "different material/trade - glass fencing is often subcontracted"),
    ("glass pool fencing installation", "different material/trade - glass fencing is often subcontracted"),
    ("best pool safety fence", "product-research intent, not clearly a hire-a-builder search"),
    ("picket fence company", "style-specific - confirm business builds this style"),
    ("picket fence builder", "style-specific - confirm business builds this style"),
    ("boundary fencing contractors", "confirm this means residential property-line fencing, not rural boundary work"),
    ("boundary fence contractors", "confirm this means residential property-line fencing, not rural boundary work"),
    ("fence post installation cost", "component-only pricing, not a full fence"),
    ("cost of fence repair", "repair pricing, not a new build"),
    ("average cost to replace a fence", "replacement pricing, not a new build"),
    ("garden fence company near me", "style-specific (garden/decorative fencing) - confirm in scope"),
    ("garden fencing contractors near me", "style-specific (garden/decorative fencing) - confirm in scope"),
    ("garden fence contractors near me", "style-specific (garden/decorative fencing) - confirm in scope"),
]

GAME_TOKENS = [
    "mtg", "yu gi oh", "yugioh", "ygo", "hearthstone", "arkham", "bakugan",
    "buddyfight", "digimon", "pokemon", "pokémon", "marvel deck", "flesh and blood",
    "kards", "archidekt", "edhrec", "royaleapi", "statsroyale", "tapped out",
    "limitless deck", "weiss", "shadowverse", "gloomhaven", "universus", "metazoo",
    "vtes", "ydk", "ygoprodeck", "lor deck", "lotr lcg", "grand archive", "kamigawa",
    "bushiroad", "chaotic deck", "clank deck", "cardkingdom", "gcg deck", "sppd deck",
    "steam deck", "flatpak", "archadeck mtg",
]


def load_rows(path):
    rows = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows[row["keyword"]] = row
    return rows


def main():
    deck_rows = load_rows(DECK_CSV)
    fence_rows = load_rows(FENCE_CSV)
    all_rows = {**deck_rows, **fence_rows}

    buckets = [
        ("Bottom of Funnel", [(kw, "") for kw in BOF_DECK + BOF_FENCE]),
        ("Price Discovery", [(kw, "") for kw in PRICE_DECK + PRICE_FENCE]),
        ("Manual Review", REVIEW_DECK + REVIEW_FENCE),
    ]

    out_rows = []
    seen = set()
    missing = []
    for category, entries in buckets:
        for kw, note in entries:
            if kw in seen:
                continue
            seen.add(kw)
            row = all_rows.get(kw)
            if not row:
                missing.append(kw)
                continue
            if any(tok in kw.lower() for tok in GAME_TOKENS):
                continue
            out_rows.append(
                {
                    "category": category,
                    "keyword": kw,
                    "avg_monthly_searches": row["avg_monthly_searches"],
                    "competition": row["competition"],
                    "low_top_of_page_bid": row["low_top_of_page_bid"],
                    "high_top_of_page_bid": row["high_top_of_page_bid"],
                    "note": note,
                }
            )

    out_rows.sort(key=lambda r: (r["category"], -int(r["avg_monthly_searches"])))

    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
        writer.writeheader()
        writer.writerows(out_rows)

    print(f"Wrote {len(out_rows)} rows to {OUT_CSV}")
    counts = {}
    for r in out_rows:
        counts[r["category"]] = counts.get(r["category"], 0) + 1
    for cat, n in counts.items():
        print(f"  {cat}: {n}")
    if missing:
        print(f"\nWARNING - {len(missing)} keywords not found in source CSVs:")
        for m in missing:
            print(f"  {m}")
        sys.exit(1)


if __name__ == "__main__":
    main()
