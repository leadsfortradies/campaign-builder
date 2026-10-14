"""
Shared helpers for syncing campaign-builder output into the web app's
project/step structure (web/projects.json + web/data/<project_id>/<step>.json).

Every step's JSON file uses the same shape so the front-end has one generic
renderer for both Step 1 (grouped by category) and Step 3 (grouped by ad
group):

    {
      "project_id": "...",
      "step": "step1",
      "label": "...",
      "group_label": "Category",
      "rows": [{"group": "...", "keyword": "...", "avg_monthly_searches": N,
                "competition": "...", "low_bid": N, "high_bid": N, "note": ""}]
    }
"""

import csv
import json
import os

WEB_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "web")
PROJECTS_PATH = os.path.join(WEB_ROOT, "projects.json")

STEP_LABELS = {
    "step0": "Step 0: Setup",
    "step1": "Step 1: Keyword Research",
    "step2": "Step 2: Location Keywords",
    "step3": "Step 3: Ad Groups",
    "step4": "Step 4: Ad Copy",
    "step5": "Step 5: Landing Pages",
    "step6": "Step 6: Sitelinks, Callouts & Snippets",
}

# Nothing is compulsory at intake (PROCESS.md Step 0, 2026-10-15); the step that
# needs a missing item is what blocks, not Step 0 itself.
STEP0_REQUIRED_FIELDS = ()


