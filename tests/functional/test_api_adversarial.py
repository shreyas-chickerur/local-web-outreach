"""Adversarial + load tests for the API: malformed input is rejected, a burst of
reads stays healthy, and a burst of approvals keeps the audit chain intact."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.api.main import create_app, get_session
from app.core.audit import verify_chain

pytestmark = pytest.mark.functional


@pytest.fixture
def client(session):
    app = create_app()

    def _override():
        yield session

    app.dependency_overrides[get_session] = _override
    return TestClient(app)


def test_read_burst_all_ok(client, make_site_drafted):
    make_site_drafted(place_id="rb")
    for _ in range(200):
        assert client.get("/api/pipeline").status_code == 200
        assert client.get("/api/review-queue").status_code == 200


def test_bad_decision_enum_is_422(client, make_site_drafted):
    biz, site = make_site_drafted(place_id="be")
    resp = client.post(f"/api/businesses/{biz.id}/site-decision",
                       json={"decision": "nuke", "approver": "x",
                             "expected_content_hash": site.content_hash})
    assert resp.status_code == 422  # not a valid decision


def test_missing_content_hash_is_422(client, make_site_drafted):
    biz, _site = make_site_drafted(place_id="mc")
    resp = client.post(f"/api/businesses/{biz.id}/site-decision",
                       json={"decision": "approve", "approver": "x"})
    assert resp.status_code == 422  # expected_content_hash is required


def test_malformed_uuid_path_is_422(client):
    assert client.get("/api/businesses/not-a-uuid").status_code == 422


def test_unknown_business_is_404(client):
    assert client.get(f"/api/businesses/{uuid.uuid4()}").status_code == 404


def test_decision_burst_keeps_chain_linear(client, make_site_drafted, session):
    targets = [make_site_drafted(name=f"B{i}", place_id=f"burst{i}") for i in range(30)]
    for biz, site in targets:
        resp = client.post(f"/api/businesses/{biz.id}/site-decision",
                           json={"decision": "approve", "approver": "ops",
                                 "expected_content_hash": site.content_hash})
        assert resp.status_code == 200 and resp.json()["new_status"] == "SITE_APPROVED"

    assert client.get("/api/review-queue").json() == []  # all cleared
    approvals = client.get("/api/approvals").json()
    assert sum(1 for a in approvals if a["decision"] == "approve") == 30

    session.expire_all()
    ok, bad = verify_chain(session)
    assert ok is True, f"audit chain broke at seq {bad}"
