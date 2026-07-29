"""Unit tests for approvals (content binding + append-only)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import func, select

from app.core.approvals import create_approval, hash_content
from app.core.enums import Decision, SubjectType
from app.core.errors import AppendOnlyError
from app.models.approval import Approval
from app.models.audit import AuditEvent

pytestmark = pytest.mark.unit


def test_create_approval_binds_content_hash(session):
    content = {"headline": "Best pizza in Galena", "sections": ["menu", "hours"]}
    subject = uuid.uuid4()
    approval = create_approval(
        session,
        subject_type=SubjectType.SITE,
        subject_id=subject,
        decision=Decision.APPROVE,
        approver="shreyas",
        content=content,
    )
    assert approval.content_hash == hash_content(content)
    # order-independent hashing
    assert hash_content({"b": 2, "a": 1}) == hash_content({"a": 1, "b": 2})


def test_create_approval_emits_audit_event(session):
    subject = uuid.uuid4()
    create_approval(
        session,
        subject_type=SubjectType.EMAIL,
        subject_id=subject,
        decision=Decision.APPROVE,
        approver="shreyas",
        content={"body": "hello"},
    )
    events = session.execute(select(AuditEvent)).scalars().all()
    assert len(events) == 1
    assert events[0].action == "approval:approve:email"
    assert events[0].after["subject_id"] == str(subject)


def test_guard_approval_append_only_update_blocked(session):
    approval = create_approval(
        session,
        subject_type=SubjectType.SITE,
        subject_id=uuid.uuid4(),
        decision=Decision.APPROVE,
        approver="shreyas",
    )
    session.commit()
    approval.decision = Decision.REJECT
    with pytest.raises(AppendOnlyError):
        session.flush()


def test_guard_approval_append_only_delete_blocked(session):
    approval = create_approval(
        session,
        subject_type=SubjectType.SITE,
        subject_id=uuid.uuid4(),
        decision=Decision.APPROVE,
        approver="shreyas",
    )
    session.commit()
    session.delete(approval)
    with pytest.raises(AppendOnlyError):
        session.flush()


def test_approvals_persist_immutably(session):
    subject = uuid.uuid4()
    create_approval(
        session,
        subject_type=SubjectType.SITE,
        subject_id=subject,
        decision=Decision.APPROVE,
        approver="shreyas",
    )
    session.commit()
    count = session.execute(select(func.count()).select_from(Approval)).scalar_one()
    assert count == 1
