"""The workspace conversation.

The one place model-written prose is allowed, and the reason it is allowed here
is the reason it is forbidden everywhere else. The no-prose rule exists because
a sentence invented about a business could reach a page shown to its owner, who
knows whether it is true. A message to the operator is not that: they are
looking at the page it describes, they asked the question, and they can see for
themselves whether the answer is right.

So the separation is structural rather than remembered. Assistant text lives in
this table, reaches the workspace, and has no path into `app/site/render.py` —
there is no function here that a renderer calls, and a test asserts the
generator does not import this module. Same discipline as the actor column on
`photo_labels`: enforced by where the data can go.

A turn is tied to the version it produced. A rejected instruction and a question
back both produced none, and say so by leaving it null.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

ROLES = ("user", "assistant")
# Long enough for a designer explaining a decision, short enough that nobody
# mistakes this for somewhere to put a document.
MAX_TEXT = 4000


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def add(conn: sqlite3.Connection, lead_id: int, role: str, text: str,
        *, version: int | None = None) -> int:
    """One turn. Returns its id."""
    if role not in ROLES:
        raise ValueError(f"unknown role {role!r} — one of {', '.join(ROLES)}")
    body = (text or "").strip()
    if not body:
        raise ValueError("an empty message records nothing")
    cursor = conn.execute(
        "INSERT INTO messages (lead_id, role, text, version, at)"
        " VALUES (?,?,?,?,?)",
        (lead_id, role, body[:MAX_TEXT], version, _now()))
    return int(cursor.lastrowid or 0)


def thread(conn: sqlite3.Connection, lead_id: int) -> list[dict]:
    """The conversation, oldest first — the order it was said in."""
    return [dict(row) for row in conn.execute(
        "SELECT id, role, text, version, at FROM messages"
        " WHERE lead_id = ? ORDER BY id", (lead_id,))]


def opened(conn: sqlite3.Connection, lead_id: int) -> bool:
    """Has the thread been started?

    The workspace opens on the design's own rationale rather than an empty box
    — a designer handing over work, not a tool waiting for input — and that
    first turn is written once.
    """
    row = conn.execute(
        "SELECT 1 FROM messages WHERE lead_id = ? LIMIT 1",
        (lead_id,)).fetchone()
    return row is not None
