"""
Step 8 item 5 - uploads account-level negative keywords into a client's
Google Ads account: this project's own negative list from Step 1
(output/<project-id>/step1_negative_keywords.csv) plus the standing
cross-client list (data/global_negative_keywords.csv).

Creates one shared negative-keyword list ("<project-id> - Negative
Keywords"), populates it with every keyword from both sources, then
attaches that shared set to every campaign currently in the account via
CampaignSharedSet - there is no working customer-level attachment for
keyword-based negative lists (CustomerNegativeCriterion.negative_keyword_list
exists in the API schema but returns NEGATIVE_KEYWORD_SHARED_SET_DOES_NOT_EXIST
even against a confirmed-ENABLED shared set with all criteria present;
this matches the Ads UI, which also only lets you attach a negative
keyword list to specific campaigns). "Account-wide" in practice means
attached to every campaign that exists right now - re-run this script
(with --attach-only, see below) when a new campaign launches later so it
picks up the same list. Two sequential mutates (see comment at the top of
main() for why), same temp-ID pattern as step8_upload_campaign.py.

Usage:
    venv/bin/python scripts/step8_upload_negatives.py <project-id> <customer_id> \
        [--skip-terms "term1,term2"] [--validate-only]

--skip-terms drops specific literal negative_keyword values from BOTH
source files before upload (comma-separated, case-insensitive exact
match on the keyword text) - use this for a term that's unsafe for THIS
ONE account specifically, without having to edit the source CSVs. If a
global CSV term turns out to be unsafe for every client (as a bare
"hire" entry was - it collided with "hire a painter near me"-style BOF
keywords, since every client here is itself a trade/service business),
fix data/global_negative_keywords.csv directly instead - --skip-terms is
for the one-off case, not a substitute for correcting the master file.

--attach-only <shared_set_resource_name> is a recovery flag: if mutate 1
(create the shared set + criteria) already succeeded but mutate 2 (the
account-wide attach) failed or was never reached, re-running the whole
script would recreate a duplicate shared set. Pass the resource name
mutate 1 already printed and only mutate 2 runs.
"""

import argparse
import csv
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from google.ads.googleads.errors import GoogleAdsException

from lib.google_ads_config import load_client

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MATCH_TYPE_MAP = {
    "Exact": "EXACT",
    "Phrase": "PHRASE",
    "Broad": "BROAD",
}


def load_project_negatives(project_id):
    path = os.path.join(PROJECT_ROOT, "output", project_id, "step1_negative_keywords.csv")
    if not os.path.exists(path):
        sys.exit(f"Missing {path} - run Step 1's negative-keyword build for this project first.")
    rows = []
    with open(path) as f:
        for r in csv.DictReader(f):
            rows.append((r["negative_keyword"].strip(), MATCH_TYPE_MAP[r["match_type"]]))
    return rows


def load_global_negatives():
    path = os.path.join(PROJECT_ROOT, "data", "global_negative_keywords.csv")
    if not os.path.exists(path):
        sys.exit(f"Missing {path}")
    rows = []
    with open(path) as f:
        for r in csv.DictReader(f):
            raw = r["Keyword"].strip()
            # CSV convention: a quoted value ("job") = phrase match; bare = broad.
            if raw.startswith('"') and raw.endswith('"'):
                rows.append((raw.strip('"'), "PHRASE"))
            elif raw.startswith("[") and raw.endswith("]"):
                rows.append((raw.strip("[]"), "EXACT"))
            else:
                rows.append((raw, "BROAD"))
    return rows


