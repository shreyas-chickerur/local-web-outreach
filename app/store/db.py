"""SQLite, on the standard library. One file, one user, no migrations engine.

The schema is created if missing and never rewritten in place; adding a column
means adding it here with a guard, so an existing database on disk keeps its
rows. Losing what you were told at a business's front door because a schema
changed would be worse than any convenience gained.
"""

from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

DEFAULT_PATH = Path(os.environ.get("WORKBENCH_DB", "workbench.db"))

_SCHEMA = """
CREATE TABLE IF NOT EXISTS leads (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    key          TEXT NOT NULL UNIQUE,   -- normalised name+location
    name         TEXT NOT NULL,
    location     TEXT,
    website_url  TEXT,
    status       TEXT NOT NULL DEFAULT 'new',
    brief_json   TEXT NOT NULL,
    created_at   TEXT NOT NULL,
    updated_at   TEXT NOT NULL
);

-- Append-only. Nothing in this table is ever updated or deleted: a correction
-- to a correction is another row, so the trail stays readable backwards.
CREATE TABLE IF NOT EXISTS events (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id    INTEGER NOT NULL REFERENCES leads(id),
    at         TEXT NOT NULL,
    actor      TEXT NOT NULL,
    kind       TEXT NOT NULL,      -- verified | corrected | status | note
    field      TEXT,
    old_value  TEXT,
    new_value  TEXT,
    note       TEXT
);
CREATE INDEX IF NOT EXISTS events_lead ON events(lead_id, id);

-- Discovery results, cached. A page of prospects is one paid request per
-- category plus one page fetch per business; without this, every reload of the
-- landing page spends that again for data that changes weekly at most.
CREATE TABLE IF NOT EXISTS discovery_cache (
    key        TEXT PRIMARY KEY,
    payload    TEXT NOT NULL,
    fetched_at TEXT NOT NULL
);
"""


def connect(path: Path | str | None = None) -> sqlite3.Connection:
    target = Path(path) if path is not None else DEFAULT_PATH
    if target.parent != Path(""):
        target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(target, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    # Survives an interrupted write, which a local tool will eventually see.
    conn.execute("PRAGMA journal_mode = WAL")
    conn.executescript(_SCHEMA)
    return conn


@contextmanager
def session(path: Path | str | None = None) -> Iterator[sqlite3.Connection]:
    """A connection that is always closed.

    `with sqlite3.connect(...)` commits but does not close, which leaks a file
    handle per request until the server runs out of them.
    """
    conn = connect(path)
    try:
        yield conn
    finally:
        conn.close()


def operator() -> str:
    """Who is making changes.

    This is attribution, not authentication: it labels a change so you can read
    the trail back later, and anyone with access to this machine can write
    under this name. Do not treat it as proof of who did something.
    """
    return (os.environ.get("WORKBENCH_OPERATOR")
            or os.environ.get("USER") or "operator").strip()
