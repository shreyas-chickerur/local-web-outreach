"""End-to-end Stage 3: build dossiers from the bundled real Frisco data and
verify corroboration, gap-handling, entity rejection, and audit integrity."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.ai.research_runner import PassthroughExtractor
from app.core.audit import verify_chain
from app.core.enums import BusinessStatus, ClaimStatus
from app.demo_data import demo_businesses
from app.models.business import Business
from app.models.research_claim import ResearchClaim
from app.stages.research import build_dossier


def _run(session):
    results = {}
    extractor = PassthroughExtractor()
    for entry in demo_businesses():
        sources = entry.pop("sources")
        biz = Business(status=BusinessStatus.RESEARCHED, **entry)
        session.add(biz)
        session.flush()
        results[biz.place_id] = (biz, build_dossier(session, biz, sources, extractor,
                                                    model_version="test"))
    session.commit()
    return results


@pytest.mark.functional
def test_frisco_research_sqlite(session):
    results = _run(session)
    depot_biz, depot = results["demo-depot"]
    _js_biz, js = results["demo-jslawn"]

    # Depot: address + phone corroborated by 2 independent sources -> VERIFIED
    verified = {c.field: c for c in depot.verified()}
    assert "address" in verified and "phone" in verified
    assert "6733 W Main St" in verified["address"].value
    assert verified["phone"].confidence >= 0.85

    # single-source facts are UNVERIFIED, not promoted
    by_field = {c.field: c for c in depot.claims}
    assert by_field["services"].status is ClaimStatus.UNVERIFIED
    assert by_field["year_opened"].status is ClaimStatus.UNVERIFIED

    # owner unknown -> a question, never a fabricated claim
    assert "owner_name" not in {c.field for c in depot.claims}
    assert any("owner name" in q for q in depot.questions)

    # JS Lawn: the look-alike "J.S.M. Lawn Care" was rejected, not merged
    assert any(s.entity_name == "J.S.M. Lawn Care" for s in js.rejected_sources)
    # so no phone claim exists (the only phone came from the rejected source)
    assert "phone" not in {c.field for c in js.claims}

    # persisted rows match, and the audit chain is intact
    rows = session.execute(
        select(ResearchClaim).where(ResearchClaim.business_id == depot_biz.id)
    ).scalars().all()
    assert len(rows) == len(depot.claims)
    ok, bad = verify_chain(session)
    assert ok is True, f"audit chain broke at {bad}"


@pytest.mark.functional
@pytest.mark.postgres
def test_frisco_research_postgres(pg_session):
    results = _run(pg_session)
    _b, depot = results["demo-depot"]
    verified_fields = {c.field for c in depot.verified()}
    assert {"address", "phone"} <= verified_fields
    ok, bad = verify_chain(pg_session)
    assert ok is True and bad is None