def main():
    parser = argparse.ArgumentParser(description="Upload account-level negative keywords (Step 1 project list + global CSV)")
    parser.add_argument("project_id")
    parser.add_argument("customer_id", help="Digits only, no dashes")
    parser.add_argument("--skip-terms", default="", help="Comma-separated keyword text to drop from upload (case-insensitive)")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--only-campaigns", nargs="+", default=None, metavar="NAME",
                        help="Attach only to campaigns with these exact names (default: every non-removed "
                             "campaign). Use on rebuilds so an existing live campaign isn't changed.")
    parser.add_argument("--attach-only", metavar="SHARED_SET_RESOURCE_NAME",
                         help="Recovery mode: skip mutate 1 (shared set + criteria already exist - "
                              "e.g. from a run where mutate 1 succeeded but mutate 2's attach failed) "
                              "and just run the account-wide attach against this existing resource name.")
    args = parser.parse_args()

    customer_id = args.customer_id.replace("-", "")
    skip = {t.strip().lower() for t in args.skip_terms.split(",") if t.strip()}

    negatives = load_project_negatives(args.project_id) + load_global_negatives()

    seen = set()
    deduped = []
    skipped_count = 0
    for text, match_type in negatives:
        key = (text.lower(), match_type)
        if text.lower() in skip:
            skipped_count += 1
            continue
        if key in seen:
            continue
        seen.add(key)
        deduped.append((text, match_type))

    print(f"Loaded {len(negatives)} negative keyword rows ({len(deduped)} unique after dedup, "
          f"{skipped_count} dropped via --skip-terms).")

    client = load_client()
    ga_service = client.get_service("GoogleAdsService")

    # Two sequential atomic mutates, not one: a same-request temp-ID forward reference from
    # the attach operation back to a shared_set_operation created in the same mutate is
    # rejected (NEGATIVE_KEYWORD_SHARED_SET_DOES_NOT_EXIST), even under validate_only. So:
    # (1) create the shared set + its criteria, (2) attach the real resulting resource name
    # to every campaign. There's also backend replication lag between the two: mutate 2 can
    # still fail with the same "does not exist" error for a while right after mutate 1
    # returns a real resource name (seen in practice on ~1000 criteria) - retry with backoff
    # before giving up.

    if args.attach_only:
        real_shared_set_resource_name = args.attach_only
        print(f"--attach-only given, skipping mutate 1. Attaching existing set: {real_shared_set_resource_name}")
    else:
        # --- Mutate 1: shared set + criteria ---
        shared_set_resource_name = f"customers/{customer_id}/sharedSets/-1"

        operations = []

        op = client.get_type("MutateOperation")
        shared_set = op.shared_set_operation.create
        shared_set.resource_name = shared_set_resource_name
        shared_set.name = f"{args.project_id} - Negative Keywords"
        shared_set.type_ = client.enums.SharedSetTypeEnum.NEGATIVE_KEYWORDS
        operations.append(op)

        for text, match_type in deduped:
            op = client.get_type("MutateOperation")
            crit = op.shared_criterion_operation.create
            crit.shared_set = shared_set_resource_name
            crit.keyword.text = text
            crit.keyword.match_type = client.enums.KeywordMatchTypeEnum[match_type]
            operations.append(op)

        print(f"Mutate 1: {len(operations)} operations (1 shared set + {len(deduped)} criteria). "
              f"validate_only={args.validate_only}")

        request = client.get_type("MutateGoogleAdsRequest")
        request.customer_id = customer_id
        request.mutate_operations = operations
        request.validate_only = args.validate_only
        request.partial_failure = False

        response = ga_service.mutate(request=request)

        if args.validate_only:
            print("Mutate 1 validation passed - no errors.")
            print("Skipping mutate 2 validation - it needs a real shared set resource name "
                  "from mutate 1, which validate_only doesn't create. Mutate 1 passing means "
                  "the criteria themselves are valid; mutate 2 is a single well-worn operation.")
            return

        real_shared_set_resource_name = response.mutate_operation_responses[0].shared_set_result.resource_name
        print("Created shared negative keyword list:", real_shared_set_resource_name)

    # --- Mutate 2: attach the shared set to every campaign in the account ---
    # CustomerNegativeCriterion.negative_keyword_list exists in the API schema but does NOT
    # work in practice (confirmed live: NEGATIVE_KEYWORD_SHARED_SET_DOES_NOT_EXIST even once
    # the shared set is confirmed ENABLED with all criteria present via a GoogleAdsService
    # search). There is no true customer-level attachment for keyword-based negative lists -
    # this matches the Ads UI itself, which only ever lets you add a negative keyword list to
    # specific campaigns. "Account-wide" in practice means: attached to every campaign in the
    # account via CampaignSharedSet, and re-attached to any new campaign launched later
    # (Priority 2 / Price Discovery) at that time.
    campaign_query = "SELECT campaign.resource_name, campaign.name FROM campaign WHERE campaign.status != 'REMOVED'"
    campaigns = list(ga_service.search(customer_id=customer_id, query=campaign_query))
    if args.only_campaigns:
        campaigns = [c for c in campaigns if c.campaign.name in args.only_campaigns]
        print(f"Attaching only to: {[c.campaign.name for c in campaigns]}")
    if not campaigns:
        sys.exit("No campaigns found on this account to attach the negative keyword list to.")

    operations = []
    for row in campaigns:
        op = client.get_type("MutateOperation")
        css = op.campaign_shared_set_operation.create
        css.campaign = row.campaign.resource_name
        css.shared_set = real_shared_set_resource_name
        operations.append(op)

    attach_request = client.get_type("MutateGoogleAdsRequest")
    attach_request.customer_id = customer_id
    attach_request.mutate_operations = operations
    attach_request.validate_only = False
    attach_request.partial_failure = False

    delays = [10, 20, 40, 60]
    for attempt, delay in enumerate([0] + delays):
        if delay:
            print(f"Retrying attach in {delay}s (replication lag)...")
            time.sleep(delay)
        try:
            attach_response = ga_service.mutate(request=attach_request)
            for row, result in zip(campaigns, attach_response.mutate_operation_responses):
                print(f"Attached to {row.campaign.name}:", result.campaign_shared_set_result.resource_name)
            return
        except GoogleAdsException as exc:
            still_missing = any(
                "DOES_NOT_EXIST" in str(e.error_code)
                for e in exc.failure.errors
            )
            if not still_missing or attempt == len(delays):
                raise
            print("Shared set not yet visible to this operation type - will retry.")


if __name__ == "__main__":
    main()
