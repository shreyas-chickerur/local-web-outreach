"""Unit tests for the business state machine."""

from __future__ import annotations

import pytest
from sqlalchemy import func, select

from app.core.enums import BusinessStatus as S
from app.core.errors import TransitionError
from app.core.state_machine import (
    ALLOWED_TRANSITIONS,
    TERMINAL_STATES,
    advance,
    can_transition,
)
from app.models.audit import AuditEvent
from app.models.business import Business

pytestmark = pytest.mark.unit


def _make_business(session, status=S.DISCOVERED) -> Business:
    biz = Business(name="Acme", location="Galena, IL", status=status)
    session.add(biz)
    session.flush()
    return biz


def _audit_count(session) -> int:
    return session.execute(select(func.count()).select_from(AuditEvent)).scalar_one()


def test_can_transition_matrix():
    assert can_transition(S.DISCOVERED, S.QUALIFIED)
    assert can_transition(S.NEGOTIATING, S.WON)
    assert not can_transition(S.DISCOVERED, S.SENT)
    assert not can_transition(S.WON, S.LOST)


def test_advance_happy_path_writes_audit(session):
    biz = _make_business(session)
    advance(session, biz, S.QUALIFIED)
    assert biz.status is S.QUALIFIED
    assert _audit_count(session) == 1

    event = session.execute(select(AuditEvent)).scalars().one()
    assert event.action == "advance:DISCOVERED->QUALIFIED"
    assert event.before == {"status": "DISCOVERED"}
    assert event.after == {"status": "QUALIFIED"}
    assert event.subject_id == biz.id


def test_guard_illegal_transition_raises_and_is_inert(session):
    biz = _make_business(session)
    with pytest.raises(TransitionError):
        advance(session, biz, S.SENT)
    # status unchanged, and no audit event was written for the failed attempt.
    assert biz.status is S.DISCOVERED
    assert _audit_count(session) == 0


def test_terminal_states_have_no_exits():
    assert TERMINAL_STATES == {S.WON, S.LOST, S.SUPPRESSED, S.DISQUALIFIED}
    for state in TERMINAL_STATES:
        assert ALLOWED_TRANSITIONS[state] == set()


def test_disqualify_available_from_early_states(session):
    biz = _make_business(session, status=S.QUALIFIED)
    advance(session, biz, S.DISQUALIFIED)
    assert biz.status is S.DISQUALIFIED


def test_transition_table_is_total():
    # Every declared status must have an entry (even if empty) so lookups never
    # silently fall through to an implicit "no transitions".
    for status in S:
        assert status in ALLOWED_TRANSITIONS
