"""What this workbench has already shipped, as decision vectors.

The diversity budget compares a new site against sites already generated,
because a generator's characteristic failure is only visible across sites —
one page in isolation always looks deliberate.

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

# WIDENED FROM TEN. `restaurant-bare` and `salon-rich` shipped identical on
# every axis but mood, accent and hero_subject — three axes, none structural,
# none required-high, an unambiguous collision under the gate's own rule —
# because the two were never within ten of each other in the shared history
# at build time. A restaurant and a salon rendered as the same page in two
# colours, which is the exact failure §2 exists to stop, and the gate that
# exists to stop it never even compared them.
#
# The window exists for a real reason, kept rather than dropped: "far enough
# that a run of similar businesses cannot all collapse onto one look, short
# enough that a decision made months ago does not constrain today's."
# Removing it entirely was tried first and reverted — `test_the_gate_is_
# satisfiable` caught it immediately. An UNBOUNDED comparison against every
# site ever built is not just occasionally tight, it is a ticking failure:
# once total sites built ever exceeds the required-high axes' combined
# cardinality (currently first_screen x type_treatment x architecture = 125),
# the pigeonhole principle guarantees a collision with SOMETHING in history,
# permanently, because nothing ever ages out to make room again. A bounded
# window avoids that by construction — only the last WINDOW are ever
# compared, so satisfiability only depends on room exceeding WINDOW, not on
# room exceeding the tool's entire lifetime volume.
#
# 60, not 10: three times the current nineteen-fixture corpus (room to grow
# during this testing phase without hitting the same bug again at, say, 25
# fixtures) while leaving 65 of the 125 combinations free at any time (52%
# spare) — comfortable room for retries and perturbation to find an unused
# combination cheaply, not just a mathematically nonzero one.
# `test_the_gate_is_satisfiable` holds this arithmetic; if `room` changes
# (adding an axis to `REQUIRED_HIGH`, e.g. the typeface pair), reconsider
# WINDOW against the new number rather than assuming 60 is still comfortable.
WINDOW = 60


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def remember(conn: sqlite3.Connection, lead_id: int, version: int | None,
             ruler: str, values: dict) -> None:
    """Record what one site decided."""
    conn.execute(
        "INSERT INTO fingerprints (lead_id, version, ruler, values_json, at)"
        " VALUES (?,?,?,?,?)",
        (lead_id, version, ruler, json.dumps(values, sort_keys=True), _now()))


def recent(conn: sqlite3.Connection, ruler: str, *,
           limit: int | None = WINDOW,
           exclude_lead: int | None = None) -> list[dict]:
    """Sites measured with this ruler, newest first. `limit=None` (the
    default) is every one of them; a caller that wants a bounded window can
    still ask for one explicitly.

    A lead's own earlier versions are excluded when asked: rebuilding one site
    should not have to differ from itself, and without that a second build of
    the same business collides with its own first by construction.
    """
    if limit is None:
        rows = conn.execute(
            "SELECT lead_id, version, values_json FROM fingerprints"
            " WHERE ruler = ? ORDER BY id DESC", (ruler,)).fetchall()
    else:
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
        if limit is not None and len(out) >= limit:
            break
    return out
