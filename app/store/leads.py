"""Leads and their audit trail.

What you learn at the front door outranks anything a directory publishes, so an
operator's confirmation overrides the corroborated value — but it never
overwrites it. The directory's claim stays in the stored brief, the operator's
value is applied on read, and the event row records both, who said so, when,
and why. Read backwards, the trail explains every value on the screen.
"""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import UTC, datetime
from urllib.parse import urlparse

from app.store import photos
from app.store.db import operator
from app.workbench.match import name_tokens
from app.workbench.resolve import town_of

# "website" is here because a listing's URL is as correctable as its phone
# number, and the correction is worth the same audit trail.
VERIFIABLE_FACTS = ("address", "phone", "hours", "website")

# Everything else worth confirming lives under `published`: read off the
# business's own site by one source, with nothing to corroborate it and, until
# now, no way to say it was wrong. Four fields could be corrected; the rest of
# a generated page — its tagline, its story, what the business sells, who to
# email — could not be touched at all.
#
# `where` is the key under `published` ("" means the brief's own top level);
# `shape` is how the operator's typing is read back into it. The audit trail
# always keeps the raw text they typed, whatever the shape.
PUBLISHED_FIELDS: dict[str, tuple[str, str]] = {
    "name": ("", "text"),
    "tagline": ("tagline", "text"),
    "about": ("about", "text"),
    "services": ("services", "lines"),
    "email": ("emails", "lines"),
    "photos": ("photos", "lines"),
    "menu_items": ("menu_items", "dishes"),
    "socials": ("socials", "links"),
    "logo": ("logo", "text"),
}
VERIFIABLE = VERIFIABLE_FACTS + tuple(PUBLISHED_FIELDS)

FIELD_LABELS = {
    "address": "Address", "phone": "Phone", "hours": "Hours",
    "website": "Website", "name": "Business name", "tagline": "Tagline",
    "about": "Their story", "services": "What they sell",
    "email": "Email address", "photos": "Photographs",
    "menu_items": "Menu items", "socials": "Social profiles",
    "logo": "Logo",
}

_PRICE = re.compile(r"\$\s?\d[\d,.]*")


def _lines(text: str) -> list[str]:
    """One item per line. People also paste lists separated by · or ;."""
    parts = re.split(r"[\n;\u00b7|]+", text or "")
    return [p.strip(" -\u2014\u2013\t") for p in parts if p.strip(" -\u2014\u2013\t")]


def _dishes(text: str) -> list[dict]:
    """"Short Rib - $32 - braised overnight" back into what the page renders."""
    out: list[dict] = []
    for line in _lines(text):
        price = _PRICE.search(line)
        without = (line[:price.start()] + " " + line[price.end():]
                   if price else line)
        bits = [b.strip(" \u2014\u2013-\t") for b in
                re.split(r"\s+[\u2014\u2013-]\s+", without)]
        bits = [b for b in bits if b]
        if not bits:
            continue
        out.append({"name": bits[0], "price": price.group(0).strip() if price else "",
                    "description": " ".join(bits[1:])})
    return out


def _links(text: str) -> list[dict]:
    """"Facebook https://..." or a bare address; the platform is the host."""
    out: list[dict] = []
    for line in _lines(text):
        found = re.search(r"https?://\S+", line)
        if not found:
            continue
        url = found.group(0)
        said = line[:found.start()].strip(" -\u2014:\t")
        if not said:
            host = re.sub(r"^www\.", "", url.split("//", 1)[-1].split("/")[0])
            said = host.split(".")[0].title()
        out.append({"name": said, "url": url})
    return out


