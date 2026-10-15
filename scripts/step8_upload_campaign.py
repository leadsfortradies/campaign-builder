"""
Step 8 - uploads the approved campaign(s) into a client's Google Ads
account, paused. Creates in one atomic mutate call: campaign budget(s),
campaign(s) (search-only, manual CPC, EU political ads off), location
targeting, ad groups, exact-match keywords, responsive search ads,
sitelinks (per ad group), callouts (account-wide, skipping any that already
exist) and a structured snippet (per campaign).

Usage:
    venv/bin/python scripts/step8_upload_campaign.py <project-id> <customer_id> \
        --geo-target-id <id> [<id> ...] [--campaigns "BOF - Priority 1" "Price Discovery"] \
        [--presence-only] [--validate-only] [--daily-budget 50] [--price-discovery-budget 25]

--campaigns defaults to BOF - Priority 1 only (PROCESS.md Step 8 item 3).
Ad group names must be unique across the campaigns uploaded in one run
(step4/step6 are keyed by ad group name).

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


def require_final_domain_confirmed(project_id):
    """Ad copy and sitelinks point at the client's final domain. Don't upload until the
    user has confirmed in the web app (Landing Pages tab) that the domain is connected."""
    path = data_path(project_id, "step5")
    if not os.path.exists(path):
        return
    s5 = json.load(open(path))
    if s5.get("custom_base") and not s5.get("domain_connected"):
        sys.exit(f"Not uploading: the final domain ({s5['custom_base']}) hasn't been confirmed as connected. "
                 "Ask the user 'is the final domain connected?'. They confirm it in the web app's Landing Pages tab. "
                 "Sync the project data afterwards, then re-run.")


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


def keywords_by_campaign(project_id, campaigns):
    """Returns {campaign: {ad_group_name: [keyword_text, ...]}} for the given campaigns."""
    rows = load_json(project_id, "step3")["rows"]
    out = {c: defaultdict(list) for c in campaigns}
    for r in rows:
        # group format: "<Campaign> — <Ad Group Name>"
        campaign, _, ad_group_name = r["group"].partition("—")
        campaign, ad_group_name = campaign.strip(), ad_group_name.strip()
        if campaign in out:
            if len(r["keyword"].split()) > 10:  # Google Ads limit: 10 words per keyword
                print(f"  SKIPPING (over 10 words, Google won't accept it): {r['keyword']}")
                continue
            out[campaign][ad_group_name].append(r["keyword"])
    seen = {}
    for c, groups in out.items():
        for ag in groups:
            if ag in seen:
                sys.exit(f"Ad group name '{ag}' appears in both '{seen[ag]}' and '{c}' - step4/6 are keyed by name.")
            seen[ag] = c
    return out


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
    parser = argparse.ArgumentParser(description="Upload campaign(s) to Google Ads (paused)")
    parser.add_argument("project_id")
    parser.add_argument("customer_id", help="Digits only, no dashes")
    parser.add_argument("--geo-target-id", required=True, nargs="+", help="Geo target constant ID(s) for location targeting")
    parser.add_argument("--campaigns", nargs="+", default=["BOF - Priority 1"],
                        choices=["BOF - Priority 1", "BOF - Priority 2", "Bottom of Funnel", "Price Discovery"])
    parser.add_argument("--daily-budget", type=float, default=50.0, help="Daily budget for every campaign unless overridden")
    parser.add_argument("--price-discovery-budget", type=float, default=None)
    parser.add_argument("--min-bid", type=float, default=0.0,
                        help="Floor for every keyword/ad group CPC bid (Keyword Planner's low first-page estimate is "
                             "sometimes unusably low, e.g. $0.09)")
    parser.add_argument("--bid-file", default=None,
                        help="JSON {'bids': {keyword: dollars}} - explicit per-keyword CPC bids (e.g. previous max "
                             "CPCs, else 30-day average CPC). Replaces the Step 1 first-page estimate for every "
                             "keyword it lists.")
    parser.add_argument("--presence-only", action="store_true",
                        help="Target people physically in the locations only (not 'presence or interest')")
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    require_final_domain_confirmed(args.project_id)

    customer_id = args.customer_id.replace("-", "")

    step4 = load_json(args.project_id, "step4")
    step6 = load_json(args.project_id, "step6")

    by_campaign = keywords_by_campaign(args.project_id, args.campaigns)
    keywords_by_adgroup = {ag: kws for groups in by_campaign.values() for ag, kws in groups.items()}
    empty = [c for c, g in by_campaign.items() if not g]
    if empty:
        sys.exit(f"No approved keywords found for campaign(s): {empty}")
    bid_map = {k: max(v, args.min_bid) for k, v in build_keyword_bid_map(args.project_id).items()}
    if args.bid_file:
        with open(args.bid_file) as f:
            bid_map.update({k.strip().lower(): float(v) for k, v in json.load(f)["bids"].items()})
    adgroup_default_bids, overall_avg = compute_adgroup_default_bids(keywords_by_adgroup, bid_map)
    adgroup_default_bids = {ag: max(b, args.min_bid) for ag, b in adgroup_default_bids.items()}
    overall_avg = max(overall_avg, args.min_bid)

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

    # --- Campaigns (budget, campaign, locations, ad groups) ---
    campaign_resource_names = {}
    ad_group_resource_names = {}
    for campaign_name, groups in by_campaign.items():
        budget_temp_id = temp_id()
        op = client.get_type("MutateOperation")
        budget = op.campaign_budget_operation.create
        budget.resource_name = f"customers/{customer_id}/campaignBudgets/{budget_temp_id}"
        budget.name = f"{campaign_name} Budget - {args.project_id}"
        amount = args.daily_budget
        if campaign_name == "Price Discovery" and args.price_discovery_budget is not None:
            amount = args.price_discovery_budget
        budget.amount_micros = micros(amount)
        budget.delivery_method = client.enums.BudgetDeliveryMethodEnum.STANDARD
        budget.explicitly_shared = False
        operations.append(op)

        campaign_temp_id = temp_id()
        campaign_resource_name = f"customers/{customer_id}/campaigns/{campaign_temp_id}"
        campaign_resource_names[campaign_name] = campaign_resource_name
        op = client.get_type("MutateOperation")
        campaign = op.campaign_operation.create
        campaign.resource_name = campaign_resource_name
        campaign.name = campaign_name
        campaign.status = client.enums.CampaignStatusEnum.PAUSED
        campaign.advertising_channel_type = client.enums.AdvertisingChannelTypeEnum.SEARCH
        campaign.campaign_budget = budget.resource_name
        campaign.manual_cpc = client.get_type("ManualCpc")
        campaign.network_settings.target_google_search = True
        campaign.network_settings.target_search_network = False
        campaign.network_settings.target_content_network = False
        campaign.network_settings.target_partner_search_network = False
        if args.presence_only:
            campaign.geo_target_type_setting.positive_geo_target_type = (
                client.enums.PositiveGeoTargetTypeEnum.PRESENCE
            )
        campaign.contains_eu_political_advertising = (
            client.enums.EuPoliticalAdvertisingStatusEnum.DOES_NOT_CONTAIN_EU_POLITICAL_ADVERTISING
        )
        operations.append(op)

        for geo_id in args.geo_target_id:
            op = client.get_type("MutateOperation")
            loc_criterion = op.campaign_criterion_operation.create
            loc_criterion.campaign = campaign_resource_name
            loc_criterion.location.geo_target_constant = f"geoTargetConstants/{geo_id}"
            operations.append(op)

        for ad_group_name in groups:
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
            continue  # ad copy exists but ad group not in the campaigns being uploaded

        op = client.get_type("MutateOperation")
        ad_group_ad = op.ad_group_ad_operation.create
        ad_group_ad.ad_group = ad_group_resource_name
        ad_group_ad.status = client.enums.AdGroupAdStatusEnum.ENABLED

        rsa = ad_group_ad.ad.responsive_search_ad
        ad_group_ad.ad.final_urls.append(ag["final_url"])

        # All 3 pinned headlines share position 1 (PROCESS.md Step 4 item 4) -
        # Google rotates among them in that slot, rather than each pinned to
        # its own distinct position 1/2/3.
        for text in ag["headlines_pinned"]:
            asset = client.get_type("AdTextAsset")
            asset.text = text
            asset.pinned_field = client.enums.ServedAssetFieldTypeEnum.HEADLINE_1
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
    # Rebuilds already have customer-level callouts; skip any whose text
    # already exists (case-insensitive) rather than creating duplicates.
    existing_callouts = {
        row.asset.callout_asset.callout_text.strip().lower()
        for row in ga_service.search(
            customer_id=customer_id,
            query="SELECT asset.callout_asset.callout_text FROM customer_asset "
                  "WHERE customer_asset.field_type = 'CALLOUT' AND customer_asset.status != 'REMOVED'",
        )
    }
    for callout_text in step6["callouts"]:
        if callout_text.strip().lower() in existing_callouts:
            print(f"  callout already on account, skipping: {callout_text}")
            continue
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

    for campaign_name, campaign_resource_name in campaign_resource_names.items():
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
    print(f"Campaign resources (temp): {campaign_resource_names}")
    for result in response.mutate_operation_responses:
        if result._pb.HasField("campaign_result"):
            print("Real campaign resource name:", result.campaign_result.resource_name)


if __name__ == "__main__":
    main()
