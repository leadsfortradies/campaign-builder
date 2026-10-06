"""
Step 8 - uploads the approved BOF - Priority 1 campaign into a client's
Google Ads account, paused. Creates in one atomic mutate call: campaign
budget, campaign (search-only, manual CPC, EU political ads off), location
targeting, ad groups, exact-match keywords, responsive search ads,
sitelinks (per ad group), callouts (account-wide) and a structured snippet
(campaign-wide).

Usage:
    venv/bin/python scripts/step8_upload_campaign.py <project-id> <customer_id> \
        --geo-target-id <id> [--validate-only] [--daily-budget 50]

Reads web/data/<project-id>/step1.json, step2.json, step3.json, step4.json,
step6.json. Does not touch step5.json directly - final URLs come from
step4.json (same values, already merged in).
"""

import argparse
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib.google_ads_config import load_client

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def data_path(project_id, step):
    return os.path.join(PROJECT_ROOT, "web", "data", project_id, f"{step}.json")


def load_json(project_id, step):
    path = data_path(project_id, step)
    if not os.path.exists(path):
        sys.exit(f"Missing {path} - Step {step[-1]} hasn't been approved for this project yet.")
    with open(path) as f:
        return json.load(f)


def build_keyword_bid_map(project_id):
    """keyword text (lower) -> low_bid (top-of-page low estimate), from step1+step2."""
    bid_map = {}
    for step in ("step1", "step2"):
        path = data_path(project_id, step)
        if not os.path.exists(path):
            continue
        for row in load_json(project_id, step)["rows"]:
            kw = row["keyword"].strip().lower()
            low_bid = row.get("low_bid") or 0
            if low_bid > 0 and kw not in bid_map:
                bid_map[kw] = low_bid
    return bid_map


def priority1_keywords_by_adgroup(project_id):
    """Returns {ad_group_name: [keyword_text, ...]} for BOF - Priority 1 only."""
    rows = load_json(project_id, "step3")["rows"]
    by_group = defaultdict(list)
    for r in rows:
        group = r["group"]
        if not group.startswith("BOF - Priority 1"):
            continue
        # group format: "BOF - Priority 1 — <Ad Group Name>"
        ad_group_name = group.split("—", 1)[1].strip()
        by_group[ad_group_name].append(r["keyword"])
    return by_group


def compute_adgroup_default_bids(keywords_by_adgroup, bid_map):
    all_bids = []
    for kws in keywords_by_adgroup.values():
        for kw in kws:
            b = bid_map.get(kw.strip().lower())
            if b:
                all_bids.append(b)
    overall_avg = sum(all_bids) / len(all_bids) if all_bids else 3.0

    defaults = {}
    for ad_group, kws in keywords_by_adgroup.items():
        bids = [bid_map[kw.strip().lower()] for kw in kws if kw.strip().lower() in bid_map]
        defaults[ad_group] = (sum(bids) / len(bids)) if bids else overall_avg
    return defaults, overall_avg


def micros(dollars):
    """Rounds to the nearest cent then converts to micros - CPC bid micros
    must be a multiple of the billable unit (10,000 micros = 1 cent for NZD),
    which an averaged default bid (e.g. $3.466666) won't satisfy otherwise."""
    cents = round(dollars * 100)
    return cents * 10_000


