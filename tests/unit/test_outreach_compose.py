"""Stage-6 compose tests: happy path + suppression/compliance/state guards."""

from __future__ import annotations

import pytest
from sqlalchemy import func, select

from app.ai.email_composer import TemplateEmailComposer
from app.core import config
from app.core.approvals import create_approval
from app.core.compliance import suppress, validate_email
from app.core.enums import Actor, Decision, EmailKind, EmailStatus, SubjectType, SuppressionReason
from app.core.enums import BusinessStatus as S
from app.core.errors import NotFoundError, SuppressionError, TransitionError
from app.core.state_machine import advance
from app.models.email import Email
from app.stages.outreach import compose_email

pytestmark = pytest.mark.unit


def _approve_site(session, biz, site):
    approval = create_approval(session, subject_type=SubjectType.SITE, subject_id=biz.id,
                               decision=Decision.APPROVE, approver="op", content=site.content_json)
    advance(session, biz, S.SITE_APPROVED, actor=Actor.HUMAN.value, approval=approval)


def _email_count(session):
    return session.execute(select(func.count()).select_from(Email)).scalar_one()


def test_compose_happy_path(session, make_site_drafted):
    biz, site = make_site_drafted(place_id="c1")
    biz.contact_email = "owner@shop.com"
    session.flush()
    _approve_site(session, biz, site)

    email = compose_email(session, biz, TemplateEmailComposer())
    assert biz.status is S.EMAIL_DRAFTED
    assert email.kind is EmailKind.OUTREACH
    assert email.status is EmailStatus.DRAFT
    assert email.suppression_checked is True
    assert email.recipient == "owner@shop.com"
    assert email.content_hash
    assert site.preview_url in email.body  # the one CTA links the real preview
    assert "unsubscribe" in email.footer.lower()
    assert config.sender_postal_address() in email.footer


def test_compose_passes_compliance_independently(session, make_site_drafted):
    biz, site = make_site_drafted(place_id="c2")
    biz.contact_email = "x@y.com"
    session.flush()
    _approve_site(session, biz, site)
    email = compose_email(session, biz, TemplateEmailComposer())
    # re-validate the composed email from scratch
    validate_email(subject=email.subject, footer=email.footer,
                   postal_address=config.sender_postal_address())


def test_guard_suppressed_recipient_blocks_compose(session, make_site_drafted):
    biz, site = make_site_drafted(place_id="c3")
    biz.contact_email = "no@spam.com"
    session.flush()
    _approve_site(session, biz, site)
    suppress(session, email="no@spam.com", reason=SuppressionReason.UNSUBSCRIBE)

    with pytest.raises(SuppressionError):
        compose_email(session, biz, TemplateEmailComposer())
    assert biz.status is S.SITE_APPROVED  # not advanced
    assert _email_count(session) == 0  # no draft produced


def test_guard_wrong_state_raises(session, make_site_drafted):
    biz, _site = make_site_drafted(place_id="c4")  # still SITE_DRAFTED
    biz.contact_email = "a@b.com"
    session.flush()
    with pytest.raises(TransitionError):
        compose_email(session, biz, TemplateEmailComposer())


def test_guard_no_contact_email_raises(session, make_site_drafted):
    biz, site = make_site_drafted(place_id="c5")  # contact_email is None
    _approve_site(session, biz, site)
    with pytest.raises(NotFoundError):
        compose_email(session, biz, TemplateEmailComposer())
