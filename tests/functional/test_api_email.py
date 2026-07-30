"""API tests for the email gate (Gate 2): review payload + decision endpoint."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.main import create_app, get_session
from app.core.audit import verify_chain
from app.models.email import Email

pytestmark = pytest.mark.functional


@pytest.fixture
def client(session):
    app = create_app()

    def _override():
        yield session

    app.dependency_overrides[get_session] = _override
    return TestClient(app)


def test_review_queue_includes_email_gate(client, make_email_drafted):
    biz, email = make_email_drafted(place_id="e1", contact_email="o@example.com")
    queue = client.get("/api/review-queue").json()
    item = next(i for i in queue if i["business"]["id"] == str(biz.id))
    assert item["gate"] == "email"
    assert item["transition"] == "EMAIL_DRAFTED → EMAIL_APPROVED"
    assert item["email"]["recipient"] == "o@example.com"
    assert "unsubscribe" in item["email"]["footer"].lower()
    assert item["email"]["content_hash"] == email.content_hash
    assert item["website"] is not None  # the approved site shown for context


def test_email_approve_advances_and_logs(client, make_email_drafted, session):
    biz, email = make_email_drafted(place_id="e2")
    resp = client.post(f"/api/businesses/{biz.id}/email-decision",
                       json={"decision": "approve", "approver": "shreyas",
                             "expected_content_hash": email.content_hash})
    assert resp.status_code == 200 and resp.json()["new_status"] == "EMAIL_APPROVED"

    session.expire_all()
    assert session.get(Email, email.id).status.value == "approved"  # ready for send layer
    approvals = client.get("/api/approvals").json()
    assert any(a["subject_type"] == "email" and a["decision"] == "approve" for a in approvals)
    assert client.get("/api/review-queue").json() == []  # cleared the queue
    ok, bad = verify_chain(session)
    assert ok is True, f"chain broke at {bad}"


def test_email_stale_hash_rejected(client, make_email_drafted):
    biz, _email = make_email_drafted(place_id="e3")
    resp = client.post(f"/api/businesses/{biz.id}/email-decision",
                       json={"decision": "approve", "approver": "x",
                             "expected_content_hash": "sha256:not-current"})
    assert resp.status_code == 409


def test_email_reject_disqualifies(client, make_email_drafted):
    biz, email = make_email_drafted(place_id="e4")
    resp = client.post(f"/api/businesses/{biz.id}/email-decision",
                       json={"decision": "reject", "approver": "x",
                             "expected_content_hash": email.content_hash})
    assert resp.status_code == 200 and resp.json()["new_status"] == "DISQUALIFIED"


def test_email_request_changes_keeps_state(client, make_email_drafted):
    biz, email = make_email_drafted(place_id="e5")
    resp = client.post(f"/api/businesses/{biz.id}/email-decision",
                       json={"decision": "request_changes", "approver": "x",
                             "expected_content_hash": email.content_hash})
    assert resp.status_code == 200 and resp.json()["new_status"] == "EMAIL_DRAFTED"
    assert any(i["business"]["id"] == str(biz.id) for i in client.get("/api/review-queue").json())


def test_email_decision_wrong_state_409(client, make_site_drafted):
    biz, _site = make_site_drafted(place_id="e6")  # SITE_DRAFTED, no email yet
    resp = client.post(f"/api/businesses/{biz.id}/email-decision",
                       json={"decision": "approve", "approver": "x",
                             "expected_content_hash": "sha256:whatever"})
    assert resp.status_code == 409