def main():
    parser = argparse.ArgumentParser(description="Upload BOF - Priority 1 campaign to Google Ads (paused)")
    parser.add_argument("project_id")
    parser.add_argument("customer_id", help="Digits only, no dashes")
    parser.add_argument("--geo-target-id", required=True, help="Geo target constant ID for location targeting")
    parser.add_argument("--daily-budget", type=float, default=50.0)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()

    customer_id = args.customer_id.replace("-", "")

    step4 = load_json(args.project_id, "step4")
    step6 = load_json(args.project_id, "step6")

    keywords_by_adgroup = priority1_keywords_by_adgroup(args.project_id)
    bid_map = build_keyword_bid_map(args.project_id)
    adgroup_default_bids, overall_avg = compute_adgroup_default_bids(keywords_by_adgroup, bid_map)

    print("Ad group default CPC bids (first-page estimate, NZD):")
    for ag, bid in adgroup_default_bids.items():
        n_kw = len(keywords_by_adgroup[ag])
        print(f"  {ag}: ${bid:.2f}  ({n_kw} keywords)")
    print(f"  (fallback avg used where no data: ${overall_avg:.2f})\n")

    client = load_client()
    ga_service = client.get_service("GoogleAdsService")

    operations = []
    next_id = -1

    def temp_id():
        nonlocal next_id
        v = next_id
        next_id -= 1
        return v

    # --- Campaign budget ---
    budget_temp_id = temp_id()
    op = client.get_type("MutateOperation")
    budget = op.campaign_budget_operation.create
    budget.resource_name = f"customers/{customer_id}/campaignBudgets/{budget_temp_id}"
    budget.name = f"BOF - Priority 1 Budget - {args.project_id}"
    budget.amount_micros = micros(args.daily_budget)
    budget.delivery_method = client.enums.BudgetDeliveryMethodEnum.STANDARD
    budget.explicitly_shared = False
    operations.append(op)

    # --- Campaign ---
    campaign_temp_id = temp_id()
    campaign_resource_name = f"customers/{customer_id}/campaigns/{campaign_temp_id}"
    op = client.get_type("MutateOperation")
    campaign = op.campaign_operation.create
    campaign.resource_name = campaign_resource_name
    campaign.name = "BOF - Priority 1"
    campaign.status = client.enums.CampaignStatusEnum.PAUSED
    campaign.advertising_channel_type = client.enums.AdvertisingChannelTypeEnum.SEARCH
    campaign.campaign_budget = budget.resource_name
    campaign.manual_cpc = client.get_type("ManualCpc")
    campaign.network_settings.target_search_network = False
    campaign.network_settings.target_content_network = False
    campaign.network_settings.target_partner_search_network = False
    campaign.contains_eu_political_advertising = (
        client.enums.EuPoliticalAdvertisingStatusEnum.DOES_NOT_CONTAIN_EU_POLITICAL_ADVERTISING
    )
    operations.append(op)

    # --- Location targeting (Canterbury) ---
    op = client.get_type("MutateOperation")
    loc_criterion = op.campaign_criterion_operation.create
    loc_criterion.campaign = campaign_resource_name
    loc_criterion.location.geo_target_constant = f"geoTargetConstants/{args.geo_target_id}"
    operations.append(op)

    # --- Ad groups ---
    ad_group_resource_names = {}
    for ad_group_name in keywords_by_adgroup:
        ag_temp_id = temp_id()
        resource_name = f"customers/{customer_id}/adGroups/{ag_temp_id}"
        ad_group_resource_names[ad_group_name] = resource_name

        op = client.get_type("MutateOperation")
        ad_group = op.ad_group_operation.create
        ad_group.resource_name = resource_name
        ad_group.name = ad_group_name
        ad_group.campaign = campaign_resource_name
        ad_group.status = client.enums.AdGroupStatusEnum.ENABLED
        ad_group.type_ = client.enums.AdGroupTypeEnum.SEARCH_STANDARD
        ad_group.cpc_bid_micros = micros(adgroup_default_bids[ad_group_name])
        operations.append(op)

    # --- Keywords (exact match) ---
    for ad_group_name, kws in keywords_by_adgroup.items():
        ad_group_resource_name = ad_group_resource_names[ad_group_name]
        for kw in kws:
            op = client.get_type("MutateOperation")
            criterion = op.ad_group_criterion_operation.create
            criterion.ad_group = ad_group_resource_name
            criterion.status = client.enums.AdGroupCriterionStatusEnum.ENABLED
            criterion.keyword.text = kw
            criterion.keyword.match_type = client.enums.KeywordMatchTypeEnum.EXACT
            own_bid = bid_map.get(kw.strip().lower())
            if own_bid:
                criterion.cpc_bid_micros = micros(own_bid)
            operations.append(op)

    # --- Responsive search ads ---
    for ag in step4["ad_groups"]:
        ad_group_resource_name = ad_group_resource_names.get(ag["name"])
        if not ad_group_resource_name:
            continue  # ad copy exists but ad group not in Priority 1 scope (shouldn't happen)

        op = client.get_type("MutateOperation")
        ad_group_ad = op.ad_group_ad_operation.create
        ad_group_ad.ad_group = ad_group_resource_name
        ad_group_ad.status = client.enums.AdGroupAdStatusEnum.ENABLED

        rsa = ad_group_ad.ad.responsive_search_ad
        ad_group_ad.ad.final_urls.append(ag["final_url"])

        pinned_slots = [
            client.enums.ServedAssetFieldTypeEnum.HEADLINE_1,
            client.enums.ServedAssetFieldTypeEnum.HEADLINE_2,
            client.enums.ServedAssetFieldTypeEnum.HEADLINE_3,
        ]
        for text, slot in zip(ag["headlines_pinned"], pinned_slots):
            asset = client.get_type("AdTextAsset")
            asset.text = text
            asset.pinned_field = slot
            rsa.headlines.append(asset)

        for text in ag["headlines_benefit"]:
            asset = client.get_type("AdTextAsset")
            asset.text = text
            rsa.headlines.append(asset)

        for text in ag["descriptions"]:
            asset = client.get_type("AdTextAsset")
            asset.text = text
            rsa.descriptions.append(asset)

        paths = ag.get("paths", [])
        if len(paths) > 0:
            rsa.path1 = paths[0]
        if len(paths) > 1:
            rsa.path2 = paths[1]

        operations.append(op)

    # --- Sitelink assets (per ad group) ---
    for ag in step6["ad_groups"]:
        ad_group_resource_name = ad_group_resource_names.get(ag["name"])
        if not ad_group_resource_name:
            continue
        for item in ag["sitelinks"]:
            asset_temp_id = temp_id()
            asset_resource_name = f"customers/{customer_id}/assets/{asset_temp_id}"

            op = client.get_type("MutateOperation")
            asset = op.asset_operation.create
            asset.resource_name = asset_resource_name
            asset.final_urls.append(item["url"])
            asset.sitelink_asset.link_text = item["text"]
            asset.sitelink_asset.description1 = item["description_1"]
            asset.sitelink_asset.description2 = item["description_2"]
            operations.append(op)

            op = client.get_type("MutateOperation")
            link = op.ad_group_asset_operation.create
            link.ad_group = ad_group_resource_name
            link.asset = asset_resource_name
            link.field_type = client.enums.AssetFieldTypeEnum.SITELINK
            operations.append(op)

    # --- Callout assets (account-wide) ---
    for callout_text in step6["callouts"]:
        asset_temp_id = temp_id()
        asset_resource_name = f"customers/{customer_id}/assets/{asset_temp_id}"

        op = client.get_type("MutateOperation")
        asset = op.asset_operation.create
        asset.resource_name = asset_resource_name
        asset.callout_asset.callout_text = callout_text
        operations.append(op)

        op = client.get_type("MutateOperation")
        link = op.customer_asset_operation.create
        link.asset = asset_resource_name
        link.field_type = client.enums.AssetFieldTypeEnum.CALLOUT
        operations.append(op)

    # --- Structured snippet (campaign-wide) ---
    snippet = step6["structured_snippets"]
    snippet_header = snippet["header"]
    if snippet_header.strip().lower() == "service catalog":
        snippet_header = "Service catalog"  # exact casing Google Ads requires for this predefined header

    asset_temp_id = temp_id()
    asset_resource_name = f"customers/{customer_id}/assets/{asset_temp_id}"

    op = client.get_type("MutateOperation")
    asset = op.asset_operation.create
    asset.resource_name = asset_resource_name
    asset.structured_snippet_asset.header = snippet_header
    asset.structured_snippet_asset.values.extend(snippet["values"])
    operations.append(op)

    op = client.get_type("MutateOperation")
    link = op.campaign_asset_operation.create
    link.campaign = campaign_resource_name
    link.asset = asset_resource_name
    link.field_type = client.enums.AssetFieldTypeEnum.STRUCTURED_SNIPPET
    operations.append(op)

    print(f"Built {len(operations)} operations. validate_only={args.validate_only}")

    request = client.get_type("MutateGoogleAdsRequest")
    request.customer_id = customer_id
    request.mutate_operations = operations
    request.validate_only = args.validate_only
    request.partial_failure = False

    response = ga_service.mutate(request=request)

    if args.validate_only:
        print("Validation passed - no errors.")
        return

    print(f"Created {len(response.mutate_operation_responses)} resources.")
    print(f"Campaign resource (temp): {campaign_resource_name}")
    for result in response.mutate_operation_responses:
        if result._pb.HasField("campaign_result"):
            print("Real campaign resource name:", result.campaign_result.resource_name)


if __name__ == "__main__":
    main()