_SHAPES = {"text": lambda v: v.strip(), "lines": _lines,
           "dishes": _dishes, "links": _links}
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
        made = int(cur.lastrowid or 0)
        # A frozen brief carries its own vision. Without this the photographs
        # stage reads an empty table, decides nobody has looked, and re-runs
        # the whole pass — which is what made the census unreproducible and
        # expensive at the same time.
        photos.seed_from_brief(conn, made, brief_json)
        return made
    conn.execute(
        "UPDATE leads SET name=?, location=?, website_url=?, brief_json=?,"
        " updated_at=? WHERE id=?",
        (brief_json["name"], brief_json.get("location"),
         brief_json.get("website_url"), payload, now, row["id"]))
    photos.seed_from_brief(conn, int(row["id"]), brief_json)
    return int(row["id"])


def record(conn: sqlite3.Connection, lead_id: int, kind: str, *,
           field: str | None = None, old_value: str | None = None,
           new_value: str | None = None, note: str | None = None,
           actor: str | None = None) -> None:
    """Append one event to a lead's audit trail."""
    conn.execute(
        "INSERT INTO events (lead_id, at, actor, kind, field, old_value,"
        " new_value, note) VALUES (?,?,?,?,?,?,?,?)",
        (lead_id, _now(), actor or operator(), kind, field, old_value,
         new_value, note))


def master_version(conn: sqlite3.Connection, lead_id: int) -> int | None:
    """The version Shreyas last marked as a good site, or `None`."""
    row = conn.execute(
        "SELECT new_value FROM events WHERE lead_id = ? AND kind = 'master'"
        " ORDER BY id DESC LIMIT 1", (lead_id,)).fetchone()
    return int(row["new_value"]) if row else None


def mark_master(conn: sqlite3.Connection, lead_id: int, version: int,
                actor: str | None = None) -> int:
    """Mark a version as the last checkpoint judged good.

    An event rather than a column: the mark moves as the site improves, and
    where it was is part of the record of what was decided, like a status.
    """
    exists = conn.execute("SELECT 1 FROM sites WHERE lead_id = ? AND version = ?",
                          (lead_id, version)).fetchone()
    if not exists:
        raise ValueError(f"there is no version {version} to mark")
    previous = master_version(conn, lead_id)
    record(conn, lead_id, "master", field="version",
           old_value=None if previous is None else str(previous),
           new_value=str(version), actor=actor)
    from app.store import folders  # folders reads leads to fill; imported here to avoid a cycle

    folders.write_master(conn, lead_id, version)
    return version


def events(conn: sqlite3.Connection, lead_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM events WHERE lead_id = ? ORDER BY id DESC", (lead_id,))
    return [dict(r) for r in rows]


def set_status(conn: sqlite3.Connection, lead_id: int, status: str,
               note: str | None = None) -> None:
    """Move a lead to another stage of the pipeline, and record the move."""
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
           note: str | None = None, actor: str | None = None) -> dict:
    """Record what you were actually told, and what it replaced.

    Returns the kind of statement it turned out to be and the value it
    displaced, because what happens next depends on it: confirming what the
    sources already said changes no page, and a correction changes one.
    """
    if field not in VERIFIABLE:
        raise ValueError(f"cannot verify {field!r} — one of {', '.join(VERIFIABLE)}")
    if not value.strip():
        raise ValueError("a confirmed value cannot be blank")
    brief = load_brief(conn, lead_id)
    published = brief.get("published") or {}
    where = PUBLISHED_FIELDS.get(field)
    previous: str | None
    if where:
        key = where[0]
        previous = _as_text(brief.get("name") if not key else published.get(key))
    else:
        previous = next((f.get("value") for f in brief.get("facts", [])
                         if f.get("field") == field), None)
    # What the operator confirmed last time outranks what the sources said, so
    # that is what a new statement is compared against. Comparing against the
    # crawl instead reports a re-confirmation of your own correction as a fresh
    # correction — which, now that a correction rebuilds the page, is a
    # generation run bought for nothing.
    standing = _overrides(conn, lead_id).get(field)
    if standing:
        previous = standing["new_value"]
    # Confirming what the sources already said is not a correction, and the
    # trail should not imply the value changed when it did not.
    kind = "verified" if previous == value.strip() else "corrected"
    record(conn, lead_id, kind, field=field, old_value=previous,
           new_value=value.strip(), note=note, actor=actor)
    return {"kind": kind, "was": previous, "value": value.strip()}


