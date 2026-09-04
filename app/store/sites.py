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
         notes: dict | None = None, actor: str | None = None,
         spec_json: dict | None = None,
         parent_version: int | None = None) -> int:
    """Store a new version and log it on the lead. Returns the version number.

    The version is allocated inside the INSERT rather than read first and
    written after: `SELECT MAX(version)` followed by `INSERT` is a race, and
    UNIQUE(lead_id, version) turns that race into an exception instead of
    preventing it.

    `parent_version` records what this was iterated from. It is a pointer, not
    a sequence — forking from v3 while v7 exists produces v8 whose parent is 3.
    """
    who = actor or operator()
    cursor = conn.execute(
        "INSERT INTO sites (lead_id, version, parent_version, spec, spec_json,"
        "                   notes, html, actor, created_at)"
        " SELECT ?, COALESCE(MAX(version), 0) + 1, ?, ?, ?, ?, ?, ?, ?"
        "   FROM sites WHERE lead_id = ?",
        (lead_id, parent_version, spec, json.dumps(spec_json or {}),
         json.dumps(notes or {}), html, who, _now(), lead_id))
    row = conn.execute("SELECT version FROM sites WHERE id = ?",
                       (cursor.lastrowid,)).fetchone()
    version = int(row["version"])
    # The trail is the record of everything done to a lead, and building a site
    # for someone is not a smaller event than correcting their phone number.
    record(conn, lead_id, "site", new_value=f"v{version}",
           old_value=f"v{parent_version}" if parent_version else None,
           note=spec.strip() or "no instructions given", actor=who)
    return version


def reject(conn: sqlite3.Connection, lead_id: int, instruction: str,
           findings: list[str], actor: str | None = None) -> None:
    """Record an iteration that was refused by the content gatekeeper.

    Nothing is written to `sites` — the previous version stays live. But an
    instruction that produced unsafe output belongs in the trail: discarding it
    silently would hide the most interesting thing that happened.
    """
    record(conn, lead_id, "site_rejected", new_value="; ".join(findings)[:400],
           note=instruction.strip() or "no instructions given", actor=actor)


def versions(conn: sqlite3.Connection, lead_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT version, parent_version, spec, spec_json, notes, actor,"
        " created_at, LENGTH(html) AS size"
        " FROM sites WHERE lead_id = ? ORDER BY version DESC", (lead_id,))
    out = []
    for row in rows:
        item = dict(row)
        for column in ("notes", "spec_json"):
            try:
                item[column] = json.loads(item[column] or "{}")
            except (ValueError, TypeError):
                item[column] = {}
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
