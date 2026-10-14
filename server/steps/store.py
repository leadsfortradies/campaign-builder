"""Read/write project step data under WEB_DATA_ROOT/data/<project_id>/ and
keep projects.json in sync - the cloud equivalent of scripts/lib/webapp_export.py."""

import json
import os

from .. import config, db, projects_store

STEP_LABELS = {
    "step0": "Step 0: Setup",
    "step1": "Step 1: Keyword Research",
    "step2": "Step 2: Location Keywords",
    "campaigns": "Campaigns to Build",
    "step3": "Step 3: Ad Groups",
    "step4": "Step 4: Ad Copy",
    "step5": "Step 6: Landing Pages",
    "step6": "Step 5: Sitelinks, Callouts & Snippets",
}


def data_dir(project_id):
    d = os.path.join(config.WEB_DATA_ROOT, "data", project_id)
    os.makedirs(d, exist_ok=True)
    return d


def read(project_id, name, default=None):
    path = os.path.join(data_dir(project_id), f"{name}.json")
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write(project_id, name, payload):
    path = os.path.join(data_dir(project_id), f"{name}.json")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    os.replace(tmp, path)


def project_label(project_id):
    for p in projects_store.load():
        if p["id"] == project_id:
            return p["label"]
    return project_id


def publish_step(project_id, step, payload, row_count, status="needs_approval"):
    """Write <step>.json and point projects.json at it."""
    write(project_id, step, payload)
    projects_store.update_step(
        project_id, step,
        status=status,
        file=f"data/{project_id}/{step}.json",
        step_label=STEP_LABELS.get(step, step),
        row_count=row_count,
    )


def skip_step(project_id, step, note):
    projects_store.update_step(project_id, step, status="skipped", note=note,
                               step_label=STEP_LABELS.get(step, step))


def approved_rows(project_id, step):
    """The rows the user kept when approving a step (latest approval), falling
    back to the step's full row list for steps approved before the backend
    existed (chat workflow)."""
    rows = db.query("SELECT payload FROM approvals WHERE project_id=? AND step=? ORDER BY id DESC LIMIT 1",
                    (project_id, step))
    if rows:
        payload = json.loads(rows[0]["payload"])
        return payload.get("kept_keywords") or payload.get("kept_items") or []
    data = read(project_id, step) or {}
    return data.get("rows", [])


ALL_CAMPAIGNS = ("BOF - Priority 1", "BOF - Priority 2", "Price Discovery")
MERGED_CAMPAIGN = "BOF - Priority 1 & 2"


def campaign_choice(project_id):
    """What the user picked on the Campaigns step: {"campaigns": [...], "merge_bof": bool}.
    Projects approved before this step existed get all three, kept separate."""
    rows = db.query("SELECT payload FROM approvals WHERE project_id=? AND step='campaigns' ORDER BY id DESC LIMIT 1",
                    (project_id,))
    sel = json.loads(rows[0]["payload"]).get("selection") if rows else None
    picked = [c for c in ALL_CAMPAIGNS if c in ((sel or {}).get("campaigns") or [])] if sel else list(ALL_CAMPAIGNS)
    merge = bool(sel and sel.get("merge_bof")) and "BOF - Priority 1" in picked and "BOF - Priority 2" in picked
    return {"campaigns": picked, "merge_bof": merge}


def ad_copy_campaign(project_id):
    """The campaign Step 4 writes ad copy for: the combined BOF campaign, else
    Priority 1, else Priority 2 if that's all that was chosen."""
    c = campaign_choice(project_id)
    if c["merge_bof"]:
        return MERGED_CAMPAIGN
    for name in ("BOF - Priority 1", "BOF - Priority 2"):
        if name in c["campaigns"]:
            return name
    return None
