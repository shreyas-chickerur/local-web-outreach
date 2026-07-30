"""Stage 6: COMPOSE (outreach email).

Draft a compliant, personalized outreach email for a business whose site was
approved. Guards, in order:
  1. business must be SITE_APPROVED (else illegal),
  2. must have a contact email,
  3. recipient must not be suppressed (else no draft — invariant #4),
  4. the assembled email must pass CAN-SPAM validation (footer address + opt-out,
     non-deceptive subject).
On success, persists a DRAFT Email and advances SITE_APPROVED → EMAIL_DRAFTED for
Gate 2. The email references only true specifics + the real preview link.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.email_composer import EmailComposer
from app.core import config
from app.core.approvals import hash_content
from app.core.compliance import build_footer, is_suppressed, validate_email
from app.core.enums import Actor, BusinessStatus, EmailKind, EmailStatus
from app.core.errors import NotFoundError, SuppressionError, TransitionError
from app.core.state_machine import advance
from app.models.email import Email
from app.models.site_weakness import SiteWeakness
from app.models.website import Website


def compose_email(session: Session, business, composer: EmailComposer) -> Email:  # noqa: ANN001
    if business.status is not BusinessStatus.SITE_APPROVED:
        raise TransitionError(
            f"composing outreach requires status SITE_APPROVED, got {business.status.value}"
        )
    if not business.contact_email:
        raise NotFoundError(f"business {business.id} has no contact_email to send to")
    if is_suppressed(session, business.contact_email):
        raise SuppressionError(f"{business.contact_email} is on the suppression list")

    website = session.execute(
        select(Website).where(Website.business_id == business.id)
        .order_by(Website.version.desc()).limit(1)
    ).scalars().first()
    if website is None:
        raise NotFoundError(f"business {business.id} has no website to link")

    weaknesses = [
        (w.issue, w.severity.value)
        for w in session.execute(
            select(SiteWeakness).where(SiteWeakness.business_id == business.id)
        ).scalars().all()
    ]

    draft = composer.compose(
        business_name=business.name, location=business.location,
        weaknesses=weaknesses, preview_url=website.preview_url,
    )
    postal = config.sender_postal_address()
    footer = build_footer(sender_name=config.sender_name(), postal_address=postal)
    body = draft.body + footer
    validate_email(subject=draft.subject, footer=footer, postal_address=postal)

    email = Email(
        business_id=business.id, kind=EmailKind.OUTREACH, recipient=business.contact_email,
        subject=draft.subject, body=body, footer=footer, status=EmailStatus.DRAFT,
        suppression_checked=True,
        content_hash=hash_content(
            {"subject": draft.subject, "body": body, "recipient": business.contact_email}
        ),
    )
    session.add(email)
    session.flush()

    advance(session, business, BusinessStatus.EMAIL_DRAFTED,
            actor=Actor.SYSTEM.value, reason="outreach email drafted")
    return email
