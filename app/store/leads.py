"""Leads and their audit trail.

What you learn at the front door outranks anything a directory publishes, so an
operator's confirmation overrides the corroborated value — but it never
overwrites it. The directory's claim stays in the stored brief, the operator's
value is applied on read, and the event row records both, who said so, when,
and why. Read backwards, the trail explains every value on the screen.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from urllib.parse import urlparse

from app.store import photos
from app.store.db import operator
from app.workbench.match import name_tokens
from app.workbench.resolve import town_of

# "website" is here because a listing's URL is as correctable as its phone
# number, and the correction is worth the same audit trail.
VERIFIABLE = ("address", "phone", "hours", "website")
STATUSES = ("new", "to visit", "visited", "interested", "not interested")


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def lead_key(name: str, location: str | None) -> str:
    """One business is one row, however it was typed in.

    "Hutchins BBQ" and "hutchins bbq, frisco tx" are the same lead; keying on
    the raw query would file them separately and split their history in two.

    The town is parsed rather than taken as the first comma-separated part,
    because `location` is sometimes a bare city and sometimes a full street
    address — which made the same business key as "frisco" once and
    "2770 main st #155" the next time.
    """
    tokens = " ".join(sorted(name_tokens(name)))
    return f"{tokens}|{town_of(location or '')}"


def site_host(url: str | None) -> str:
    """The registrable part of a website, as an identity for the business."""
    if not url:
        return ""
    host = urlparse(url if "//" in url else f"//{url}").netloc.lower()
    return host[4:] if host.startswith("www.") else host


def save_brief(conn: sqlite3.Connection, brief_json: dict) -> int:
    """Insert or refresh a lead. Returns its id.

    A re-run refreshes what the sources say and leaves status and history
    alone: research is disposable, what you were told is not.
    """
    key = lead_key(brief_json["name"], brief_json.get("location"))
    now = _now()
    row = conn.execute("SELECT id FROM leads WHERE key = ?", (key,)).fetchone()
    # A business looked up by name and by URL must land on the same lead. Two
    # rows would split its history, and the confirmation you recorded after
    # talking to them would silently stop applying.
    host = site_host(brief_json.get("website_url"))
    if row is None and host:
        for other in conn.execute(
                "SELECT id, website_url FROM leads WHERE website_url IS NOT NULL"):
            if site_host(other["website_url"]) == host:
                row = other
                break
    payload = json.dumps(brief_json)
    if row is None:
        cur = conn.execute(
            "INSERT INTO leads (key, name, location, website_url, brief_json,"
            " created_at, updated_at) VALUES (?,?,?,?,?,?,?)",
            (key, brief_json["name"], brief_json.get("location"),
             brief_json.get("website_url"), payload, now, now))
        return int(cur.lastrowid or 0)
    conn.execute(
        "UPDATE leads SET name=?, location=?, website_url=?, brief_json=?,"
        " updated_at=? WHERE id=?",
        (brief_json["name"], brief_json.get("location"),
         brief_json.get("website_url"), payload, now, row["id"]))
    return int(row["id"])


def record(conn: sqlite3.Connection, lead_id: int, kind: str, *,
           field: str | None = None, old_value: str | None = None,
           new_value: str | None = None, note: str | None = None,
           actor: str | None = None) -> None:
    conn.execute(
        "INSERT INTO events (lead_id, at, actor, kind, field, old_value,"
        " new_value, note) VALUES (?,?,?,?,?,?,?,?)",
        (lead_id, _now(), actor or operator(), kind, field, old_value,
         new_value, note))


def events(conn: sqlite3.Connection, lead_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM events WHERE lead_id = ? ORDER BY id DESC", (lead_id,))
    return [dict(r) for r in rows]


def set_status(conn: sqlite3.Connection, lead_id: int, status: str,
               note: str | None = None) -> None:
    if status not in STATUSES:
        raise ValueError(f"unknown status {status!r} — one of {', '.join(STATUSES)}")
    row = conn.execute("SELECT status FROM leads WHERE id = ?", (lead_id,)).fetchone()
    if row is None:
        raise ValueError(f"no lead {lead_id}")
    conn.execute("UPDATE leads SET status=?, updated_at=? WHERE id=?",
                 (status, _now(), lead_id))
    record(conn, lead_id, "status", old_value=row["status"], new_value=status,
           note=note)


def verify(conn: sqlite3.Connection, lead_id: int, field: str, value: str,
           note: str | None = None, actor: str | None = None) -> None:
    """Record what you were actually told, and what it replaced."""
    if field not in VERIFIABLE:
        raise ValueError(f"cannot verify {field!r} — one of {', '.join(VERIFIABLE)}")
    if not value.strip():
        raise ValueError("a confirmed value cannot be blank")
    brief = load_brief(conn, lead_id)
    previous = next((f.get("value") for f in brief.get("facts", [])
                     if f.get("field") == field), None)
    # Confirming what the sources already said is not a correction, and the
    # trail should not imply the value changed when it did not.
    kind = "verified" if previous == value.strip() else "corrected"
    record(conn, lead_id, kind, field=field, old_value=previous,
           new_value=value.strip(), note=note, actor=actor)


def load_brief(conn: sqlite3.Connection, lead_id: int) -> dict:
    row = conn.execute("SELECT brief_json FROM leads WHERE id = ?",
                       (lead_id,)).fetchone()
    if row is None:
        raise ValueError(f"no lead {lead_id}")
    return json.loads(row["brief_json"])


def _overrides(conn: sqlite3.Connection, lead_id: int) -> dict[str, dict]:
    """The newest operator statement per field. Later rows win."""
    latest: dict[str, dict] = {}
    for event in reversed(events(conn, lead_id)):
        if event["kind"] in ("verified", "corrected") and event["field"]:
            latest[event["field"]] = event
    return latest


def brief_with_overrides(conn: sqlite3.Connection, lead_id: int) -> dict:
    """The stored brief as it should be read: your answers on top.

    The source's own claim is kept alongside as `superseded`, because a value
    you were given at the door is worth more than a directory's but is not a
    reason to pretend the directory never disagreed.
    """
    brief = load_brief(conn, lead_id)
    row = conn.execute("SELECT id, status FROM leads WHERE id = ?",
                       (lead_id,)).fetchone()
    brief["lead_id"] = lead_id
    brief["status"] = row["status"]
    brief["events"] = events(conn, lead_id)
    brief["photo_labels"] = photos.labels_for(conn, lead_id)

    overrides = _overrides(conn, lead_id)
    facts = brief.get("facts", [])
    for fact in facts:
        event = overrides.pop(fact.get("field"), None)
        if event is None:
            continue
        if fact.get("value") != event["new_value"]:
            fact["superseded"] = fact.get("value")
        fact["value"] = event["new_value"]
        fact["confidence"] = "operator_verified"
        fact["score"] = 100
        fact["verified_by"] = event["actor"]
        fact["verified_at"] = event["at"]
        fact["verified_note"] = event["note"]
        fact["sources"] = []
        fact["candidates"] = []
        fact["dissent"] = []
    # A field nobody published, that you then established, is still a fact.
    for field, event in overrides.items():
        facts.append({
            "field": field, "label": field.title(), "value": event["new_value"],
            "confidence": "operator_verified", "score": 100,
            "corroborations": 1, "sources": [], "candidates": [], "dissent": [],
            "verified_by": event["actor"], "verified_at": event["at"],
            "verified_note": event["note"],
        })
    brief["facts"] = facts
    # A question you have answered is no longer a question.
    answered = {f["field"] for f in facts if f["confidence"] == "operator_verified"}
    brief["open_questions"] = [
        q for q in brief.get("open_questions", [])
        if not any(word in q.lower() for word in _QUESTION_WORDS(answered))]
    return brief


def _QUESTION_WORDS(fields: set[str]) -> list[str]:  # noqa: N802
    words = {"address": ["street address"], "phone": ["phone number", "customers actually call"],
             "hours": ["opening hours"]}
    return [w for f in fields for w in words.get(f, [])]


def all_leads(conn: sqlite3.Connection) -> list[dict]:
    """Every saved lead, most recently touched first.

    Carries the last thing that happened to each one: a list of names and
    statuses does not tell you what you were doing, and "corrected their hours,
    Tuesday" is what makes a lead pickup-able a week later.
    """
    rows = conn.execute(
        "SELECT l.id, l.name, l.location, l.website_url, l.status, l.updated_at,"
        " (SELECT COUNT(*) FROM events e WHERE e.lead_id = l.id) AS event_count,"
        " (SELECT e.kind || CASE WHEN e.field IS NOT NULL THEN ' ' || e.field"
        "         ELSE '' END FROM events e WHERE e.lead_id = l.id"
        "  ORDER BY e.id DESC LIMIT 1) AS last_action,"
        " (SELECT e.at FROM events e WHERE e.lead_id = l.id"
        "  ORDER BY e.id DESC LIMIT 1) AS last_action_at"
        " FROM leads l ORDER BY l.updated_at DESC")
    return [dict(r) for r in rows]
