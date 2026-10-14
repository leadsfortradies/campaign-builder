"""
Step 4 ad copy for Rowdy Builders (Manawatu rebuild, 2026-10-13) - both
campaigns (BOF - Priority 1 and Price Discovery), at the user's request.

Per ad group: 3 headlines pinned to position 1 (closest match to the ad
group's keywords), 12 benefit headlines, 4 descriptions (each containing one
of the ad group's keywords), 2 display paths, final URL from step5.json.

Benefit headlines only use facts confirmed on Rowdy's own sites
(palmydecksandfences / palmerstonnorthfences / palmerstonnorthdecks) or the
generic ones PROCESS.md allows. "Fully insured" confirmed by the user in
chat 2026-10-13.

Usage:
    venv/bin/python scripts/build_step4_adcopy_rowdy_manawatu.py
"""

import csv
import json
import sys

PROJECT = "rowdy-builders-manawatu"
OUT_CSV = f"output/{PROJECT}/step4_ad_copy.csv"
STEP5 = f"web/data/{PROJECT}/step5.json"

BENEFITS = [
    "100+ Projects Completed",
    "10+ Years Experience",
    "Fully Insured",
    "Free On-Site Quotes",
    "Written Quote In 48 Hours",
    "One Fixed Price In Writing",
    "No Surprise Extras",
    "Whoever Quotes It Builds It",
    "Built For Manawatū Weather",
    "5-Star Rated",
    "Priced To Compete",
    "Palmy Born & Bred",
]


def benefits(*swaps):
    """Shared benefit set with 1-2 service-specific swaps: (old, new)."""
    out = list(BENEFITS)
    for old, new in swaps:
        out[out.index(old)] = new
    return out


FENCE_SWAPS = (("Priced To Compete", "Old Fence Hauled Away"), ("Palmy Born & Bred", "Posts Concreted To Depth"))
DECK_SWAPS = (("Palmy Born & Bred", "Pine, Hardwood & Composite"),)
QUOTE_SWAPS = (("Palmy Born & Bred", "Free No-Obligation Quote"),)

