"""Unit tests for the two human approval gates (invariant #2)."""

from __future__ import annotations

import pytest
from sqlalchemy import func, select

from app.core.approvals import create_approval
from app.core.enums import BusinessStatus as S
from app.core.enums import Decision, SubjectType
from app.core.errors import ApprovalRequiredError
from app.core.state_machine import advance
from app.models.audit import AuditEvent
from app.models.business import Business

pytestmark = pytest.mark.unit


def _business_at(session, status) -> Business:
    biz = Business(name="Acme", location="Galena, IL", status=status)
    session.add(biz)
    session.flush()
    return biz


def _audit_count(session) -> int:
    return session.execute(select(func.count()).select_from(AuditEvent)).scalar_one()


def test_guard_no_advance_to_site_approved_without_approval(session):
    biz = _business_at(session, S.SITE_DRAFTED)
    before = _audit_count(session)
    with pytest.raises(ApprovalRequiredError):
        advance(session, biz, S.SITE_APPROVED)
    assert biz.status is S.SITE_DRAFTED
    assert _audit_count(session) == before  # nothing recorded for the blocked move


def test_advance_with_valid_site_approval_succeeds(session):
    biz = _business_at(session, S.SITE_DRAFTED)
    approval = create_approval(
        session,
        subject_type=SubjectType.SITE,
        subject_id=biz.id,
        decision=Decision.APPROVE,
        approver="shreyas",
        content={"headline": "hi"},
    )
    advance(session, biz, S.SITE_APPROVED, actor="human", approval=approval)
    assert biz.status is S.SITE_APPROVED


def test_guard_reject_decision_does_not_authorize(session):
    biz = _business_at(session, S.SITE_DRAFTED)
    approval = create_approval(
        session,
        subject_type=SubjectType.SITE,
        subject_id=biz.id,
        decision=Decision.REJECT,
        approver="shreyas",
    )
    with pytest.raises(ApprovalRequiredError):
        advance(session, biz, S.SITE_APPROVED, approval=approval)
    assert biz.status is S.SITE_DRAFTED


def test_guard_wrong_subject_type_rejected(session):
    biz = _business_at(session, S.SITE_DRAFTED)
    email_approval = create_approval(
        session,
        subject_type=SubjectType.EMAIL,  # wrong kind for the site gate
        subject_id=biz.id,
        decision=Decision.APPROVE,
        approver="shreyas",
    )
    with pytest.raises(ApprovalRequiredError):
        advance(session, biz, S.SITE_APPROVED, approval=email_approval)


def test_guard_approval_for_other_business_rejected(session):
    biz = _business_at(session, S.SITE_DRAFTED)
    other = _business_at(session, S.SITE_DRAFTED)
    stolen = create_approval(
        session,
        subject_type=SubjectType.SITE,
        subject_id=other.id,  # approval belongs to a different business
        decision=Decision.APPROVE,
        approver="shreyas",
    )
    with pytest.raises(ApprovalRequiredError):
        advance(session, biz, S.SITE_APPROVED, approval=stolen)


def test_email_gate_requires_email_approval(session):
    biz = _business_at(session, S.EMAIL_DRAFTED)
    with pytest.raises(ApprovalRequiredError):
        advance(session, biz, S.EMAIL_APPROVED)

    approval = create_approval(
        session,
        subject_type=SubjectType.EMAIL,
        subject_id=biz.id,
        decision=Decision.APPROVE,
        approver="shreyas",
        content={"subject": "A quick idea for Acme"},
    )
    advance(session, biz, S.EMAIL_APPROVED, actor="human", approval=approval)
    assert biz.status is S.EMAIL_APPROVED
