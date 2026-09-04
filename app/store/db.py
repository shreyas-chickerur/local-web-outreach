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

-- Generated sites, one row per attempt. Versions are never overwritten: the
-- point of iterating is being able to go back to the one that was better.
CREATE TABLE IF NOT EXISTS sites (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id        INTEGER NOT NULL REFERENCES leads(id),
    version        INTEGER NOT NULL,
    -- The version this one was iterated from. NULL for a first build. Version
    -- is a monotonic counter; parent is a pointer — forking from v3 while v7
    -- exists produces v8 with parent 3, never a second v4.
    parent_version INTEGER,
    spec           TEXT NOT NULL DEFAULT '',   -- the sentence, as typed
    spec_json      TEXT NOT NULL DEFAULT '{}', -- the resolved configuration
    notes          TEXT NOT NULL DEFAULT '{}',
    html           TEXT NOT NULL,
    actor          TEXT NOT NULL,
    created_at     TEXT NOT NULL,
    UNIQUE (lead_id, version)
);

-- What a photograph actually shows, said by a person.
-- Nothing here can look at an image: shape is measurable, subject matter is
-- not, and a landscape photograph of raw peppers is still the wrong lead for a
-- dining room. One pass of labelling per lead is cheaper than iterating on a
-- hero nobody can judge automatically.
CREATE TABLE IF NOT EXISTS photo_labels (
    lead_id     INTEGER NOT NULL REFERENCES leads(id),
    url         TEXT NOT NULL,
    label       TEXT NOT NULL,
    -- What you actually wrote. Kept verbatim because it becomes the alt text
    -- on the finished page, which is worth as much as the placement.
    description TEXT NOT NULL DEFAULT '',
    actor     TEXT NOT NULL,
    at        TEXT NOT NULL,
    PRIMARY KEY (lead_id, url)
);

-- Discovery results, cached. A page of prospects is one paid request per
-- category plus one page fetch per business; without this, every reload of the
-- landing page spends that again for data that changes weekly at most.
CREATE TABLE IF NOT EXISTS discovery_cache (
    key        TEXT PRIMARY KEY,
    payload    TEXT NOT NULL,
    fetched_at TEXT NOT NULL
);
"""


# Columns added after the first databases were written. SQLite cannot add a
# column conditionally, so existing files are widened on open. Dropping and
# recreating would lose the versions someone had already built.
_LATER_COLUMNS = (
    ("sites", "parent_version", "INTEGER"),
    ("sites", "spec_json", "TEXT NOT NULL DEFAULT '{}'"),
    ("photo_labels", "description", "TEXT NOT NULL DEFAULT ''"),
)


def _widen(conn: sqlite3.Connection) -> None:
    for table, column, decl in _LATER_COLUMNS:
        existing = {row["name"] for row in
                    conn.execute(f"PRAGMA table_info({table})")}
        if existing and column not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")


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
    _widen(conn)
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
