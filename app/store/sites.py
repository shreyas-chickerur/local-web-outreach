"""Saving generated sites, one version per attempt.

Nothing is overwritten. Iterating only helps if you can go back to the version
that was better, and comparing what you asked for against what you got is how
you learn which instructions actually work.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime

from app.store.db import operator
from app.store.leads import record


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def save(conn: sqlite3.Connection, lead_id: int, html: str, spec: str,
         notes: dict | None = None, actor: str | None = None) -> int:
    """Store a new version and log it on the lead. Returns the version number."""
    row = conn.execute("SELECT MAX(version) AS v FROM sites WHERE lead_id = ?",
                       (lead_id,)).fetchone()
    version = int(row["v"] or 0) + 1
    who = actor or operator()
    conn.execute(
        "INSERT INTO sites (lead_id, version, spec, notes, html, actor, created_at)"
        " VALUES (?,?,?,?,?,?,?)",
        (lead_id, version, spec, json.dumps(notes or {}), html, who, _now()))
    # The trail is the record of everything done to a lead, and building a site
    # for someone is not a smaller event than correcting their phone number.
    record(conn, lead_id, "site", new_value=f"v{version}",
           note=spec.strip() or "no instructions given", actor=who)
    return version


def versions(conn: sqlite3.Connection, lead_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT version, spec, notes, actor, created_at, LENGTH(html) AS size"
        " FROM sites WHERE lead_id = ? ORDER BY version DESC", (lead_id,))
    out = []
    for row in rows:
        item = dict(row)
        try:
            item["notes"] = json.loads(item["notes"])
        except ValueError:
            item["notes"] = {}
        out.append(item)
    return out


def html_for(conn: sqlite3.Connection, lead_id: int,
             version: int | None = None) -> str | None:
    if version is None:
        row = conn.execute(
            "SELECT html FROM sites WHERE lead_id = ? ORDER BY version DESC LIMIT 1",
            (lead_id,)).fetchone()
    else:
        row = conn.execute(
            "SELECT html FROM sites WHERE lead_id = ? AND version = ?",
            (lead_id, version)).fetchone()
    return row["html"] if row else None
