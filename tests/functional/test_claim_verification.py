"""A named human may vouch for a fact — and the ledger records who."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.main import create_app, get_session
from app.core.enums import ClaimStatus
from app.models.audit import AuditEvent
from app.models.research_claim import ResearchClaim

pytestmark = pytest.mark.functional


@pytest.fixture
def client(session):
    app = create_app()

    def _override():
        yield session

    app.dependency_overrides[get_session] = _override
    return TestClient(app)


def _claim(session, business_id, field="services", status=ClaimStatus.UNVERIFIED, value="stuff"):
    return session.query(ResearchClaim).filter_by(
        business_id=business_id, field=field, status=status).first() or \
        session.query(ResearchClaim).filter_by(business_id=business_id, field=field).first()


def test_operator_can_verify_an_unverified_claim(client, session, make_site_drafted):
    biz, _ = make_site_drafted()
    claim = _claim(session, biz.id)
    assert claim.status is ClaimStatus.UNVERIFIED

    res = client.post(f"/api/claims/{claim.id}/verify",
                      json={"verifier": "shreyas", "note": "called the owner"})
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "operator_verified"
    assert body["verified_by"] == "shreyas"
    assert body["ships_as_fact"] is True


def test_verification_is_attributed_on_the_ledger(client, session, make_site_drafted):
    """Attribution is the point — an operator-verified fact names its operator."""
    biz, _ = make_site_drafted()
    claim = _claim(session, biz.id)
    client.post(f"/api/claims/{claim.id}/verify",
                json={"verifier": "shreyas", "note": "confirmed by phone"})

    session.expire_all()
    event = session.query(AuditEvent).filter_by(action="claim:operator_verified").one()
    assert event.actor == "human"
    assert event.after["verified_by"] == "shreyas"
    assert "shreyas verified" in event.after["reason"]
    assert "confirmed by phone" in event.after["reason"]
    # the prior state is preserved, so the change is reconstructable
    assert event.before["status"] == "unverified"


def test_operator_may_correct_the_value_while_verifying(client, session, make_site_drafted):
    biz, _ = make_site_drafted()
    claim = _claim(session, biz.id)
    res = client.post(f"/api/claims/{claim.id}/verify",
                      json={"verifier": "shreyas", "value": "Lawn mowing and edging"})
    assert res.json()["value"] == "Lawn mowing and edging"

    session.expire_all()
    assert session.get(ResearchClaim, claim.id).value == "Lawn mowing and edging"


def test_already_corroborated_claims_are_refused(client, session, make_site_drafted):
    """Nothing to vouch for — two sources already agree."""
    biz, _ = make_site_drafted()
    claim = session.query(ResearchClaim).filter_by(
        business_id=biz.id, status=ClaimStatus.VERIFIED).first()
    res = client.post(f"/api/claims/{claim.id}/verify", json={"verifier": "shreyas"})
    assert res.status_code == 409


def test_unknown_claim_is_404(client):
    import uuid
    res = client.post(f"/api/claims/{uuid.uuid4()}/verify", json={"verifier": "x"})
    assert res.status_code == 404


def test_operator_verified_facts_reach_the_generated_site(session, make_site_drafted):
    """A human vouching makes the fact shippable, exactly like corroboration."""
    from app.stages.generate import generate_website

    biz, _ = make_site_drafted()
    claim = _claim(session, biz.id)
    claim.status = ClaimStatus.OPERATOR_VERIFIED
    claim.verified_by = "shreyas"
    session.flush()

    biz.status = __import__("app.core.enums", fromlist=["x"]).BusinessStatus.RESEARCHED
    site = generate_website(session, biz)
    rendered = [f["field"] for sec in site.content_json["sections"]
                for f in sec.get("facts", [])]
    assert claim.field in rendered
