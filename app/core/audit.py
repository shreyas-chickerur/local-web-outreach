"""Append-only, hash-chained audit ledger.

``record_event`` is the only sanctioned way to write to ``audit_events``. It
assigns ``seq`` and computes the chain ``hash`` under a per-chain lock so the
ledger stays linear and verifiable even with concurrent writers. On PostgreSQL
the lock is a transaction-scoped advisory lock; on SQLite writes are already
serialized by the database file lock, so the lock is a no-op.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.audit import AuditEvent

GENESIS_PREV = "0" * 64
_CHAIN_LOCK_KEY = 918_273_645  # arbitrary constant for pg_advisory_xact_lock


def _canonical(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()


def _payload(
    *,
    seq: int,
    ts: str,
    actor: str,
    action: str,
    subject_type: str,
    subject_id: uuid.UUID | None,
    before: dict | None,
    after: dict | None,
    approval_id: uuid.UUID | None,
    prev_hash: str,
) -> dict[str, Any]:
    """The exact, ordered set of fields that are hashed. Write and verify paths
    both go through here so they can never drift."""
    return {
        "seq": seq,
        "ts": ts,
        "actor": actor,
        "action": action,
        "subject_type": subject_type,
        "subject_id": str(subject_id) if subject_id is not None else None,
        "before": before,
        "after": after,
        "approval_id": str(approval_id) if approval_id is not None else None,
        "prev_hash": prev_hash,
    }


def _lock_chain(session: Session) -> None:
    if session.get_bind().dialect.name == "postgresql":
        session.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": _CHAIN_LOCK_KEY})


def record_event(
    session: Session,
    *,
    actor: str,
    action: str,
    subject_type: str,
    subject_id: uuid.UUID | None = None,
    before: dict | None = None,
    after: dict | None = None,
    approval_id: uuid.UUID | None = None,
) -> AuditEvent:
    """Append one event to the ledger and return it (flushed, not committed)."""
    _lock_chain(session)
    tip = session.execute(
        select(AuditEvent).order_by(AuditEvent.seq.desc()).limit(1)
    ).scalar_one_or_none()

    seq = 1 if tip is None else tip.seq + 1
    prev_hash = GENESIS_PREV if tip is None else tip.hash
    ts = datetime.now(UTC).isoformat()

    payload = _payload(
        seq=seq,
        ts=ts,
        actor=str(actor),
        action=action,
        subject_type=subject_type,
        subject_id=subject_id,
        before=before,
        after=after,
        approval_id=approval_id,
        prev_hash=prev_hash,
    )
    event = AuditEvent(
        seq=seq,
        ts=ts,
        actor=str(actor),
        action=action,
        subject_type=subject_type,
        subject_id=subject_id,
        before=before,
        after=after,
        approval_id=approval_id,
        prev_hash=prev_hash,
        hash=_hash(payload),
    )
    session.add(event)
    session.flush()
    return event


def verify_chain(session: Session) -> tuple[bool, int | None]:
    """Recompute the whole chain. Returns ``(ok, first_bad_seq)``.

    ``ok`` is False if any row's stored hash does not match a recomputation, or
    if the ``prev_hash`` linkage is broken. ``first_bad_seq`` is the seq of the
    first offending row (or ``None`` when the chain is intact).
    """
    prev = GENESIS_PREV
    for event in session.execute(select(AuditEvent).order_by(AuditEvent.seq.asc())).scalars():
        if event.prev_hash != prev:
            return False, event.seq
        recomputed = _hash(
            _payload(
                seq=event.seq,
                ts=event.ts,
                actor=event.actor,
                action=event.action,
                subject_type=event.subject_type,
                subject_id=event.subject_id,
                before=event.before,
                after=event.after,
                approval_id=event.approval_id,
                prev_hash=event.prev_hash,
            )
        )
        if recomputed != event.hash:
            return False, event.seq
        prev = event.hash
    return True, None


def latest_transition_reason(session: Session, subject_id: uuid.UUID) -> str:
    """The reason recorded on the most recent state transition for a subject —
    the plain-English 'why' the console shows — or '—' if there is none yet."""
    event = session.execute(
        select(AuditEvent)
        .where(AuditEvent.subject_id == subject_id, AuditEvent.action.like("advance:%"))
        .order_by(AuditEvent.seq.desc())
        .limit(1)
    ).scalar_one_or_none()
    return (event.after or {}).get("reason", "—") if event else "—"
