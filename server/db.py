"""SQLite state: jobs, approvals, change requests, event log."""

import json
import os
import sqlite3
import threading
import time

from . import config

_lock = threading.RLock()
_conn = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL,
    step TEXT NOT NULL,
    kind TEXT NOT NULL,              -- run_step | revise_step | selftest
    status TEXT NOT NULL,            -- queued | running | done | failed | blocked
    payload TEXT NOT NULL DEFAULT '{}',
    log TEXT NOT NULL DEFAULT '',
    error TEXT NOT NULL DEFAULT '',
    created_at REAL NOT NULL,
    started_at REAL,
    finished_at REAL
);
CREATE INDEX IF NOT EXISTS jobs_status ON jobs(status);
CREATE TABLE IF NOT EXISTS approvals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL,
    step TEXT NOT NULL,
    payload TEXT NOT NULL,
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS approvals_ps ON approvals(project_id, step);
CREATE TABLE IF NOT EXISTS change_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL,
    step TEXT NOT NULL,
    note TEXT NOT NULL,
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT,
    step TEXT,
    kind TEXT NOT NULL,
    detail TEXT NOT NULL DEFAULT '',
    created_at REAL NOT NULL
);
"""


def conn():
    global _conn
    with _lock:
        if _conn is None:
            os.makedirs(config.STATE_DIR, exist_ok=True)
            _conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
            _conn.row_factory = sqlite3.Row
            _conn.executescript(SCHEMA)
            cols = [r[1] for r in _conn.execute("PRAGMA table_info(jobs)").fetchall()]
            if "model" not in cols:
                _conn.execute("ALTER TABLE jobs ADD COLUMN model TEXT NOT NULL DEFAULT ''")
            _conn.commit()
        return _conn


def execute(sql, params=()):
    with _lock:
        c = conn()
        cur = c.execute(sql, params)
        c.commit()
        return cur


def query(sql, params=()):
    with _lock:
        return [dict(r) for r in conn().execute(sql, params).fetchall()]


def log_event(kind, project_id=None, step=None, detail=""):
    execute(
        "INSERT INTO events (project_id, step, kind, detail, created_at) VALUES (?,?,?,?,?)",
        (project_id, step, kind, detail, time.time()),
    )


def add_job(project_id, step, kind, payload=None):
    cur = execute(
        "INSERT INTO jobs (project_id, step, kind, status, payload, created_at) VALUES (?,?,?,?,?,?)",
        (project_id, step, kind, "queued", json.dumps(payload or {}), time.time()),
    )
    return cur.lastrowid


def get_setting(key, default=""):
    rows = query("SELECT value FROM settings WHERE key=?", (key,))
    return rows[0]["value"] if rows else default


def set_setting(key, value):
    execute("INSERT INTO settings (key, value) VALUES (?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))


def current_model():
    valid = {m["id"] for m in config.MODELS}
    m = get_setting("model", config.DEFAULT_MODEL)
    return m if m in valid else config.DEFAULT_MODEL
