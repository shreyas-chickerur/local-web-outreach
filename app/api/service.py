"""Read + write operations backing the Operator Console API.

Reads assemble the same side-by-side payload the console renders; the write path
(`decide_site`) records a hashed approval bound to the exact reviewed draft and
advances the business through the spine's state machine. Kept free of FastAPI so
it stays unit-testable; routes map its domain errors to HTTP status codes.
"""

from __future__ import annotations

import uuid
from copy import deepcopy
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.email_composer import TemplateEmailComposer
from app.api import schemas
from app.core.approvals import create_approval, hash_content
from app.core.audit import latest_transition_reason, record_event
from app.core.audit_labels import humanize
from app.core.clock import utcnow
from app.core.compliance import validate_subject
from app.core.enums import (
    Actor,
    BusinessStatus,
    ClaimStatus,
    Decision,
    EmailKind,
    EmailStatus,
    SubjectType,
    WebsiteState,
)
from app.core.errors import (
    ComplianceError,
    NotFoundError,
    StaleContentError,
    SuppressionError,
    TransitionError,
)
from app.core.state_machine import advance
from app.models.approval import Approval
from app.models.audit import AuditEvent
from app.models.business import Business
from app.models.email import Email
from app.models.research_claim import ResearchClaim
from app.models.site_weakness import SiteWeakness
from app.models.website import Website
from app.stages.outreach import compose_email

_CLAIM_ORDER = {
    ClaimStatus.VERIFIED: 0,
    ClaimStatus.OPERATOR_VERIFIED: 1,
    ClaimStatus.CONFLICT: 2,
    ClaimStatus.UNVERIFIED: 3,
}


def _summary(session: Session, biz: Business) -> schemas.BusinessSummary:
    return schemas.BusinessSummary(
        id=biz.id, name=biz.name, location=biz.location, category=biz.category,
        status=biz.status.value, opportunity_score=biz.opportunity_score,
        has_site=biz.has_site, why=latest_transition_reason(session, biz.id),
    )


def _weaknesses(session: Session, business_id: uuid.UUID) -> list[schemas.Weakness]:
    rows = session.execute(
        select(SiteWeakness).where(SiteWeakness.business_id == business_id)
    ).scalars().all()
    return [schemas.Weakness(issue=w.issue, severity=w.severity.value, evidence=w.evidence)
            for w in rows]


def _claim_out(c: ResearchClaim) -> schemas.Claim:
    return schemas.Claim(
        id=c.id, field=c.field, value=c.value, status=c.status.value,
        confidence=c.confidence, corroborations=c.corroborations,
        sources=list(c.sources or []), verified_by=c.verified_by,
        verified_at=c.verified_at, verified_note=c.verified_note,
        ships_as_fact=c.ships_as_fact,
    )


def _claims(session: Session, business_id: uuid.UUID) -> list[schemas.Claim]:
    rows = list(session.execute(
        select(ResearchClaim).where(ResearchClaim.business_id == business_id)
    ).scalars().all())
    rows.sort(key=lambda c: (_CLAIM_ORDER.get(c.status, 9), c.field))
    return [_claim_out(c) for c in rows]


def _latest_draft(session: Session, business_id: uuid.UUID) -> Website | None:
    return session.execute(
        select(Website)
        .where(Website.business_id == business_id, Website.state == WebsiteState.DRAFT)
        .order_by(Website.version.desc())
        .limit(1)
    ).scalars().first()


def _all_websites(session: Session, business_id: uuid.UUID) -> list[Website]:
    return list(session.execute(
        select(Website).where(Website.business_id == business_id)
        .order_by(Website.version.desc())
    ).scalars().all())


def _website_out(site: Website) -> schemas.WebsiteOut:
    content = site.content_json or {}
    return schemas.WebsiteOut(
        version=site.version, state=site.state.value, preview_url=site.preview_url,
        content_hash=site.content_hash, content=content,
        needs_confirmation=list(content.get("needs_confirmation", [])),
    )


def _latest_email(session: Session, business_id: uuid.UUID) -> Email | None:
    return session.execute(
        select(Email).where(
            Email.business_id == business_id,
            Email.kind == EmailKind.OUTREACH,
            Email.status == EmailStatus.DRAFT,
        ).order_by(Email.created_at.desc()).limit(1)
    ).scalars().first()


