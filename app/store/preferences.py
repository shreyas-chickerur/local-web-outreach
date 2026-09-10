"""Repeated operator preferences, accumulated across leads.

BRIEF §5, Slice H item 4: when the same phrase understood from an
instruction shows up across several different leads, it is a stable
preference rather than a one-off for that business — worth surfacing to
the NEXT lead's opening call as a consideration, never a constraint (the
business's own material always wins; see `opening.py`'s own prompt
framing, where this is appended as one more line of context beside the
brief's own evidence, not a rule that overrides it).

Deliberately not fuzzy: an exact string match on `understood`'s own
phrasing, the same closed-vocabulary discipline this project already
applies everywhere else (never invent a similarity nothing measured).
Two differently-worded requests for the same underlying preference are
recorded as two different phrases until they are both phrased the same
way often enough to each clear the threshold on their own.

Scoped to REAL leads only, and not by a check written here — by the
replay invariant this table cannot see around. `opening.opening_spec()`
returns a frozen `design_direction` immediately, before it ever looks at
a `preferences` argument, for any brief that carries one — which is
every fixture in the corpus. A table of accumulated phrases threaded
into a prompt that fixture briefs never reach cannot move what those
fixtures render; `tests/test_render_snapshots.py` and
`tests/test_the_instrument_reproduces.py` staying green with this table
populated is the proof, not an assertion made here.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def record(conn: sqlite3.Connection, lead_id: int, phrases: list[str]) -> None:
    """One iteration's understood phrases, tied to the lead that said them."""
    now = _now()
    for phrase in phrases:
        text = str(phrase or "").strip()
        if not text:
            continue
        conn.execute(
            "INSERT INTO preferences (lead_id, phrase, at) VALUES (?,?,?)",
            (lead_id, text, now))


def repeated(conn: sqlite3.Connection, *, min_leads: int = 3) -> list[str]:
    """Phrases understood on at least `min_leads` DISTINCT leads — a stable
    cross-business preference, not the same conversation repeating itself.

    Ordered by how many leads said it, most-repeated first, so a prompt
    that only has room for a few gets the strongest signal.
    """
    rows = conn.execute(
        "SELECT phrase, COUNT(DISTINCT lead_id) AS n FROM preferences"
        " GROUP BY phrase HAVING n >= ? ORDER BY n DESC, phrase",
        (min_leads,))
    return [row["phrase"] for row in rows]
