"""Unit tests for the hash-chained audit ledger."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select, text

from app.core.audit import (
    GENESIS_PREV,
    latest_transition_reason,
    record_event,
    verify_chain,
)
from app.core.errors import AppendOnlyError
from app.models.audit import AuditEvent

pytestmark = pytest.mark.unit


def _write(session, n: int) -> None:
    for i in range(n):
        record_event(
            session,
            actor="worker",
            action=f"test:{i}",
            subject_type="business",
            subject_id=uuid.uuid4(),
            after={"i": i},
        )


def test_first_event_uses_genesis_prev_hash(session):
    event = record_event(session, actor="system", action="init", subject_type="business")
    assert event.seq == 1
    assert event.prev_hash == GENESIS_PREV
    assert len(event.hash) == 64


def test_seq_increments_and_chain_links(session):
    _write(session, 5)
    events = session.execute(select(AuditEvent).order_by(AuditEvent.seq)).scalars().all()
    assert [e.seq for e in events] == [1, 2, 3, 4, 5]
    # each row's prev_hash equals the previous row's hash
    for prev, cur in zip(events, events[1:], strict=False):
        assert cur.prev_hash == prev.hash


def test_verify_chain_ok_on_valid_ledger(session):
    _write(session, 10)
    ok, bad = verify_chain(session)
    assert ok is True
    assert bad is None


def test_verify_chain_detects_out_of_band_tamper(session):
    _write(session, 6)
    # Tamper via raw SQL (Core execute bypasses the ORM append-only guard, which
    # is exactly how an attacker or a bug outside the sanctioned path would look).
    session.execute(
        text("UPDATE audit_events SET after = :a WHERE seq = 3"),
        {"a": '{"i": 999}'},
    )
    session.commit()
    session.expire_all()

    ok, bad = verify_chain(session)
    assert ok is False
    assert bad == 3


def test_guard_audit_append_only_update_blocked(session):
    event = record_event(session, actor="worker", action="x", subject_type="business")
    session.commit()
    event.action = "tampered"
    with pytest.raises(AppendOnlyError):
        session.flush()


def test_guard_audit_append_only_delete_blocked(session):
    event = record_event(session, actor="worker", action="x", subject_type="business")
    session.commit()
    session.delete(event)
    with pytest.raises(AppendOnlyError):
        session.flush()


def test_latest_transition_reason(session):
    subject = uuid.uuid4()
    # no transitions yet
    assert latest_transition_reason(session, subject) == "—"
    # a non-advance event does not count
    record_event(session, actor="system", action="discover:created",
                 subject_type="business", subject_id=subject, after={"x": 1})
    assert latest_transition_reason(session, subject) == "—"
    # the most recent advance's reason wins
    record_event(session, actor="human", action="advance:A->B", subject_type="business",
                 subject_id=subject, after={"status": "B", "reason": "first"})
    record_event(session, actor="human", action="advance:B->C", subject_type="business",
                 subject_id=subject, after={"status": "C", "reason": "latest"})
    assert latest_transition_reason(session, subject) == "latest"