def _email_out(email: Email) -> schemas.EmailOut:
    return schemas.EmailOut(
        id=email.id, kind=email.kind.value, recipient=email.recipient, subject=email.subject,
        body=email.body, footer=email.footer, status=email.status.value,
        content_hash=email.content_hash,
    )


def _questions(needs_confirmation: list[str]) -> list[str]:
    return [f"Can you confirm your {f.replace('_', ' ')}?" for f in needs_confirmation]


def _get_business(session: Session, business_id: uuid.UUID) -> Business:
    biz = session.get(Business, business_id)
    if biz is None:
        raise NotFoundError(f"business {business_id} not found")
    return biz


# ------------------------------- reads ------------------------------------- #
def list_pipeline(session: Session) -> list[schemas.BusinessSummary]:
    rows = session.execute(select(Business).order_by(Business.created_at)).scalars().all()
    return [_summary(session, b) for b in rows]


def get_detail(session: Session, business_id: uuid.UUID) -> schemas.BusinessDetail:
    biz = _get_business(session, business_id)
    return schemas.BusinessDetail(
        business=_summary(session, biz), address=biz.address, phone=biz.phone,
        existing_site_url=biz.existing_site_url,
        weaknesses=_weaknesses(session, biz.id), dossier=_claims(session, biz.id),
        websites=[_website_out(w) for w in _all_websites(session, biz.id)],
        audit=[
            schemas.AuditItem(ts=e.ts, actor=e.actor, action=e.action,
                              title=humanize(e.action),
                              reason=(e.after or {}).get("reason"))
            for e in session.execute(
                select(AuditEvent).where(AuditEvent.subject_id == biz.id)
                .order_by(AuditEvent.seq)
            ).scalars().all()
        ],
    )


def _review_item(session: Session, biz: Business) -> schemas.ReviewItem:
    # The generated site (still the DRAFT record) is shown for both gates: it's
    # the thing being approved at Gate 1, and context for the email at Gate 2.
    site = _latest_draft(session, biz.id)
    website = _website_out(site) if site else None
    gate: Literal["site", "email"]
    if biz.status is BusinessStatus.EMAIL_DRAFTED:
        gate, transition = "email", "EMAIL_DRAFTED → EMAIL_APPROVED"
        email_row = _latest_email(session, biz.id)
        email = _email_out(email_row) if email_row else None
    else:
        gate, transition, email = "site", "SITE_DRAFTED → SITE_APPROVED", None
    return schemas.ReviewItem(
        business=_summary(session, biz), address=biz.address, phone=biz.phone,
        why=latest_transition_reason(session, biz.id),
        weaknesses=_weaknesses(session, biz.id), dossier=_claims(session, biz.id),
        questions=_questions(website.needs_confirmation if website else []),
        website=website, email=email, gate=gate, transition=transition,
    )


def list_review_queue(session: Session) -> list[schemas.ReviewItem]:
    rows = session.execute(
        select(Business).where(Business.status.in_(
            [BusinessStatus.SITE_DRAFTED, BusinessStatus.EMAIL_DRAFTED]
        ))
        .order_by(Business.created_at)
    ).scalars().all()
    return [_review_item(session, b) for b in rows]


def get_review_item(session: Session, business_id: uuid.UUID) -> schemas.ReviewItem:
    biz = _get_business(session, business_id)
    return _review_item(session, biz)


def list_approvals(session: Session) -> list[schemas.ApprovalOut]:
    rows = session.execute(select(Approval).order_by(Approval.decided_at.desc())).scalars().all()
    out = []
    for a in rows:
        biz = session.get(Business, a.subject_id)
        out.append(schemas.ApprovalOut(
            id=a.id, subject_type=a.subject_type.value, subject_id=a.subject_id,
            business_name=biz.name if biz else None, decision=a.decision.value,
            approver=a.approver, content_hash=a.content_hash, notes=a.notes,
            decided_at=a.decided_at,
        ))
    return out