def load_projects():
    if not os.path.exists(PROJECTS_PATH):
        return []
    with open(PROJECTS_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_projects(projects):
    with open(PROJECTS_PATH, "w", encoding="utf-8") as f:
        json.dump(projects, f, indent=2)


def find_or_create_project(projects, project_id, label):
    for p in projects:
        if p["id"] == project_id:
            return p
    p = {"id": project_id, "label": label, "steps": {}}
    projects.append(p)
    return p


def write_step0_business_info(project_id, label, info, status="approved"):
    """Persists whatever business info has been collected in chat (PROCESS.md
    Step 0 - there's no web app UI for this step). `info` is a dict that may
    contain: business_name, business_logo_path, years_experience,
    completed_projects, certifications, work_photo_paths (list),
    team_photo_paths (list), service_areas, other_info. Any field not passed
    is left as whatever was already stored, so this is safe to call
    repeatedly as more info comes in across the conversation rather than
    needing it all up front.

    Image paths should already point into web/data/<project_id>/assets/ -
    copy the file there before calling this, don't leave it wherever the
    user originally dropped it.

    Returns the list of still-missing required fields (business_name,
    business_logo_path, service_areas) so the caller knows whether it's
    safe to move on to Step 4/5 without asking the user anything further.
    """
    data_dir = os.path.join(WEB_ROOT, "data", project_id)
    out_path = os.path.join(data_dir, "step0.json")

    existing = {}
    if os.path.exists(out_path):
        with open(out_path, encoding="utf-8") as f:
            existing = json.load(f)

    merged = {**existing, **{k: v for k, v in info.items() if v is not None}}
    merged["project_id"] = project_id
    merged["step"] = "step0"
    merged["label"] = label

    os.makedirs(data_dir, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2)

    missing = [field for field in STEP0_REQUIRED_FIELDS if not merged.get(field)]

    projects = load_projects()
    project = find_or_create_project(projects, project_id, label)
    project["steps"]["step0"] = {
        "status": status if not missing else "pending_review",
        "file": f"data/{project_id}/step0.json",
        "step_label": STEP_LABELS["step0"],
    }
    save_projects(projects)
    print(f"Wrote business info to {out_path}; updated {PROJECTS_PATH}")
    if missing:
        print(f"Still missing required field(s): {', '.join(missing)}")
    return missing


def write_step_data_csv(project_id, step, label, group_label, group_field, csv_path, status="pending_review"):
    """group_field is the CSV column holding the grouping value (category for
    step1, ad_group for step3)."""
    rows = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append(
                {
                    "group": r[group_field],
                    "keyword": r["keyword"],
                    "avg_monthly_searches": int(r["avg_monthly_searches"]),
                    "competition": r["competition"],
                    "low_bid": round(float(r.get("low_top_of_page_bid", r.get("low_bid", 0)) or 0), 2),
                    "high_bid": round(float(r.get("high_top_of_page_bid", r.get("high_bid", 0)) or 0), 2),
                    "note": r.get("note", ""),
                }
            )

    data_dir = os.path.join(WEB_ROOT, "data", project_id)
    os.makedirs(data_dir, exist_ok=True)
    out_path = os.path.join(data_dir, f"{step}.json")
    payload = {
        "project_id": project_id,
        "step": step,
        "label": label,
        "group_label": group_label,
        "rows": rows,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    projects = load_projects()
    project = find_or_create_project(projects, project_id, label)
    project["steps"][step] = {
        "status": status,
        "file": f"data/{project_id}/{step}.json",
        "step_label": STEP_LABELS.get(step, step),
        "row_count": len(rows),
    }
    save_projects(projects)
    print(f"Wrote {len(rows)} rows to {out_path}; updated {PROJECTS_PATH}")


def write_step4_adcopy_csv(project_id, label, csv_path, status="pending_review"):
    """step4_ad_copy.csv columns: ad_group, field_type, slot, text, char_count.
    field_type is one of "Headline" / "Description" / "Display Path" /
    "Final URL"; for Headline rows, slot is "H<n> (pinned to position 1)" for
    the 3 pinned exact-match headlines or "Benefit <n> (unpinned)" for the
    other 12 - the front-end only needs to know pinned vs not. "Final URL" is
    optional - one row per ad group, the landing page URL from Step 5."""
    ad_groups = {}
    with open(csv_path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            group = ad_groups.setdefault(
                r["ad_group"],
                {"name": r["ad_group"], "final_url": "", "headlines_pinned": [], "headlines_benefit": [], "descriptions": [], "paths": []},
            )
            text, slot, field_type = r["text"], r["slot"], r["field_type"]
            if field_type == "Headline":
                target = group["headlines_pinned"] if "pinned to position" in slot else group["headlines_benefit"]
                target.append(text)
            elif field_type == "Description":
                group["descriptions"].append(text)
            elif field_type == "Display Path":
                group["paths"].append(text)
            elif field_type == "Final URL":
                group["final_url"] = text

    data_dir = os.path.join(WEB_ROOT, "data", project_id)
    os.makedirs(data_dir, exist_ok=True)
    out_path = os.path.join(data_dir, "step4.json")
    payload = {
        "project_id": project_id,
        "step": "step4",
        "label": label,
        "ad_groups": list(ad_groups.values()),
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    item_count = sum(
        len(g["headlines_pinned"]) + len(g["headlines_benefit"]) + len(g["descriptions"]) + len(g["paths"])
        for g in ad_groups.values()
    )

    projects = load_projects()
    project = find_or_create_project(projects, project_id, label)
    project["steps"]["step4"] = {
        "status": status,
        "file": f"data/{project_id}/step4.json",
        "step_label": STEP_LABELS["step4"],
        "row_count": item_count,
    }
    save_projects(projects)
    print(f"Wrote {len(ad_groups)} ad groups ({item_count} items) to {out_path}; updated {PROJECTS_PATH}")


def write_step5_landing_pages(project_id, label, mode=None, urls=None, status="pending_review", design_source_url=None):
    """Seeds/updates web/data/<project_id>/step5.json.

    ad_groups are seeded from the project's step4.json (same ad groups that
    already have written copy) the first time this runs; later calls merge
    in `urls` (a dict of {ad_group_name: url}) and keep whatever was already
    stored for ad groups not mentioned. `mode` is "urls", "build_template"
    (new pages from the site template) or "build_designed" (site template
    layout re-skinned with an existing site's design system; pass that
    site's link as `design_source_url`) - pass None to leave whatever is
    already stored (or unset, pre-choice). Legacy "build_site" is read as
    "build_template".

    Used both by the web app's own /approve round-trip and directly by
    Claude when the user pastes landing page URLs into chat instead of
    typing them into the browser - in that case call this then set
    status="approved" once every ad group has a URL.
    """
    data_dir = os.path.join(WEB_ROOT, "data", project_id)
    step5_path = os.path.join(data_dir, "step5.json")
    step4_path = os.path.join(data_dir, "step4.json")

    if os.path.exists(step5_path):
        with open(step5_path, encoding="utf-8") as f:
            existing = json.load(f)
        ad_groups = existing.get("ad_groups", [])
        if mode is None:
            mode = existing.get("mode")
        if design_source_url is None:
            design_source_url = existing.get("design_source_url")
    else:
        ad_groups = []
        if os.path.exists(step4_path):
            with open(step4_path, encoding="utf-8") as f:
                step4 = json.load(f)
            ad_groups = [{"name": g["name"], "url": ""} for g in step4.get("ad_groups", [])]

    by_name = {g["name"]: g for g in ad_groups}
    for name, url in (urls or {}).items():
        by_name.setdefault(name, {"name": name, "url": ""})["url"] = url

    os.makedirs(data_dir, exist_ok=True)
    payload = {
        "project_id": project_id,
        "step": "step5",
        "label": label,
        "mode": mode,
        "design_source_url": design_source_url,
        "ad_groups": list(by_name.values()),
    }
    with open(step5_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    projects = load_projects()
    project = find_or_create_project(projects, project_id, label)
    project["steps"]["step5"] = {
        "status": status,
        "file": f"data/{project_id}/step5.json",
        "step_label": STEP_LABELS["step5"],
        "row_count": len(by_name),
    }
    save_projects(projects)
    print(f"Wrote {len(by_name)} ad groups to {step5_path}; updated {PROJECTS_PATH}")


def write_step6_sitelinks_csv(
    project_id,
    label,
    csv_path,
    callouts=None,
    snippet_header=None,
    snippet_values=None,
    status="pending_review",
):
    """step6_sitelinks.csv columns: ad_group, sitelink_number, sitelink_text,
    sitelink_char_count, description_1, description_1_char_count,
    description_2, description_2_char_count, final_url.

    callouts (account-wide list of strings) and snippet_header/snippet_values
    (the structured snippet's header, e.g. "Service Catalog", and its list of
    values) are optional - when omitted, any existing values already in
    step6.json for this project are kept rather than wiped."""
    ad_groups = {}
    with open(csv_path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            group = ad_groups.setdefault(r["ad_group"], {"name": r["ad_group"], "sitelinks": []})
            group["sitelinks"].append(
                {
                    "text": r["sitelink_text"],
                    "description_1": r["description_1"],
                    "description_2": r["description_2"],
                    "url": r["final_url"],
                }
            )

    data_dir = os.path.join(WEB_ROOT, "data", project_id)
    os.makedirs(data_dir, exist_ok=True)
    out_path = os.path.join(data_dir, "step6.json")

    existing = {}
    if os.path.exists(out_path):
        with open(out_path, encoding="utf-8") as f:
            existing = json.load(f)

    payload = {
        "project_id": project_id,
        "step": "step6",
        "label": label,
        "ad_groups": list(ad_groups.values()),
        "callouts": callouts if callouts is not None else existing.get("callouts", []),
        "structured_snippets": (
            {"header": snippet_header, "values": snippet_values}
            if snippet_header is not None
            else existing.get("structured_snippets", {"header": "Service Catalog", "values": []})
        ),
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    item_count = (
        sum(len(g["sitelinks"]) for g in ad_groups.values())
        + len(payload["callouts"])
        + len(payload["structured_snippets"]["values"])
    )

    projects = load_projects()
    project = find_or_create_project(projects, project_id, label)
    project["steps"]["step6"] = {
        "status": status,
        "file": f"data/{project_id}/step6.json",
        "step_label": STEP_LABELS["step6"],
        "row_count": item_count,
    }
    save_projects(projects)
    print(
        f"Wrote {len(ad_groups)} ad groups ({item_count} total items incl. "
        f"callouts/snippets) to {out_path}; updated {PROJECTS_PATH}"
    )


def mark_step_skipped(project_id, label, step, note):
    projects = load_projects()
    project = find_or_create_project(projects, project_id, label)
    project["steps"][step] = {
        "status": "skipped",
        "note": note,
        "step_label": STEP_LABELS.get(step, step),
    }
    save_projects(projects)
    print(f"Marked {project_id}/{step} as skipped; updated {PROJECTS_PATH}")
