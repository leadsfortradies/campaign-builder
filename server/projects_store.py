"""Thread-safe, atomic access to projects.json (the app's project/step index)."""

import json
import os
import threading

from . import config

_lock = threading.RLock()

STEP_ORDER = ["step1", "step2", "step3", "step4", "step5", "step6"]


def load():
    with _lock:
        if not os.path.exists(config.PROJECTS_PATH):
            return []
        with open(config.PROJECTS_PATH, encoding="utf-8") as f:
            return json.load(f)


def _save(projects):
    tmp = config.PROJECTS_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(projects, f, indent=2)
    os.replace(tmp, config.PROJECTS_PATH)


def update_step(project_id, step, **fields):
    """Merge fields into projects.json[project].steps[step]. Returns the
    updated step dict, or None if the project doesn't exist."""
    with _lock:
        projects = load()
        for p in projects:
            if p["id"] == project_id:
                info = p.setdefault("steps", {}).setdefault(step, {})
                info.update(fields)
                _save(projects)
                return info
        return None


def next_step(step):
    if step in STEP_ORDER:
        i = STEP_ORDER.index(step)
        if i + 1 < len(STEP_ORDER):
            return STEP_ORDER[i + 1]
    return None


def create_project(project_id, label, **fields):
    with _lock:
        projects = load()
        if any(p["id"] == project_id for p in projects):
            raise ValueError(f"Project {project_id} already exists")
        projects.append({"id": project_id, "label": label, "steps": {}, **fields})
        _save(projects)


def get(project_id):
    for p in load():
        if p["id"] == project_id:
            return p
    return None


def set_label(project_id, label):
    with _lock:
        projects = load()
        for p in projects:
            if p["id"] == project_id:
                p["label"] = label
                _save(projects)
                return
