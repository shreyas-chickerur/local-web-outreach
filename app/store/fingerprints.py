"""What this workbench has already shipped, as decision vectors.

The diversity budget compares a new site against the last N generated, because
a generator's characteristic failure is only visible across sites — one page
in isolation always looks deliberate.

Stored rather than recomputed. The point is what was ACTUALLY shipped, which is
not the same as what those leads would produce today: their briefs move, the
generator changes, and recomputing would compare a new site against a history
that never existed.

Each row carries the ruler it was measured with. A vector taken under a
different set of axes is not comparable, and the budget skips it rather than
comparing across instruments — the same rule the census follows.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime

# How far back the budget looks. Ten is the brief's number: far enough that a
# run of similar businesses cannot all collapse onto one look, short enough
# that a decision made months ago does not constrain today's.
WINDOW = 10


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def remember(conn: sqlite3.Connection, lead_id: int, version: int | None,
             ruler: str, values: dict) -> None:
    """Record what one site decided."""
    conn.execute(
        "INSERT INTO fingerprints (lead_id, version, ruler, values_json, at)"
        " VALUES (?,?,?,?,?)",
        (lead_id, version, ruler, json.dumps(values, sort_keys=True), _now()))


def recent(conn: sqlite3.Connection, ruler: str, *, limit: int = WINDOW,
           exclude_lead: int | None = None) -> list[dict]:
    """The last few sites, newest first, measured with this ruler.

    A lead's own earlier versions are excluded when asked: rebuilding one site
    should not have to differ from itself, and without that a second build of
    the same business collides with its own first by construction.
    """
    rows = conn.execute(
        "SELECT lead_id, version, values_json FROM fingerprints"
        " WHERE ruler = ? ORDER BY id DESC LIMIT ?",
        (ruler, limit * 3)).fetchall()
    out: list[dict] = []
    for row in rows:
        if exclude_lead is not None and row["lead_id"] == exclude_lead:
            continue
        try:
            out.append(json.loads(row["values_json"]))
        except json.JSONDecodeError:
            continue
        if len(out) >= limit:
            break
    return out