AD_GROUPS = {
    # ---------------- BOF - Priority 1 ----------------
    "Deck Builders": {
        "pinned": ["Deck Builders Palmerston North", "Deck Builders Near Me", "Deck Building Company"],
        "benefits": benefits(*DECK_SWAPS),
        "descriptions": [
            "Deck builders in Palmerston North. Free on-site quote, written price within 48 hours.",
            "Local deck contractors near me. Pine, hardwood and composite decks built to last.",
            "Whoever quotes your deck builds it. One fixed price, no surprise extras. Fully insured.",
            "100+ projects completed. Get your new deck built by a 5-star rated Palmy builder.",
        ],
        "paths": ["Decks", "Palmerston-Nth"],
    },
    "Composite Decks": {
        "pinned": ["Composite Deck Builder", "Composite Decking Installers", "Composite Decks Palmy"],
        "benefits": benefits(("Palmy Born & Bred", "No Oiling, No Splinters")),
        "descriptions": [
            "Composite deck builder in Palmerston North. Free on-site quote, written within 48 hours.",
            "Composite decking installation that keeps its colour and just needs a wash. No oiling.",
            "Whoever quotes your composite deck builds it. One fixed price, no surprise extras.",
            "100+ projects completed across Palmy and Manawatū. Fully insured, 5-star rated.",
        ],
        "paths": ["Composite", "Decks"],
    },
    "Timber Decks": {
        "pinned": ["Timber Deck Builders", "Kwila Decking Installation", "Wood Deck Builders Near Me"],
        "benefits": benefits(("Palmy Born & Bred", "Pine & Hardwood Decks")),
        "descriptions": [
            "Timber decking installation in Palmerston North. Pine, kwila and hardwood decks.",
            "Wood deck builders near me. Free on-site quote with a written price within 48 hours.",
            "Kwila decking installation by the same builder who quotes it. No surprise extras.",
            "100+ projects completed. Fully insured, 5-star rated. Built for Manawatū weather.",
        ],
        "paths": ["Timber", "Decks"],
    },
    "Deck & Fence Builders": {
        "pinned": ["Deck And Fence Builders", "Deck & Fence Builders Near Me", "Fence And Deck Builders"],
        "benefits": benefits(("Palmy Born & Bred", "Decks, Fences & Pergolas")),
        "descriptions": [
            "Deck and fence builders in Palmerston North. Free on-site quote, written in 48 hours.",
            "Local deck and fence installers near me. One fixed price in writing, no surprise extras.",
            "Fence and deck builders with 100+ projects completed. Fully insured and 5-star rated.",
            "Whoever quotes it builds it. Decks, fences and pergolas built for Manawatū weather.",
        ],
        "paths": ["Decks-Fences", "Palmy"],
    },
    "Fence Builders": {
        "pinned": ["Fencing Contractors Near Me", "Fence Builders Near Me", "Fence Company Near Me"],
        "benefits": benefits(*FENCE_SWAPS),
        "descriptions": [
            "Fencing contractors near me. Free on-site quote with a written price within 48 hours.",
            "Local fence builders in Palmy. Posts concreted to proper depth, old fence hauled away.",
            "Fence company with 100+ projects completed. One fixed price, no surprise extras.",
            "Timber, Colorbond, aluminium and more. Fence installers who are fully insured.",
        ],
        "paths": ["Fencing", "Palmerston-Nth"],
    },
    "Fencing Palmerston North": {
        "pinned": ["Fencing Palmerston North", "Fencers Palmerston North", "Fences Palmerston North"],
        "benefits": benefits(*FENCE_SWAPS),
        "descriptions": [
            "Fencing in Palmerston North. Free on-site quote with a written price within 48 hours.",
            "Fence builders in Palmerston North. Posts concreted to depth, old fence hauled away.",
            "Fencing contractors in Palmerston North with 100+ projects completed. Fully insured.",
            "Whoever quotes your fence builds it. One fixed price in writing, no surprise extras.",
        ],
        "paths": ["Fencing", "Palmerston-Nth"],
    },
    "Fencing Manawatu, Levin & Marton": {
        "pinned": ["Fencing Manawatu", "Fencing Levin", "Fencing Marton"],
        "benefits": benefits(*FENCE_SWAPS),
        "descriptions": [
            "Fencing in Manawatū, Levin and Marton. Free on-site quote, written price within 48 hours.",
            "Fencing contractors for Manawatū and Levin. Posts concreted to depth, old fence removed.",
            "Fences built across Manawatū with 100+ projects completed. Fully insured, 5-star rated.",
            "Whoever quotes your fence builds it. One fixed price in writing, no surprise extras.",
        ],
        "paths": ["Fencing", "Manawatu"],
    },
    "Brick Fences": {
        "pinned": ["Brick Fence Builders", "Brick Fence Builders Near Me", "Brick Fences Palmerston North"],
        "benefits": benefits(("Priced To Compete", "Old Fence Hauled Away"), ("Palmy Born & Bred", "All Fence Types Built")),
        "descriptions": [
            "Brick fence builders in Palmerston North. Free on-site quote, written within 48 hours.",
            "Brick fence builders near me with 100+ projects completed. Fully insured, 5-star rated.",
            "Whoever quotes your brick fence builds it. One fixed price, no surprise extras.",
            "Local fence builders for brick, timber, Colorbond and more. Built for Manawatū weather.",
        ],
        "paths": ["Brick-Fences", "Palmy"],
    },
    "Timber Fences": {
        "pinned": ["Timber Fence Installers", "Timber Fence Builders", "Paling Fence Installation"],
        "benefits": benefits(*FENCE_SWAPS),
        "descriptions": [
            "Timber fence installers in Palmerston North. Free on-site quote, written within 48 hours.",
            "Timber fence builders who concrete posts to proper depth. Old fence hauled away.",
            "Paling fence installation with one fixed price in writing. No surprise extras.",
            "Wood fence builders near me with 100+ projects completed. Fully insured, 5-star rated.",
        ],
        "paths": ["Timber-Fences", "Palmy"],
    },
    "Aluminium & Metal Fences": {
        "pinned": ["Aluminium Fence Installers", "Colorbond Fence Installers", "Steel Fence Installers"],
        "benefits": benefits(("Priced To Compete", "Old Fence Hauled Away"), ("Palmy Born & Bred", "No Staining Needed")),
        "descriptions": [
            "Aluminium fence installers in Palmerston North. Free on-site quote within 48 hours.",
            "Colorbond fence installers. Low-maintenance fencing that holds its colour. No staining.",
            "Aluminium fence installation with one fixed price in writing. No surprise extras.",
            "Steel and iron fence installers with 100+ projects completed. Fully insured.",
        ],
        "paths": ["Aluminium", "Fences"],
    },
    "Pergolas": {
        "pinned": ["Pergola Builders Near Me", "Pergolas Palmerston North", "Custom Built Pergolas"],
        "benefits": benefits(("Palmy Born & Bred", "Freestanding Or Attached")),
        "descriptions": [
            "Pergola builders near me. Free on-site quote with a written price within 48 hours.",
            "Custom built pergolas in Palmerston North, freestanding or attached to the house.",
            "Pergola installers with 100+ projects completed. One fixed price, no surprise extras.",
            "Whoever quotes your pergola builds it. Fully insured, 5-star rated, local to Palmy.",
        ],
        "paths": ["Pergolas", "Palmerston-Nth"],
    },
    "Pool Fencing": {
        "pinned": ["Pool Fencing Installers", "Pool Fence Installers Near Me", "Pool Fencing Palmerston North"],
        "benefits": benefits(("Priced To Compete", "Built To NZ Pool Rules"), ("Palmy Born & Bred", "Aluminium & Glass Options")),
        "descriptions": [
            "Pool fencing installers in Palmerston North. Free on-site quote within 48 hours.",
            "Pool fence installation built to meet NZ pool barrier rules. Aluminium or glass.",
            "Pool fence installers near me with 100+ projects completed. Fully insured.",
            "Swimming pool fence installation with one fixed price in writing. No surprise extras.",
        ],
        "paths": ["Pool-Fencing", "Palmy"],
    },
    # ---------------- Price Discovery ----------------
    "Deck Costs": {
        "pinned": ["Get A Price For Your Deck", "Need A Price For Your Deck?", "Get Your New Deck Priced"],
        "benefits": benefits(*QUOTE_SWAPS),
        "descriptions": [
            "How much does it cost to build a deck? Get a free on-site quote, written in 48 hours.",
            "Deck pricing in Palmerston North. One fixed price in writing, no surprise extras.",
            "Get a free deck quote from a builder with 100+ projects completed. Fully insured.",
            "Pine, hardwood or composite. We'll price your deck after a free on-site visit.",
        ],
        "paths": ["Deck-Cost", "Free-Quote"],
    },
    "Fence Costs": {
        "pinned": ["Get A Price For Your Fence", "Need A Price For Your Fence?", "Get Your New Fence Priced"],
        "benefits": benefits(("Priced To Compete", "Old Fence Hauled Away"), ("Palmy Born & Bred", "Free No-Obligation Quote")),
        "descriptions": [
            "How much does a fence cost? Get a free on-site quote with a written price in 48 hours.",
            "Fence installation cost in writing. One fixed price per job, no surprise extras.",
            "Get a free fence quote from a builder with 100+ projects completed. Fully insured.",
            "Fencing prices for Palmerston North and Manawatū. Posts concreted to proper depth.",
        ],
        "paths": ["Fence-Cost", "Free-Quote"],
    },
    "Timber Fence Costs": {
        "pinned": ["Get A Timber Fence Price", "Need A Timber Fence Price?", "Get Your Timber Fence Priced"],
        "benefits": benefits(("Priced To Compete", "Old Fence Hauled Away"), ("Palmy Born & Bred", "Free No-Obligation Quote")),
        "descriptions": [
            "Timber fence cost in writing. Free on-site quote with a fixed price within 48 hours.",
            "Wood fence prices for Palmerston North. One fixed price, no surprise extras.",
            "Paling fence cost from a builder with 100+ projects completed. Fully insured.",
            "Get your timber fence priced properly. Posts concreted to depth, old fence hauled away.",
        ],
        "paths": ["Timber-Fence", "Cost"],
    },
    "Aluminium, Brick & Colorbond Fence Costs": {
        "pinned": ["Need An Aluminium Fence Price?", "Get A Colorbond Fence Price", "Get A Brick Fence Price"],
        "benefits": benefits(("Priced To Compete", "Old Fence Hauled Away"), ("Palmy Born & Bred", "Free No-Obligation Quote")),
        "descriptions": [
            "Aluminium fence cost in writing. Free on-site quote with a fixed price within 48 hours.",
            "Colorbond fence installation cost for Palmerston North. One fixed price, no extras.",
            "Brick fence cost, aluminium or Colorbond. Get a free quote from a fully insured builder.",
            "100+ projects completed. Get your new fence priced properly by a local builder.",
        ],
        "paths": ["Fence-Cost", "Free-Quote"],
    },
    "Pergola Costs": {
        "pinned": ["Get A Price For Your Pergola", "Need A Price For A Pergola?", "Get Your Pergola Priced"],
        "benefits": benefits(("Palmy Born & Bred", "Free No-Obligation Quote")),
        "descriptions": [
            "How much does a pergola cost? Get a free on-site quote, written within 48 hours.",
            "Pergola prices for Palmerston North. One fixed price in writing, no surprise extras.",
            "Get a free pergola quote from a builder with 100+ projects completed. Fully insured.",
            "Pergola installation cost depends on size and roofing. We'll price yours on site.",
        ],
        "paths": ["Pergola-Cost", "Free-Quote"],
    },
    "Pool Fencing Costs": {
        "pinned": ["Get A Pool Fence Price", "Need A Pool Fence Price?", "Get Your Pool Fence Priced"],
        "benefits": benefits(("Priced To Compete", "Built To NZ Pool Rules"), ("Palmy Born & Bred", "Free No-Obligation Quote")),
        "descriptions": [
            "Pool fencing cost in writing. Free on-site quote with a fixed price within 48 hours.",
            "Pool fencing prices for Palmerston North. One fixed price, no surprise extras.",
            "Get a free pool fence quote from a builder with 100+ projects completed. Insured.",
            "Pool fencing cost per metre depends on the fence type. We'll price yours on site.",
        ],
        "paths": ["Pool-Fence", "Cost"],
    },
    "Covered Deck Costs": {
        "pinned": ["Get A Price For A Deck Roof", "Need A Covered Deck Price?", "Get Your Deck Roof Priced"],
        "benefits": benefits(("Palmy Born & Bred", "Use Your Deck Year Round")),
        "descriptions": [
            "Covered deck cost in writing. Free on-site quote with a fixed price within 48 hours.",
            "Deck roof cost for Palmerston North homes. One fixed price, no surprise extras.",
            "Cost to cover a deck depends on size and roofing. We'll price yours on site, free.",
            "Get a roof over your deck from a builder with 100+ projects completed. Fully insured.",
        ],
        "paths": ["Covered-Deck", "Cost"],
    },
}

