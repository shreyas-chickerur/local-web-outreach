"""The business lifecycle state machine.

``advance`` is the single sanctioned way to change ``Business.status``. It
refuses illegal transitions, enforces the two human approval gates, and writes
an audit event for every legal move. Nothing else should assign ``status``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.core.audit import record_event
from app.core.enums import Actor, BusinessStatus, Decision, SubjectType
from app.core.errors import ApprovalRequiredError, TransitionError

if TYPE_CHECKING:
    from app.models.approval import Approval
    from app.models.business import Business

S = BusinessStatus

# Legal transitions. Terminal states map to an empty set.
ALLOWED_TRANSITIONS: dict[BusinessStatus, set[BusinessStatus]] = {
    S.DISCOVERED: {S.QUALIFIED, S.DISQUALIFIED},
    S.QUALIFIED: {S.RESEARCHED, S.DISQUALIFIED},
    S.RESEARCHED: {S.SITE_DRAFTED, S.DISQUALIFIED},
    S.SITE_DRAFTED: {S.SITE_APPROVED, S.DISQUALIFIED},
    S.SITE_APPROVED: {S.EMAIL_DRAFTED, S.DISQUALIFIED},
    S.EMAIL_DRAFTED: {S.EMAIL_APPROVED, S.DISQUALIFIED},
    S.EMAIL_APPROVED: {S.SENT},
    S.SENT: {S.REPLIED, S.LOST, S.SUPPRESSED},
    S.REPLIED: {S.NEGOTIATING, S.LOST, S.SUPPRESSED},
    S.NEGOTIATING: {S.WON, S.LOST, S.SUPPRESSED},
    S.WON: set(),
    S.LOST: set(),
    S.SUPPRESSED: set(),
    S.DISQUALIFIED: set(),
}

# Transitions that require a matching, approved sign-off before they may fire.
GATED_TRANSITIONS: dict[tuple[BusinessStatus, BusinessStatus], SubjectType] = {
    (S.SITE_DRAFTED, S.SITE_APPROVED): SubjectType.SITE,
    (S.EMAIL_DRAFTED, S.EMAIL_APPROVED): SubjectType.EMAIL,
}

TERMINAL_STATES: frozenset[BusinessStatus] = frozenset(
    s for s, nxt in ALLOWED_TRANSITIONS.items() if not nxt
)


def can_transition(src: BusinessStatus, dst: BusinessStatus) -> bool:
    """True if ``src -> dst`` is a declared legal transition."""
    return dst in ALLOWED_TRANSITIONS.get(src, set())


def _check_gate(
    business: Business, to_status: BusinessStatus, approval: Approval | None
) -> None:
    required = GATED_TRANSITIONS.get((business.status, to_status))
    if required is None:
        return
    if approval is None:
        raise ApprovalRequiredError(
            f"transition {business.status.value} -> {to_status.value} requires a "
            f"{required.value} approval"
        )
    if approval.decision != Decision.APPROVE:
        raise ApprovalRequiredError(
            f"approval {approval.id} has decision {approval.decision.value}, "
            f"not 'approve'"
        )
    if approval.subject_type != required:
        raise ApprovalRequiredError(
            f"approval subject_type {approval.subject_type.value} does not match "
            f"required {required.value}"
        )
    if approval.subject_id != business.id:
        raise ApprovalRequiredError(
            f"approval {approval.id} is for subject {approval.subject_id}, "
            f"not business {business.id}"
        )


def advance(
    session: Session,
    business: Business,
    to_status: BusinessStatus,
    *,
    actor: str = Actor.WORKER.value,
    approval: Approval | None = None,
    reason: str | None = None,
) -> Business:
    """Move ``business`` to ``to_status``, enforcing legality + gates + audit."""
    src = business.status
    if not can_transition(src, to_status):
        raise TransitionError(f"illegal transition: {src.value} -> {to_status.value}")

    _check_gate(business, to_status, approval)

    business.status = to_status
    after: dict = {"status": to_status.value}
    if reason:
        after["reason"] = reason

    record_event(
        session,
        actor=actor,
        action=f"advance:{src.value}->{to_status.value}",
        subject_type="business",
        subject_id=business.id,
        before={"status": src.value},
        after=after,
        approval_id=approval.id if approval is not None else None,
    )
    session.flush()
    return business
