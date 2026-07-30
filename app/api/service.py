"""Read + write operations backing the Operator Console API.

Reads assemble the same side-by-side payload the console renders; the write path
(`decide_site`) records a hashed approval bound to the exact reviewed draft and
advances the business through the spine's state machine. Kept free of FastAPI so
it stays unit-testable; routes map its domain errors to HTTP status codes.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api import schemas
from app.core.approvals import create_approval
from app.core.enums import Actor, BusinessStatus, ClaimStatus, Decision, SubjectType, WebsiteState
from app.core.errors import NotFoundError, StaleContentError, TransitionError
from app.core.state_machine import advance
from app.models.approval import Approval
from app.models.audit import AuditEvent
from app.models.business import Business
from app.models.research_claim import ResearchClaim
from app.models.site_weakness import SiteWeakness
from app.models.website import Website

_CLAIM_ORDER = {ClaimStatus.VERIFIED: 0, ClaimStatus.CONFLICT: 1, ClaimStatus.UNVERIFIED: 2}


def _latest_reason(session: Session, business_id: uuid.UUID) -> str:
    event = session.execute(
        select(AuditEvent)
        .where(AuditEvent.subject_id == business_id, AuditEvent.action.like("advance:%"))
        .order_by(AuditEvent.seq.desc())
        .limit(1)
    ).scalars().first()
    return (event.after or {}).get("reason", "—") if event else "—"


def _summary(session: Session, biz: Business) -> schemas.BusinessSummary:
    return schemas.BusinessSummary(
        id=biz.id, name=biz.name, location=biz.location, category=biz.category,
        status=biz.status.value, opportunity_score=biz.opportunity_score,
        has_site=biz.has_site, why=_latest_reason(session, biz.id),
    )


def _weaknesses(session: Session, business_id: uuid.UUID) -> list[schemas.Weakness]:
    rows = session.execute(
        select(SiteWeakness).where(SiteWeakness.business_id == business_id)
    ).scalars().all()
    return [schemas.Weakness(issue=w.issue, severity=w.severity.value, evidence=w.evidence)
            for w in rows]


def _claims(session: Session, business_id: uuid.UUID) -> list[schemas.Claim]:
    rows = list(session.execute(
        select(ResearchClaim).where(ResearchClaim.business_id == business_id)
    ).scalars().all())
    rows.sort(key=lambda c: (_CLAIM_ORDER.get(c.status, 9), c.field))
    return [schemas.Claim(field=c.field, value=c.value, status=c.status.value,
                          confidence=c.confidence, corroborations=c.corroborations,
                          sources=list(c.sources or [])) for c in rows]


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
                              reason=(e.after or {}).get("reason"))
            for e in session.execute(
                select(AuditEvent).where(AuditEvent.subject_id == biz.id)
                .order_by(AuditEvent.seq)
            ).scalars().all()
        ],
    )


def _review_item(session: Session, biz: Business) -> schemas.ReviewItem:
    site = _latest_draft(session, biz.id)
    website = _website_out(site) if site else None
    needs = website.needs_confirmation if website else []
    return schemas.ReviewItem(
        business=_summary(session, biz), address=biz.address, phone=biz.phone,
        why=_latest_reason(session, biz.id),
        weaknesses=_weaknesses(session, biz.id), dossier=_claims(session, biz.id),
        questions=_questions(needs), website=website, gate="site",
        transition="SITE_DRAFTED → SITE_APPROVED",
    )


def list_review_queue(session: Session) -> list[schemas.ReviewItem]:
    rows = session.execute(
        select(Business).where(Business.status == BusinessStatus.SITE_DRAFTED)
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
    elif decision is Decision.REJECT:
        advance(session, biz, BusinessStatus.DISQUALIFIED,
                actor=Actor.HUMAN.value, reason="operator rejected the site")
    # request_changes: no transition; the draft is regenerated and re-reviewed.

    return schemas.DecisionResult(
        ok=True, business_id=biz.id, new_status=biz.status.value, approval_id=approval.id
    )