# ------------------------------- writes ------------------------------------ #
def decide_site(
    session: Session, business_id: uuid.UUID, payload: schemas.SiteDecisionIn
) -> schemas.DecisionResult:
    """Gate 1: record a hashed approval bound to the exact reviewed draft and
    advance (approve → SITE_APPROVED, reject → DISQUALIFIED, request_changes →
    no state change)."""
    biz = _get_business(session, business_id)
    if biz.status is not BusinessStatus.SITE_DRAFTED:
        raise TransitionError(
            f"site decision requires status SITE_DRAFTED, got {biz.status.value}"
        )
    site = _latest_draft(session, biz.id)
    if site is None:
        raise NotFoundError(f"no draft website for business {business_id}")
    if site.content_hash != payload.expected_content_hash:
        raise StaleContentError(
            "the draft changed since you reviewed it — reload and review the new version"
        )

    decision = Decision(payload.decision)
    approval = create_approval(
        session, subject_type=SubjectType.SITE, subject_id=biz.id, decision=decision,
        approver=payload.approver, content=site.content_json, notes=payload.notes,
    )

    if decision is Decision.APPROVE:
        advance(session, biz, BusinessStatus.SITE_APPROVED,
                actor=Actor.HUMAN.value, approval=approval)
        # Approving the site is what unlocks outreach, so draft the email now —
        # it appears at Gate 2 for a second, separate approval. If we can't (no
        # contact email yet, recipient suppressed, non-compliant), the business
        # simply rests at SITE_APPROVED; that is not an approval failure.
        try:
            compose_email(session, biz, TemplateEmailComposer())
        except (NotFoundError, SuppressionError, ComplianceError, TransitionError) as exc:
            # Record WHY, so the operator sees a reason instead of a lead that
            # silently stops dead at SITE_APPROVED with no email to review.
            record_event(
                session, actor=Actor.SYSTEM.value, action="outreach:blocked",
                subject_type=SubjectType.EMAIL.value, subject_id=biz.id,
                after={"reason": f"no outreach email drafted — {exc}"},
            )
    elif decision is Decision.REJECT:
        advance(session, biz, BusinessStatus.DISQUALIFIED,
                actor=Actor.HUMAN.value, reason="operator rejected the site")
    # request_changes: no transition; the draft is regenerated and re-reviewed.

    return schemas.DecisionResult(
        ok=True, business_id=biz.id, new_status=biz.status.value, approval_id=approval.id
    )


def edit_draft(
    session: Session, business_id: uuid.UUID, payload: schemas.DraftEditIn
) -> schemas.DraftEditResult:
    """Apply an operator edit to the draft at the current gate, re-hash it, and
    append an audit event. Editing is NOT a gate decision: it never changes
    status and never records an approval. Because the content hash changes, any
    approval the operator had already staged against the old text goes stale —
    they must re-review, which is the point.

    Only non-factual copy is editable: the site's hero heading/subheading (the
    fact rows carry claim_ids and stay grounded) and the email's subject/body.
    The CAN-SPAM footer is re-attached if an edit removed it, and the subject is
    re-validated, so an edit cannot produce a non-compliant email.
    """
    biz = _get_business(session, business_id)

    if payload.subject_type == "site":
        if biz.status is not BusinessStatus.SITE_DRAFTED:
            raise TransitionError(
                f"site edits require status SITE_DRAFTED, got {biz.status.value}"
            )
        site = _latest_draft(session, biz.id)
        if site is None:
            raise NotFoundError(f"no draft website for business {business_id}")
        content = deepcopy(site.content_json or {})
        hero = next((s for s in content.get("sections", []) if s.get("type") == "hero"), None)
        if hero is None:
            raise NotFoundError("draft has no hero section to edit")
        before = {"heading": hero.get("heading"), "subheading": hero.get("subheading")}
        if payload.heading is not None:
            hero["heading"] = payload.heading
        if payload.subheading is not None:
            hero["subheading"] = payload.subheading
        site.content_json = content
        site.content_hash = hash_content(content)
        session.flush()
        record_event(
            session, actor=Actor.HUMAN.value, action="edit",
            subject_type=SubjectType.SITE.value, subject_id=biz.id,
            before=before,
            after={"heading": hero.get("heading"), "subheading": hero.get("subheading"),
                   "reason": "operator edited site hero copy · re-hashed "
                             f"{site.content_hash[:12]}"},
        )
        return schemas.DraftEditResult(
            ok=True, business_id=biz.id, gate="site", content_hash=site.content_hash
        )

    # email
    if biz.status is not BusinessStatus.EMAIL_DRAFTED:
        raise TransitionError(
            f"email edits require status EMAIL_DRAFTED, got {biz.status.value}"
        )
    email = _latest_email(session, biz.id)
    if email is None:
        raise NotFoundError(f"no draft email for business {business_id}")

    new_subject = payload.subject if payload.subject is not None else email.subject
    new_body = payload.body if payload.body is not None else email.body
    validate_subject(new_subject)  # an edit cannot make the subject deceptive
    if email.footer and email.footer not in new_body:
        new_body = new_body.rstrip() + email.footer  # never let an edit drop the footer

    before = {"subject": email.subject, "body": email.body}
    email.subject = new_subject
    email.body = new_body
    email.content_hash = hash_content(
        {"subject": new_subject, "body": new_body, "recipient": email.recipient}
    )
    session.flush()
    record_event(
        session, actor=Actor.HUMAN.value, action="edit",
        subject_type=SubjectType.EMAIL.value, subject_id=biz.id,
        before=before,
        after={"subject": new_subject,
               "reason": f"operator edited outreach copy · re-hashed {email.content_hash[:12]}"},
    )
    return schemas.DraftEditResult(
        ok=True, business_id=biz.id, gate="email", content_hash=email.content_hash
    )