BANNED = ["—", "–", "!"]


def main():
    urls = {g["name"]: g["url"] for g in json.load(open(STEP5))["ad_groups"]}
    step3 = {r["ad_group"] for r in csv.DictReader(open(f"output/{PROJECT}/step3_adgroups.csv"))}
    errors = []
    if set(AD_GROUPS) != step3:
        errors.append(f"ad group mismatch vs step3: {set(AD_GROUPS) ^ step3}")

    rows = []
    for name, ag in AD_GROUPS.items():
        if name not in urls:
            errors.append(f"{name}: no final URL in step5.json")
        hl = ag["pinned"] + ag["benefits"]
        if len(ag["pinned"]) != 3 or len(ag["benefits"]) != 12 or len(set(h.lower() for h in hl)) != 15:
            errors.append(f"{name}: need 3 pinned + 12 unique benefit headlines")
        if len(ag["descriptions"]) != 4 or len(ag["paths"]) != 2:
            errors.append(f"{name}: need 4 descriptions, 2 paths")
        checks = [(h, 30, "headline") for h in hl] + [(d, 90, "description") for d in ag["descriptions"]] + [
            (p, 15, "path") for p in ag["paths"]]
        for text, limit, kind in checks:
            if len(text) > limit:
                errors.append(f"{name}: {kind} too long ({len(text)}>{limit}): {text}")
            if any(b in text for b in BANNED):
                errors.append(f"{name}: banned character in {kind}: {text}")
        for p in ag["paths"]:
            if " " in p:
                errors.append(f"{name}: space in path {p}")

        rows += [(name, "Headline", f"H{i + 1} (pinned to position 1)", t) for i, t in enumerate(ag["pinned"])]
        rows += [(name, "Headline", f"Benefit {i + 1} (unpinned)", t) for i, t in enumerate(ag["benefits"])]
        rows += [(name, "Description", f"D{i + 1}", t) for i, t in enumerate(ag["descriptions"])]
        rows += [(name, "Display Path", f"Path {i + 1}", t) for i, t in enumerate(ag["paths"])]
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