def load_brief(conn: sqlite3.Connection, lead_id: int) -> dict:
    """The lead's brief as stored, before any correction is applied."""
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
    # What the table holds wins; what the brief already carried is the
    # fallback. A frozen fixture carries its own labels and vision, and loading
    # one into an empty database used to discard them — so the census re-ran
    # the whole vision pass, paid for it, and measured a system nobody could
    # reproduce without a key. The table is still the source of truth for a
    # real lead, because that is where a person's corrections live.
    said = photos.labels_for(conn, lead_id)
    brief["photo_labels"] = said or dict(brief.get("photo_labels") or {})
    seen = photos.vision_for(conn, lead_id)
    brief["photo_vision"] = seen or dict(brief.get("photo_vision") or {})
    # The words you wrote, kept for alt text on the finished page.
    written = {url: what["description"]
               for url, what in photos.described(conn, lead_id).items()
               if what["description"]}
    brief["photo_notes"] = written or dict(brief.get("photo_notes") or {})

    overrides = _overrides(conn, lead_id)
    applied = dict(overrides)          # `overrides` is emptied by pop() below
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
    # The same correction, applied where generation will actually read it.
    # A fact the page never looks up is a fact the page cannot be wrong about;
    # `published` is where the tagline, the story, the services and the rest
    # are read from, so an override that stops at `facts` changes nothing a
    # visitor would see.
    published = brief.setdefault("published", {})
    was = dict(brief.get("published_superseded") or {})
    for field, (where, shape) in PUBLISHED_FIELDS.items():
        event = applied.get(field)
        if event is None:
            continue
        value = _SHAPES[shape](event["new_value"] or "")
        if not value:
            continue
        target = brief if not where else published
        key = where or "name"
        if target.get(key) != value:
            was[field] = target.get(key)
        target[key] = value
    brief["published_superseded"] = was
    brief["confirmable"] = _confirmable(brief, applied)
    # A question you have answered is no longer a question.
    answered = {f["field"] for f in facts if f["confidence"] == "operator_verified"}
    brief["open_questions"] = [
        q for q in brief.get("open_questions", [])
        if not any(word in q.lower() for word in _QUESTION_WORDS(answered))]
    return brief


def _as_text(value: object) -> str:
    """A published value as the operator would type it back."""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        lines = []
        for item in value:
            if isinstance(item, dict) and "url" in item and "name" in item:
                lines.append(f"{item['name']} {item['url']}")
            elif isinstance(item, dict):
                bits = [str(item.get("name") or ""), str(item.get("price") or ""),
                        str(item.get("description") or "")]
                lines.append(" \u2014 ".join(b for b in bits if b))
            else:
                lines.append(str(item))
        return "\n".join(lines)
    return "" if value is None else str(value)


def _confirmable(brief: dict, applied: dict[str, dict]) -> list[dict]:
    """Everything outside `facts` that an operator can now confirm.

    These come off the business's own site with one source and no
    corroboration, so they carry no confidence score and never did: a page's
    whole story, everything it says the business sells, and who to write to
    were simply taken on trust. This is the list the screen offers.
    """
    published = brief.get("published") or {}
    rows: list[dict] = []
    for field, (where, _shape) in PUBLISHED_FIELDS.items():
        value = brief.get("name") if not where else published.get(where)
        event = applied.get(field)
        rows.append({
            "field": field,
            "label": FIELD_LABELS.get(field, field.title()),
            "value": _as_text(value),
            "count": len(value) if isinstance(value, list) else None,
            "confidence": "operator_verified" if event else (
                "unverified" if value else "missing"),
            "verified_by": event["actor"] if event else None,
            "verified_at": event["at"] if event else None,
            "verified_note": event["note"] if event else None,
            "superseded": _as_text((brief.get("published_superseded") or {}).get(field)),
        })
    return rows


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
