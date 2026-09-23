"""The approval stage: what was checked, what a person said about it, and when.

A review belongs to one version of one site. It is opened when somebody is
finished iterating and wants to ship; it holds every finding the checks
produced, and every finding holds whatever the person decided about it.

Two rules give the record its value:

* Nothing here is ever rewritten to make a later story tidier. A decision is
  stamped with a time and an actor and stays. Changing your mind writes a new
  decision over the top of the old one in the same row — and also an event,
  which is append-only, so the sequence survives.
* A review is bound to a version. A correction produces a NEW version, which
  opens a NEW review. That is the whole point: you cannot approve version 7,
  edit the page, and still be holding an approval. The approval names what it
  approved.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime

from app.store import db as _db

# A review cannot be approved while one of these is unresolved. Exactly one
# verdict is hard, for the reason the checks module gives: it is the only one
# a machine is entitled to be certain about.
BLOCKING = ("contradicted",)

OPEN, APPROVED, SENT_BACK = "open", "approved", "sent back"
UNRESOLVED = "open"


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def open_review(conn: sqlite3.Connection, lead_id: int, version: int,
                findings: list[dict], *, actor: str | None = None,
                brief_hash: str = "", capture_hash: str = "") -> dict:
    """Start (or return) the review of one version. Findings are written once.

    Re-opening an existing review does NOT re-run or replace its findings:
    somebody's notes live on those rows, and silently regenerating them would
    erase the work while looking like a refresh.
    """
    existing = conn.execute(
        "SELECT id FROM reviews WHERE lead_id=? AND version=?",
        (lead_id, version)).fetchone()
    if existing:
        return review(conn, int(existing["id"]))

    who = actor or _db.operator()
    cursor = conn.execute(
        "INSERT INTO reviews(lead_id, version, opened_at, opened_by, stage,"
        " brief_hash, capture_hash) VALUES(?,?,?,?,?,?,?)",
        (lead_id, version, _now(), who, OPEN, brief_hash, capture_hash))
    review_id = int(cursor.lastrowid or 0)
    for row in findings:
        conn.execute(
            "INSERT INTO findings(review_id, stage, verdict, title, detail,"
            " locator, anchor, quote, evidence, resources)"
            " VALUES(?,?,?,?,?,?,?,?,?,?)",
            (review_id, row.get("stage", "claim"), row.get("verdict", "unsourced"),
             row.get("title", ""), row.get("detail", ""), row.get("locator", ""),
             row.get("anchor", "page"), row.get("quote", ""),
             row.get("evidence", ""), row.get("resources", "[]")))
    conn.execute(
        "INSERT INTO events(lead_id, at, actor, kind, field, new_value, note)"
        " VALUES(?,?,?,?,?,?,?)",
        (lead_id, _now(), who, "review", f"v{version}", "opened",
         f"{len(findings)} finding(s)"))
    conn.commit()
    return review(conn, review_id)


def review(conn: sqlite3.Connection, review_id: int) -> dict:
    """One review with its findings, in the order a person should read them."""
    row = conn.execute("SELECT * FROM reviews WHERE id=?", (review_id,)).fetchone()
    if row is None:
        raise ValueError(f"no review {review_id}")
    out = dict(row)
    out["findings"] = [_finding(r) for r in conn.execute(
        "SELECT * FROM findings WHERE review_id=? ORDER BY"
        " CASE verdict WHEN 'contradicted' THEN 0 WHEN 'defect' THEN 1"
        "   WHEN 'unsourced' THEN 2 WHEN 'assembled' THEN 3"
        "   WHEN 'wording' THEN 4 WHEN 'unmeasured' THEN 5 ELSE 6 END, id",
        (review_id,))]
    out["blocking"] = [f for f in out["findings"]
                       if f["verdict"] in BLOCKING and f["status"] == UNRESOLVED]
    out["open_count"] = sum(1 for f in out["findings"]
                            if f["status"] == UNRESOLVED and f["verdict"] != "corroborated")
    return out


def for_version(conn: sqlite3.Connection, lead_id: int, version: int) -> dict | None:
    row = conn.execute("SELECT id FROM reviews WHERE lead_id=? AND version=?",
                       (lead_id, version)).fetchone()
    return review(conn, int(row["id"])) if row else None


def history(conn: sqlite3.Connection, lead_id: int) -> list[dict]:
    """Every review a lead has had, newest version first."""
    return [dict(r) for r in conn.execute(
        "SELECT id, version, stage, opened_at, decided_at, decided_by,"
        " decision_note FROM reviews WHERE lead_id=? ORDER BY version DESC",
        (lead_id,))]


def _finding(row: sqlite3.Row) -> dict:
    out = dict(row)
    try:
        out["resources"] = json.loads(out.get("resources") or "[]")
    except (TypeError, ValueError):
        out["resources"] = []
    return out


def mark(conn: sqlite3.Connection, finding_id: int, status: str,
         note: str = "", *, actor: str | None = None) -> dict:
    """Record what a person decided about one finding.

    `status` is theirs, not the machine's: confirmed (it is right as it
    stands), corrected (it is wrong and the page needs changing), or
    dismissed (not worth acting on). The note is why, and the note is the
    part that will matter in six weeks.
    """
    if status not in ("open", "confirmed", "corrected", "dismissed"):
        raise ValueError(f"unknown status {status!r}")
    row = conn.execute("SELECT * FROM findings WHERE id=?", (finding_id,)).fetchone()
    if row is None:
        raise ValueError(f"no finding {finding_id}")
    who = actor or _db.operator()
    conn.execute(
        "UPDATE findings SET status=?, note=?, decided_at=?, decided_by=? WHERE id=?",
        (status, note, _now(), who, finding_id))
    parent = conn.execute("SELECT lead_id, version FROM reviews WHERE id=?",
                          (row["review_id"],)).fetchone()
    conn.execute(
        "INSERT INTO events(lead_id, at, actor, kind, field, old_value, new_value, note)"
        " VALUES(?,?,?,?,?,?,?,?)",
        (parent["lead_id"], _now(), who, "finding",
         f"v{parent['version']} #{finding_id}", row["status"], status,
         note or row["title"]))
    conn.commit()
    return _finding(conn.execute("SELECT * FROM findings WHERE id=?",
                                 (finding_id,)).fetchone())


def decide(conn: sqlite3.Connection, review_id: int, decision: str,
           note: str = "", *, actor: str | None = None) -> dict:
    """Approve the version, or send it back.

    Approval refuses while a contradicted finding is still open. Every other
    verdict is advice — the person may ship over it, and the note says they
    chose to.
    """
    if decision not in (APPROVED, SENT_BACK):
        raise ValueError(f"unknown decision {decision!r}")
    current = review(conn, review_id)
    if decision == APPROVED and current["blocking"]:
        titles = ", ".join(f["title"] for f in current["blocking"][:3])
        raise ValueError(
            "cannot approve while a contradicted finding is unresolved: " + titles)
    who = actor or _db.operator()
    conn.execute(
        "UPDATE reviews SET stage=?, decided_at=?, decided_by=?, decision_note=?"
        " WHERE id=?", (decision, _now(), who, note, review_id))
    conn.execute(
        "INSERT INTO events(lead_id, at, actor, kind, field, new_value, note)"
        " VALUES(?,?,?,?,?,?,?)",
        (current["lead_id"], _now(), who, "review", f"v{current['version']}",
         decision, note))
    conn.commit()
    return review(conn, review_id)

def refresh(conn: sqlite3.Connection, review_id: int, findings: list[dict],
            *, actor: str | None = None) -> dict:
    """Re-run the checks over a version whose review is already open.

    `open_review` never regenerates, because findings carry notes and a silent
    regeneration is a deletion wearing a refresh's clothes. But a review opened
    before the checks improved is stuck with the worse ones, and the only way
    out was to throw the review away.

    So this regenerates deliberately, and protects the part worth protecting:
    anything somebody has already decided stays exactly as it is, and a new
    finding that repeats one of those titles is dropped rather than resurrecting
    a question that has been answered. Undecided findings are replaced.
    """
    settled = {row["title"] for row in conn.execute(
        "SELECT title FROM findings WHERE review_id=? AND status<>?",
        (review_id, UNRESOLVED))}
    conn.execute("DELETE FROM findings WHERE review_id=? AND status=?",
                 (review_id, UNRESOLVED))
    added = 0
    for row in findings:
        if row.get("title", "") in settled:
            continue
        conn.execute(
            "INSERT INTO findings(review_id, stage, verdict, title, detail,"
            " locator, anchor, quote, evidence, resources)"
            " VALUES(?,?,?,?,?,?,?,?,?,?)",
            (review_id, row.get("stage", "claim"), row.get("verdict", "unsourced"),
             row.get("title", ""), row.get("detail", ""), row.get("locator", ""),
             row.get("anchor", "page"), row.get("quote", ""),
             row.get("evidence", ""), row.get("resources", "[]")))
        added += 1
    current = review(conn, review_id)
    who = actor or _db.operator()
    conn.execute(
        "INSERT INTO events(lead_id, at, actor, kind, field, new_value, note)"
        " VALUES(?,?,?,?,?,?,?)",
        (current["lead_id"], _now(), who, "review", f"v{current['version']}",
         "checks re-run",
         f"{added} finding(s) rewritten, {len(settled)} decision(s) kept"))
    conn.commit()
    return review(conn, review_id)
