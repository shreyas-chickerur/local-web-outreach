"""Stage 7: SEND.

The only place in the system that causes something irreversible to happen
outside it. Every guard is therefore checked *here*, immediately before
delivery, rather than trusted from an earlier stage — state can go stale between
approval and send, and the expensive failure is sending something that was true
last week.

Order matters. Cheap, absolute refusals first; the actual delivery last.

    1. mode              — dry_run delivers nothing; self_test only to an allow-list
    2. sender address    — a placeholder postal address is a CAN-SPAM violation
    3. business state    — must be EMAIL_APPROVED, nothing else
    4. approval binding  — the email must still hash to what was approved
    5. suppression       — re-checked at send, not trusted from compose time
    6. geo               — re-checked at send
    7. identity          — not paused, past warmup, under today's cap
    8. deliver
    9. record            — audit event, status transition, counters

A failure at any step raises before the sender is touched.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.adapters.email_send import Sender, SendResult
from app.core import config
from app.core.approvals import hash_content
from app.core.audit import record_event
from app.core.clock import as_aware, utcnow
from app.core.compliance import (
    assert_real_sender_address,
    is_placeholder_address,
    is_suppressed,
)
from app.core.enums import Actor, BusinessStatus, Decision, EmailStatus, SubjectType
from app.core.errors import ComplianceError, NotFoundError, SuppressionError, TransitionError
from app.core.state_machine import advance
from app.models.approval import Approval
from app.models.business import Business
from app.models.email import Email
from app.models.sender_identity import SenderIdentity

# Deliverability thresholds. Past either, the identity stops sending — no human
# in the loop, because by the time a person notices the domain is already burnt.
MAX_BOUNCE_RATE = 0.02
MAX_COMPLAINT_RATE = 0.003
# Rates are meaningless on tiny samples; below this, only absolute failures pause.
MIN_SAMPLE_FOR_RATES = 20


class SendBlocked(Exception):
    """A guard refused this send. Never a bug — it is the system working."""


@dataclass
class SendOutcome:
    business_id: uuid.UUID
    recipient: str
    ok: bool
    reason: str
    message_id: str = ""


def _sent_today(session: Session, identity: SenderIdentity) -> int:
    since = utcnow() - timedelta(days=1)
    return int(session.execute(
        select(func.count()).select_from(Email).where(
            Email.inbox_used == identity.address,
            Email.status == EmailStatus.SENT,
            Email.sent_at >= since,
        )
    ).scalar_one())


def eligible_identity(session: Session, identities: list[SenderIdentity]) -> SenderIdentity:
    """Pick a mailbox that may send right now, spreading load across them.

    Raises rather than falling back to a paused or unwarmed identity — a send is
    always postponable, a burnt domain is not.
    """
    if not identities:
        raise SendBlocked("no sending identity configured")

    warmup_needed = config.warmup_days_required()
    now = utcnow()
    candidates: list[tuple[int, SenderIdentity]] = []
    reasons: list[str] = []

    for identity in identities:
        if identity.paused:
            reasons.append(f"{identity.address}: paused ({identity.paused_reason})")
            continue
        if warmup_needed:
            started = as_aware(identity.warmup_started_at)
            if started is None:
                reasons.append(f"{identity.address}: warmup never started")
                continue
            age_days = (now - started).days
            if age_days < warmup_needed:
                reasons.append(
                    f"{identity.address}: only {age_days}d into a {warmup_needed}d warmup")
                continue
        used = _sent_today(session, identity)
        if used >= identity.daily_cap:
            reasons.append(f"{identity.address}: daily cap {identity.daily_cap} reached")
            continue
        candidates.append((used, identity))

    if not candidates:
        raise SendBlocked("no identity may send right now — " + "; ".join(reasons))
    # Least-used first: rotation, not round-robin, so a restart cannot bunch sends.
    candidates.sort(key=lambda pair: pair[0])
    return candidates[0][1]


def _assert_mode_allows(recipient: str) -> str:
    mode = config.send_mode()
    if mode == "self_test":
        allow = config.send_allowlist()
        if not allow:
            raise SendBlocked("self_test mode with an empty SEND_ALLOWLIST")
        if recipient.strip().lower() not in allow:
            raise SendBlocked(
                f"self_test mode: {recipient} is not on SEND_ALLOWLIST")
    return mode


def _assert_still_approved(session: Session, business: Business, email: Email) -> None:
    """The email must still be byte-identical to what was approved at Gate 2."""
    approval = session.execute(
        select(Approval).where(
            Approval.subject_type == SubjectType.EMAIL,
            Approval.subject_id == business.id,
            Approval.decision == Decision.APPROVE,
        ).order_by(Approval.decided_at.desc()).limit(1)
    ).scalars().first()
    if approval is None:
        raise SendBlocked("no email approval on record")
    current = hash_content(
        {"subject": email.subject, "body": email.body, "recipient": email.recipient}
    )
    if approval.content_hash != current:
        raise SendBlocked(
            "the email changed after it was approved — re-approve before sending")


def send_one(
    session: Session,
    business: Business,
    sender: Sender,
    identities: list[SenderIdentity],
    redirect_to: str | None = None,
) -> SendOutcome:
    """Run every guard, then deliver one approved outreach email.

    ``redirect_to`` re-addresses the message to the operator instead of the
    business — the standard way to test a mail path end to end without
    contacting anyone. It is permitted ONLY outside live mode, the real intended
    recipient is recorded in the audit event, and the suppression and geo checks
    still run against the ORIGINAL recipient so a redirect can never be used to
    smuggle past them.
    """
    email = session.execute(
        select(Email).where(
            Email.business_id == business.id, Email.status == EmailStatus.APPROVED
        ).order_by(Email.created_at.desc()).limit(1)
    ).scalars().first()
    if email is None:
        raise NotFoundError(f"no approved email for business {business.id}")

    if redirect_to and config.send_mode() == "live":
        raise SendBlocked("redirect is not permitted in live mode")
    delivery_address = redirect_to or email.recipient
    mode = _assert_mode_allows(delivery_address)

    # CAN-SPAM's postal-address requirement protects RECIPIENTS. A self-test
    # redirected to an allow-listed address of your own cannot reach anyone else,
    # so the requirement has nothing to bite on and the check is waived — but
    # ONLY under both conditions together, and never in live mode. Every other
    # path checks the configured address AND the address baked into this email,
    # because the two differ whenever the email was composed before a real
    # address was set, and it is the composed bytes that reach the recipient.
    self_test_to_self = mode == "self_test" and redirect_to is not None
    if not self_test_to_self:
        try:
            assert_real_sender_address(config.sender_postal_address())
        except ComplianceError as exc:
            raise SendBlocked(str(exc)) from exc
        if is_placeholder_address(email.footer or ""):
            raise SendBlocked(
                "this email was composed while the postal address was still a "
                "placeholder — re-draft it before sending")

    if business.status is not BusinessStatus.EMAIL_APPROVED:
        raise TransitionError(
            f"sending requires status EMAIL_APPROVED, got {business.status.value}")

    _assert_still_approved(session, business, email)

    if is_suppressed(session, email.recipient):
        raise SuppressionError(f"{email.recipient} is on the suppression list")
    if (business.geo_country or "US").upper() != "US":
        raise SendBlocked(f"geo-gated: {business.geo_country}")

    identity = eligible_identity(session, identities)

    result: SendResult = sender.send(
        sender=identity.address,
        sender_name=identity.display_name or config.sender_name(),
        recipient=delivery_address,
        subject=(f"[TEST → {email.recipient}] {email.subject}"
                 if redirect_to else email.subject),
        body=email.body,
    )

    email.inbox_used = identity.address
    identity.sent_count += 1

    if not result.ok:
        email.status = EmailStatus.FAILED
        identity.bounce_count += 1
        _pause_if_degraded(session, identity)
        record_event(
            session, actor=Actor.SYSTEM.value, action="send:failed",
            subject_type=SubjectType.EMAIL.value, subject_id=business.id,
            after={"reason": f"send failed via {identity.address}: {result.detail}"},
        )
        session.flush()
        return SendOutcome(business.id, email.recipient, False, result.detail)

    email.status = EmailStatus.SENT
    email.sent_at = utcnow()
    advance(session, business, BusinessStatus.SENT, actor=Actor.SYSTEM.value,
            reason=f"sent via {identity.address} ({mode})")
    record_event(
        session, actor=Actor.SYSTEM.value, action="send:delivered",
        subject_type=SubjectType.EMAIL.value, subject_id=business.id,
        after={"mode": mode, "inbox": identity.address,
               "message_id": result.message_id,
               "intended_recipient": email.recipient,
               "delivered_to": delivery_address,
               "reason": (f"delivered to {delivery_address} via {identity.address}"
                          + (f" (redirected from {email.recipient})" if redirect_to else "")
                          + (f" [{mode}]" if mode != "live" else ""))},
    )
    session.flush()
    return SendOutcome(business.id, delivery_address, True, result.detail or mode,
                       result.message_id)


def _pause_if_degraded(session: Session, identity: SenderIdentity) -> None:
    """The kill switch. Automatic, because a person always notices too late."""
    if identity.paused or identity.sent_count < MIN_SAMPLE_FOR_RATES:
        return
    reason = ""
    if identity.bounce_rate > MAX_BOUNCE_RATE:
        reason = (f"bounce rate {identity.bounce_rate:.1%} exceeds "
                  f"{MAX_BOUNCE_RATE:.1%}")
    elif identity.complaint_rate > MAX_COMPLAINT_RATE:
        reason = (f"complaint rate {identity.complaint_rate:.2%} exceeds "
                  f"{MAX_COMPLAINT_RATE:.2%}")
    if not reason:
        return
    identity.paused = True
    identity.paused_reason = reason
    identity.paused_at = utcnow()
    record_event(
        session, actor=Actor.SYSTEM.value, action="send:identity_paused",
        subject_type="sender_identity", subject_id=None,
        after={"address": identity.address,
               "reason": f"KILL SWITCH: {identity.address} paused — {reason}"},
    )


def send_approved(
    session: Session,
    sender: Sender,
    identities: list[SenderIdentity],
    limit: int = 10,
    redirect_to: str | None = None,
) -> list[SendOutcome]:
    """Send every approved email we are currently permitted to send."""
    businesses = session.execute(
        select(Business).where(Business.status == BusinessStatus.EMAIL_APPROVED)
        .order_by(Business.created_at).limit(limit)
    ).scalars().all()

    outcomes: list[SendOutcome] = []
    for business in businesses:
        try:
            outcomes.append(
                send_one(session, business, sender, identities, redirect_to))
        except (SendBlocked, SuppressionError, TransitionError, NotFoundError) as exc:
            outcomes.append(SendOutcome(business.id, "", False, str(exc)))
    return outcomes
