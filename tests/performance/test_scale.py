"""Scale stress: many businesses through research→generate, then the API and the
audit ledger must stay correct and fast — and the grounding invariant must hold
for EVERY generated site (no unverified/conflict field ever rendered as fact)."""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from app.api.main import create_app, get_session
from app.core.audit import verify_chain

pytestmark = pytest.mark.performance

N = 250


def test_scale_pipeline_grounding_and_ledger(session, make_site_drafted, capsys):
    t0 = time.perf_counter()
    for i in range(N):
        make_site_drafted(name=f"Biz {i}", place_id=f"p{i}")
    session.commit()
    seed_s = time.perf_counter() - t0

    app = create_app()

    def _override():
        yield session

    app.dependency_overrides[get_session] = _override
    client = TestClient(app)

    t1 = time.perf_counter()
    pipeline = client.get("/api/pipeline").json()
    queue = client.get("/api/review-queue").json()
    api_s = time.perf_counter() - t1

    with capsys.disabled():
        print(f"\n[scale] seeded {N} businesses in {seed_s:.2f}s; "
              f"pipeline+queue served in {api_s:.3f}s")

    assert len(pipeline) == N
    assert len(queue) == N  # all are SITE_DRAFTED

    # Grounding property across the WHOLE batch: every rendered fact is a verified
    # field only (address/phone) — the unverified 'services' is never on any site.
    for item in queue:
        facts = {f["field"] for s in item["website"]["content"]["sections"]
                 for f in s.get("facts", [])}
        assert facts <= {"address", "phone"}, f"unverified fact leaked: {facts}"
        assert "services" in item["website"]["needs_confirmation"]

    # The audit ledger stays verifiable at scale.
    ok, bad = verify_chain(session)
    assert ok is True, f"audit chain broke at seq {bad}"

    # Serving the board must stay snappy even with N businesses.
    assert api_s < 5.0, f"pipeline+queue too slow at N={N}: {api_s:.2f}s"
