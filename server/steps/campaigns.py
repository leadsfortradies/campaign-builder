"""Campaigns step - asks which campaigns to build before ad groups are made.

Choices: BOF - Priority 1, BOF - Priority 2, Price Discovery, and whether
Priority 1 and 2 are combined into one campaign. The answer is read back by
Step 3 (ad groups) and Step 4 (ad copy) via store.campaign_choice().
"""

from ..jobs import register_step
from . import store
from .step3 import _campaign


def run(ctx):
    counts = {c: 0 for c in store.ALL_CAMPAIGNS}
    seen = set()
    for r in store.approved_rows(ctx.project_id, "step1"):
        if r["keyword"] not in seen:
            seen.add(r["keyword"])
            counts[_campaign(r, False)] += 1
    for r in store.approved_rows(ctx.project_id, "step2"):
        if r["keyword"] not in seen:
            seen.add(r["keyword"])
            counts["BOF - Priority 1"] += 1
    store.publish_step(ctx.project_id, "campaigns", {
        "project_id": ctx.project_id, "step": "campaigns", "label": store.project_label(ctx.project_id),
        "counts": counts, "merged_name": store.MERGED_CAMPAIGN,
        "default": store.campaign_choice(ctx.project_id),
    }, row_count=len(store.ALL_CAMPAIGNS))
    ctx.need_approval("Choose which campaigns to build.")


register_step("campaigns")(run)