def verify_claim(
    session: Session, claim_id: uuid.UUID, payload: schemas.ClaimVerifyIn
) -> schemas.Claim:
    """Let a named human vouch for a claim the machine could not corroborate.

    Machine corroboration (two independent sources) is the only route to truth
    that needs no trust. It is not the only legitimate one: an operator who
    phones the business knows more than two directories do. So a human may
    verify a claim — but the ledger records WHO, WHEN, and any correction, and
    the claim is marked OPERATOR_VERIFIED rather than VERIFIED so the two are
    never confused.
    """
    claim = session.get(ResearchClaim, claim_id)
    if claim is None:
        raise NotFoundError(f"claim {claim_id} not found")
    if claim.status is ClaimStatus.VERIFIED:
        raise TransitionError("this claim is already corroborated by two sources")

    before = {"status": claim.status.value, "value": claim.value}
    if payload.value is not None:
        claim.value = payload.value
    claim.status = ClaimStatus.OPERATOR_VERIFIED
    claim.confidence = 1.0          # a human checked it
    claim.verified_by = payload.verifier
    claim.verified_at = utcnow()
    claim.verified_note = payload.note
    session.flush()

    record_event(
        session, actor=Actor.HUMAN.value, action="claim:operator_verified",
        subject_type="research_claim", subject_id=claim.business_id,
        before=before,
        after={"field": claim.field, "value": claim.value,
               "verified_by": payload.verifier,
               "reason": f"{payload.verifier} verified {claim.field}"
                         + (f" — {payload.note}" if payload.note else "")},
    )
    return _claim_out(claim)


def decide_email(
    session: Session, business_id: uuid.UUID, payload: schemas.EmailDecisionIn
) -> schemas.DecisionResult:
    """Gate 2: record a hashed approval bound to the exact reviewed email and
    advance (approve → EMAIL_APPROVED, reject → DISQUALIFIED, request_changes →
    no state change). Nothing is sent — sending is Phase 7."""
    biz = _get_business(session, business_id)
    if biz.status is not BusinessStatus.EMAIL_DRAFTED:
        raise TransitionError(
            f"email decision requires status EMAIL_DRAFTED, got {biz.status.value}"
        )
    email = _latest_email(session, biz.id)
    if email is None:
        raise NotFoundError(f"no draft email for business {business_id}")
    if email.content_hash != payload.expected_content_hash:
        raise StaleContentError(
            "the email changed since you reviewed it — reload and review the new version"
        )

    decision = Decision(payload.decision)
    approval = create_approval(
        session, subject_type=SubjectType.EMAIL, subject_id=biz.id, decision=decision,
        approver=payload.approver,
        content={"subject": email.subject, "body": email.body, "recipient": email.recipient},
        notes=payload.notes,
    )

    if decision is Decision.APPROVE:
        advance(session, biz, BusinessStatus.EMAIL_APPROVED,
                actor=Actor.HUMAN.value, approval=approval)
        email.status = EmailStatus.APPROVED  # ready for the send layer (Phase 7)
    elif decision is Decision.REJECT:
        advance(session, biz, BusinessStatus.DISQUALIFIED,
                actor=Actor.HUMAN.value, reason="operator rejected the email")
    # request_changes: no transition; the email is re-drafted and re-reviewed.

    return schemas.DecisionResult(
        ok=True, business_id=biz.id, new_status=biz.status.value, approval_id=approval.id
    )
