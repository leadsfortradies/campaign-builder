"""
Syncs a step's output CSV into the web app's project/step structure.

Usage:
    venv/bin/python scripts/webapp_sync.py step0 <project-id> "<label>" <info.json>
    venv/bin/python scripts/webapp_sync.py step1 <project-id> "<label>" <step1_categorized.csv>
    venv/bin/python scripts/webapp_sync.py step2 <project-id> "<label>" <step2_filtered.csv>
    venv/bin/python scripts/webapp_sync.py step3 <project-id> "<label>" <step3_adgroups.csv>
    venv/bin/python scripts/webapp_sync.py step4 <project-id> "<label>" <step4_ad_copy.csv>
    venv/bin/python scripts/webapp_sync.py step5 <project-id> "<label>"
    venv/bin/python scripts/webapp_sync.py step6 <project-id> "<label>" <step6_sitelinks.csv> [<callouts.txt> <snippets.txt>]
    venv/bin/python scripts/webapp_sync.py skip <project-id> "<label>" step2 "<note explaining why>"

step6's optional <callouts.txt> is one callout per line (account-wide,
max 6). <snippets.txt>'s first line is the structured snippet header
(e.g. "Service Catalog"), remaining lines are its values. Omit both to
update sitelinks only and keep whatever callouts/snippets are already
saved for this project.

step0's <info.json> is a dict of whatever business-info fields have been
collected so far in chat (business_name, business_logo_path,
years_experience, completed_projects, certifications, work_photo_paths,
team_photo_paths, service_areas, other_info) - see PROCESS.md Step 0.

project-id: short hyphenated slug, e.g. "deck-fence-auckland". Reused across
steps for the same business/campaign.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib.webapp_export import (
    mark_step_skipped,
    write_step0_business_info,
    write_step4_adcopy_csv,
    write_step5_landing_pages,
    write_step6_sitelinks_csv,
    write_step_data_csv,
)

STEP_GROUP_FIELDS = {
    "step1": ("category", "Category"),
    "step2": ("location", "Location"),
    "step3": ("section", "Campaign — Ad Group"),
}


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)

    kind = sys.argv[1]

    if kind == "step0":
        if len(sys.argv) != 5:
            sys.exit("Usage: webapp_sync.py step0 <project-id> \"<label>\" <info.json>")
        _, _, project_id, label, info_path = sys.argv
        if not os.path.exists(info_path):
            sys.exit(f"JSON not found: {info_path}")
        with open(info_path, encoding="utf-8") as f:
            info = json.load(f)
        write_step0_business_info(project_id, label, info)
        return

    if kind == "skip":
        if len(sys.argv) != 6:
            sys.exit("Usage: webapp_sync.py skip <project-id> \"<label>\" <step> \"<note>\"")
        _, _, project_id, label, step, note = sys.argv
        mark_step_skipped(project_id, label, step, note)
        return

    if kind == "step4":
        if len(sys.argv) != 5:
            sys.exit("Usage: webapp_sync.py step4 <project-id> \"<label>\" <step4_ad_copy.csv>")
        _, _, project_id, label, csv_path = sys.argv
        if not os.path.exists(csv_path):
            sys.exit(f"CSV not found: {csv_path}")
        write_step4_adcopy_csv(project_id, label, csv_path)
        return

    if kind == "step5":
        if len(sys.argv) != 4:
            sys.exit("Usage: webapp_sync.py step5 <project-id> \"<label>\"")
        _, _, project_id, label = sys.argv
        write_step5_landing_pages(project_id, label)
        return

    if kind == "step6":
        if len(sys.argv) not in (5, 7):
            sys.exit(
                "Usage: webapp_sync.py step6 <project-id> \"<label>\" <step6_sitelinks.csv> "
                "[<callouts.txt> <snippets.txt>]"
            )
        project_id, label, csv_path = sys.argv[2], sys.argv[3], sys.argv[4]
        if not os.path.exists(csv_path):
            sys.exit(f"CSV not found: {csv_path}")

        callouts = None
        snippet_header = None
        snippet_values = None
        if len(sys.argv) == 7:
            callouts_path, snippets_path = sys.argv[5], sys.argv[6]
            if not os.path.exists(callouts_path):
                sys.exit(f"Callouts file not found: {callouts_path}")
            if not os.path.exists(snippets_path):
                sys.exit(f"Snippets file not found: {snippets_path}")
            with open(callouts_path, encoding="utf-8") as f:
                callouts = [line.strip() for line in f if line.strip()]
            with open(snippets_path, encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]
            if not lines:
                sys.exit(f"Snippets file is empty: {snippets_path}")
            snippet_header, snippet_values = lines[0], lines[1:]

        write_step6_sitelinks_csv(
            project_id, label, csv_path,
            callouts=callouts, snippet_header=snippet_header, snippet_values=snippet_values,
        )
        return

    if kind not in STEP_GROUP_FIELDS:
        sys.exit(f"Unknown step '{kind}'. Expected one of: 'step0', {list(STEP_GROUP_FIELDS)}, 'step4', 'step5', 'step6', or 'skip'")

    if len(sys.argv) != 5:
        sys.exit(f"Usage: webapp_sync.py {kind} <project-id> \"<label>\" <csv-path>")

    _, _, project_id, label, csv_path = sys.argv
    group_field, group_label = STEP_GROUP_FIELDS[kind]
    if not os.path.exists(csv_path):
        sys.exit(f"CSV not found: {csv_path}")

    write_step_data_csv(project_id, kind, label, group_label, group_field, csv_path)


if __name__ == "__main__":
    main()
