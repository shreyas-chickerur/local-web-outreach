"""End-to-end spine flow: walk a business from DISCOVERED to WON and prove the
audit chain reconstructs the entire history and verifies."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.core.approvals import create_approval
from app.core.audit import verify_chain
from app.core.enums import BusinessStatus as S
from app.core.enums import Decision, SubjectType
from app.core.state_machine import advance
from app.models.audit import AuditEvent
from app.models.business import Business


def _run_full_lifecycle(session) -> Business:
    biz = Business(name="Vinny's Trattoria", location="Galena, IL", category="restaurant")
    session.add(biz)
    session.flush()

    advance(session, biz, S.QUALIFIED)
    advance(session, biz, S.RESEARCHED)
    advance(session, biz, S.SITE_DRAFTED)

    site_ok = create_approval(
        session,
        subject_type=SubjectType.SITE,
        subject_id=biz.id,
        decision=Decision.APPROVE,
        approver="shreyas",
        content={"headline": "Family Italian since 1994"},
    )
    advance(session, biz, S.SITE_APPROVED, actor="human", approval=site_ok)
    advance(session, biz, S.EMAIL_DRAFTED)

    email_ok = create_approval(
        session,
        subject_type=SubjectType.EMAIL,
        subject_id=biz.id,
        decision=Decision.APPROVE,
        approver="shreyas",
        content={"subject": "A modern site for Vinny's"},
    )
    advance(session, biz, S.EMAIL_APPROVED, actor="human", approval=email_ok)
    advance(session, biz, S.SENT)
    advance(session, biz, S.REPLIED)
    advance(session, biz, S.NEGOTIATING)
    advance(session, biz, S.WON)

    session.commit()
    return biz


def _assert_history_is_complete_and_verifiable(session, biz) -> None:
    assert biz.status is S.WON

    ok, bad = verify_chain(session)
    assert ok is True, f"audit chain broke at seq {bad}"

    events = session.execute(select(AuditEvent).order_by(AuditEvent.seq)).scalars().all()
    # 10 transitions + 2 approval events = 12 audited actions.
    assert len(events) == 12

    transitions = [e.after["status"] for e in events if e.action.startswith("advance:")]
    assert transitions == [
        "QUALIFIED", "RESEARCHED", "SITE_DRAFTED", "SITE_APPROVED", "EMAIL_DRAFTED",
        "EMAIL_APPROVED", "SENT", "REPLIED", "NEGOTIATING", "WON",
    ]
    # both gated transitions carry the approval id that authorized them
    gated = [e for e in events if e.action in ("advance:SITE_DRAFTED->SITE_APPROVED",
                                               "advance:EMAIL_DRAFTED->EMAIL_APPROVED")]
    assert all(e.approval_id is not None for e in gated)


@pytest.mark.functional
def test_full_lifecycle_sqlite(session):
    biz = _run_full_lifecycle(session)
    _assert_history_is_complete_and_verifiable(session, biz)


@pytest.mark.functional
@pytest.mark.postgres
def test_full_lifecycle_postgres(pg_session):
    biz = _run_full_lifecycle(pg_session)
    _assert_history_is_complete_and_verifiable(pg_session, biz)
