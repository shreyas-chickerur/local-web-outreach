"""Gate-draft editing: re-hash + audit, never a status change, never non-compliant."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.main import create_app, get_session
from app.core.enums import BusinessStatus
from app.models.audit import AuditEvent
from app.models.email import Email
from app.models.website import Website

pytestmark = pytest.mark.functional


@pytest.fixture
def client(session):
    app = create_app()

    def _override():
        yield session

    app.dependency_overrides[get_session] = _override
    return TestClient(app)


def _hero(site: Website) -> dict:
    return next(s for s in site.content_json["sections"] if s["type"] == "hero")


# --------------------------------- site ----------------------------------- #
def test_site_edit_rehashes_and_audits_without_changing_status(client, session, make_site_drafted):
    biz, _ = make_site_drafted()
    before = client.get(f"/api/review/{biz.id}").json()
    old_hash = before["website"]["content_hash"]

    res = client.post(f"/api/businesses/{biz.id}/edit-draft", json={
        "subject_type": "site", "heading": "Reliable lawn care in Frisco",
    })
    assert res.status_code == 200
    new_hash = res.json()["content_hash"]
    assert new_hash != old_hash  # re-hashed

    session.expire_all()
    site = session.query(Website).filter_by(business_id=biz.id).one()
    assert _hero(site)["heading"] == "Reliable lawn care in Frisco"
    assert site.content_hash == new_hash
    # status untouched — editing is not a gate decision
    assert session.get(type(biz), biz.id).status is BusinessStatus.SITE_DRAFTED
    # and the edit is on the immutable ledger
    actions = [e.action for e in session.query(AuditEvent).all()]
    assert "edit" in actions


def test_site_edit_makes_a_staged_approval_stale(client, make_site_drafted):
    """The whole point of re-hashing: an approval against the pre-edit text 409s."""
    biz, _ = make_site_drafted()
    stale_hash = client.get(f"/api/review/{biz.id}").json()["website"]["content_hash"]
    client.post(f"/api/businesses/{biz.id}/edit-draft",
                json={"subject_type": "site", "heading": "New headline"})

    res = client.post(f"/api/businesses/{biz.id}/site-decision", json={
        "decision": "approve", "approver": "operator", "expected_content_hash": stale_hash,
    })
    assert res.status_code == 409


def test_site_edit_rejected_when_not_at_the_gate(client, session, make_site_drafted):
    biz, _ = make_site_drafted()
    biz.status = BusinessStatus.SITE_APPROVED
    session.flush()
    res = client.post(f"/api/businesses/{biz.id}/edit-draft",
                      json={"subject_type": "site", "heading": "too late"})
    assert res.status_code == 409


# --------------------------------- email ---------------------------------- #
def test_email_edit_rehashes_and_preserves_the_footer(client, session, make_email_drafted):
    biz, _ = make_email_drafted()
    email = session.query(Email).filter_by(business_id=biz.id).one()
    old_hash, footer = email.content_hash, email.footer

    # An operator rewrites the body and (carelessly) drops the compliance footer.
    res = client.post(f"/api/businesses/{biz.id}/edit-draft", json={
        "subject_type": "email", "body": "Hi there — short note about your website.",
    })
    assert res.status_code == 200

    session.expire_all()
    email = session.query(Email).filter_by(business_id=biz.id).one()
    assert email.content_hash != old_hash
    assert footer in email.body  # footer re-attached: the edit cannot drop CAN-SPAM
    assert "UNSUBSCRIBE" in email.body
    assert session.get(type(biz), biz.id).status is BusinessStatus.EMAIL_DRAFTED


def test_email_edit_rejects_a_deceptive_subject(client, make_email_drafted):
    """HTTP surface: a deceptive subject is a 400, not a silent accept."""
    biz, _ = make_email_drafted()
    res = client.post(f"/api/businesses/{biz.id}/edit-draft", json={
        "subject_type": "email", "subject": "Re: your invoice",  # fakes a reply thread
    })
    assert res.status_code == 400
    assert "deceptive" in res.json()["detail"].lower()


def test_email_edit_leaves_the_draft_untouched_when_rejected(session, make_email_drafted):
    """Service layer (no request-scoped rollback): the stored draft is unchanged."""
    from app.api import schemas, service
    from app.core.errors import ComplianceError

    biz, _ = make_email_drafted()
    original = session.query(Email).filter_by(business_id=biz.id).one()
    old_subject, old_hash = original.subject, original.content_hash

    with pytest.raises(ComplianceError):
        service.edit_draft(session, biz.id, schemas.DraftEditIn(
            subject_type="email", subject="Re: your invoice",
        ))

    email = session.query(Email).filter_by(business_id=biz.id).one()
    assert email.subject == old_subject
    assert email.content_hash == old_hash


def test_email_edit_then_approve_with_the_new_hash_succeeds(client, make_email_drafted):
    biz, _ = make_email_drafted()
    edited = client.post(f"/api/businesses/{biz.id}/edit-draft", json={
        "subject_type": "email", "subject": "A quick idea for your website",
    }).json()

    res = client.post(f"/api/businesses/{biz.id}/email-decision", json={
        "decision": "approve", "approver": "operator",
        "expected_content_hash": edited["content_hash"],
    })
    assert res.status_code == 200
    assert res.json()["new_status"] == "EMAIL_APPROVED"


# ------------------- site approval unlocks the email gate ------------------- #
def test_approving_a_site_drafts_the_outreach_email(client, session, make_site_drafted):
    """Gate 1 → the email appears at Gate 2 automatically; no manual step."""
    biz, site = make_site_drafted()
    biz.contact_email = "owner@acme.example"
    session.flush()

    res = client.post(f"/api/businesses/{biz.id}/site-decision", json={
        "decision": "approve", "approver": "operator",
        "expected_content_hash": site.content_hash,
    })
    assert res.status_code == 200
    # composing the email advances it past SITE_APPROVED to the second gate
    assert res.json()["new_status"] == "EMAIL_DRAFTED"

    queue = client.get("/api/review-queue").json()
    item = next(i for i in queue if i["business"]["id"] == str(biz.id))
    assert item["gate"] == "email"
    assert item["email"]["recipient"] == "owner@acme.example"


def test_approving_a_site_without_an_email_rests_at_site_approved(client, make_site_drafted):
    """No contact email yet is not an approval failure — it just stops there."""
    biz, site = make_site_drafted()  # no contact_email set
    res = client.post(f"/api/businesses/{biz.id}/site-decision", json={
        "decision": "approve", "approver": "operator",
        "expected_content_hash": site.content_hash,
    })
    assert res.status_code == 200
    assert res.json()["new_status"] == "SITE_APPROVED"
