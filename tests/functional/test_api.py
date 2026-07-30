"""End-to-end API tests (FastAPI TestClient) for the Operator Console backend."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.main import create_app, get_session
from app.core.audit import verify_chain
from app.core.enums import BusinessStatus, ClaimStatus, Severity
from app.models.business import Business
from app.models.research_claim import ResearchClaim
from app.models.site_weakness import SiteWeakness
from app.stages.generate import generate_website

pytestmark = pytest.mark.functional

ADDR = "418 W Ridgemont Ave, Frisco, TX 75034"
PHONE = "(972) 555-0148"


def _claim(biz_id, field, value, status, conf, sources):
    return ResearchClaim(business_id=biz_id, field=field, value=value, status=status,
                         confidence=conf, corroborations=len(sources), sources=sources)


def _seed(session):
    """One SITE_DRAFTED business with dossier + weaknesses + a draft website,
    plus a second DISCOVERED business for pipeline variety."""
    biz = Business(name="The Roundhouse Diner", location="Frisco, TX", category="restaurant",
                   address=ADDR, phone=PHONE, place_id="rh", opportunity_score=82,
                   status=BusinessStatus.RESEARCHED)
    session.add(biz)
    session.flush()

    two = [{"source_type": "yelp", "source_url": "https://yelp/x"},
           {"source_type": "directory", "source_url": "https://dir/x"}]
    one = [{"source_type": "site", "source_url": "https://rh/x"}]
    session.add_all([
        _claim(biz.id, "address", ADDR, ClaimStatus.VERIFIED, 0.96, two),
        _claim(biz.id, "phone", PHONE, ClaimStatus.VERIFIED, 0.94, two),
        _claim(biz.id, "rating", "4.1 | 4.6", ClaimStatus.CONFLICT, 0.3, two),
        _claim(biz.id, "services", "fried catfish, burgers", ClaimStatus.UNVERIFIED, 0.5, one),
    ])
    session.add_all([
        SiteWeakness(business_id=biz.id, issue="no_https", severity=Severity.HIGH,
                     evidence="served over http"),
        SiteWeakness(business_id=biz.id, issue="not_mobile_responsive", severity=Severity.HIGH,
                     evidence="fixed layout"),
    ])
    session.flush()
    site = generate_website(session, biz)  # advances RESEARCHED -> SITE_DRAFTED

    other = Business(name="Corner Tap House", location="Frisco, TX", category="restaurant",
                     place_id="cth", status=BusinessStatus.DISCOVERED)
    session.add(other)
    session.commit()
    return biz, site


@pytest.fixture
def api(session):
    app = create_app()

    def _override_session():
        yield session

    app.dependency_overrides[get_session] = _override_session
    biz, site = _seed(session)
    return TestClient(app), session, biz, site


# --------------------------------- reads ----------------------------------- #
def test_health(api):
    client, *_ = api
    assert client.get("/api/health").json() == {"ok": True}


def test_pipeline_lists_businesses(api):
    client, *_ = api
    rows = client.get("/api/pipeline").json()
    names = {r["name"]: r for r in rows}
    assert {"The Roundhouse Diner", "Corner Tap House"} <= set(names)
    assert names["The Roundhouse Diner"]["status"] == "SITE_DRAFTED"
    assert names["The Roundhouse Diner"]["opportunity_score"] is not None


def test_review_queue_payload(api):
    client, _s, biz, site = api
    queue = client.get("/api/review-queue").json()
    assert len(queue) == 1  # only SITE_DRAFTED items
    item = queue[0]
    assert item["business"]["name"] == "The Roundhouse Diner"
    assert item["gate"] == "site"
    assert item["transition"] == "SITE_DRAFTED → SITE_APPROVED"
    assert {w["issue"] for w in item["weaknesses"]} >= {"no_https", "not_mobile_responsive"}
    # dossier carries verified + conflict + unverified with sources
    by_field = {c["field"]: c for c in item["dossier"]}
    assert by_field["address"]["status"] == "verified"
    assert by_field["rating"]["status"] == "conflict"
    assert len(by_field["address"]["sources"]) == 2
    # website is grounded: only verified fields rendered as facts
    facts = [f for s in item["website"]["content"]["sections"] for f in s.get("facts", [])]
    assert {f["field"] for f in facts} <= {"address", "phone"}
    assert item["website"]["content_hash"] == site.content_hash
    assert item["questions"]  # owner questions for unverified fields


def test_business_detail(api):
    client, _s, biz, _site = api
    detail = client.get(f"/api/businesses/{biz.id}").json()
    assert detail["business"]["name"] == "The Roundhouse Diner"
    assert len(detail["websites"]) == 1
    assert any(e["action"].startswith("advance:") for e in detail["audit"])


def test_review_item_404(api):
    client, *_ = api
    import uuid
    assert client.get(f"/api/review/{uuid.uuid4()}").status_code == 404


# ------------------------------ the site gate ------------------------------ #
def test_approve_advances_and_logs_hashed_approval(api):
    client, session, biz, site = api
    resp = client.post(f"/api/businesses/{biz.id}/site-decision",
                       json={"decision": "approve", "approver": "shreyas",
                             "expected_content_hash": site.content_hash})
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] and body["new_status"] == "SITE_APPROVED"

    # no longer in the review queue
    assert client.get("/api/review-queue").json() == []
    # pipeline reflects the new status
    rows = {r["name"]: r for r in client.get("/api/pipeline").json()}
    assert rows["The Roundhouse Diner"]["status"] == "SITE_APPROVED"
    # approval logged, bound to the exact reviewed content hash
    approvals = client.get("/api/approvals").json()
    top = next(a for a in approvals if a["business_name"] == "The Roundhouse Diner")
    assert top["decision"] == "approve"
    assert top["content_hash"] == site.content_hash
    # audit chain intact after the mutation
    session.expire_all()
    ok, bad = verify_chain(session)
    assert ok is True, f"chain broke at {bad}"


def test_stale_content_hash_rejected(api):
    client, _s, biz, _site = api
    resp = client.post(f"/api/businesses/{biz.id}/site-decision",
                       json={"decision": "approve", "approver": "shreyas",
                             "expected_content_hash": "sha256:stale-does-not-match"})
    assert resp.status_code == 409
    # business did not advance
    assert client.get("/api/review-queue").json()[0]["business"]["status"] == "SITE_DRAFTED"


def test_reject_disqualifies(api):
    client, _s, biz, site = api
    resp = client.post(f"/api/businesses/{biz.id}/site-decision",
                       json={"decision": "reject", "approver": "shreyas",
                             "expected_content_hash": site.content_hash,
                             "notes": "not a fit"})
    assert resp.status_code == 200
    assert resp.json()["new_status"] == "DISQUALIFIED"
    approvals = client.get("/api/approvals").json()
    assert any(a["decision"] == "reject" for a in approvals)


def test_request_changes_keeps_state(api):
    client, _s, biz, site = api
    resp = client.post(f"/api/businesses/{biz.id}/site-decision",
                       json={"decision": "request_changes", "approver": "shreyas",
                             "expected_content_hash": site.content_hash,
                             "notes": "add the menu section"})
    assert resp.status_code == 200
    assert resp.json()["new_status"] == "SITE_DRAFTED"  # stays for re-draft
    # still in the queue, and the request is logged
    assert len(client.get("/api/review-queue").json()) == 1
    assert any(a["decision"] == "request_changes" for a in client.get("/api/approvals").json())


def test_decision_on_wrong_state_409(api):
    client, session, biz, site = api
    # approve once -> SITE_APPROVED; a second decision is now illegal
    client.post(f"/api/businesses/{biz.id}/site-decision",
                json={"decision": "approve", "approver": "x",
                      "expected_content_hash": site.content_hash})
    resp = client.post(f"/api/businesses/{biz.id}/site-decision",
                       json={"decision": "approve", "approver": "x",
                             "expected_content_hash": site.content_hash})
    assert resp.status_code == 409


def test_decision_missing_business_404(api):
    client, *_ = api
    import uuid
    resp = client.post(f"/api/businesses/{uuid.uuid4()}/site-decision",
                       json={"decision": "approve", "approver": "x",
                             "expected_content_hash": "sha256:whatever"})
    assert resp.status_code == 404
