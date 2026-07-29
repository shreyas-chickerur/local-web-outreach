"""Creating operator approvals (and auditing that they happened)."""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.core.audit import record_event
from app.core.enums import Actor, Decision, SubjectType
from app.models.approval import Approval


def hash_content(content: Any) -> str:
    """Stable hash of the exact reviewed content, bound onto the approval."""
    canonical = json.dumps(content, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def create_approval(
    session: Session,
    *,
    subject_type: SubjectType,
    subject_id: uuid.UUID,
    decision: Decision,
    approver: str,
    content: Any | None = None,
    notes: str | None = None,
) -> Approval:
    """Record an immutable approval and emit an audit event for it."""
    approval = Approval(
        subject_type=subject_type,
        subject_id=subject_id,
        decision=decision,
        approver=approver,
        content_hash=hash_content(content) if content is not None else None,
        notes=notes,
    )
    session.add(approval)
    session.flush()

    record_event(
        session,
        actor=Actor.HUMAN.value,
        action=f"approval:{decision.value}:{subject_type.value}",
        subject_type="approval",
        subject_id=approval.id,
        after={
            "decision": decision.value,
            "subject_type": subject_type.value,
            "subject_id": str(subject_id),
            "content_hash": approval.content_hash,
            "approver": approver,
        },
    )
    return approval
