"""End-to-end Stage 3+4: research the bundled Frisco data, then generate a
grounded site draft, and verify traceability + private-preview + audit."""

from __future__ import annotations

import pytest

from app.ai.research_runner import PassthroughExtractor
from app.core.audit import verify_chain
from app.core.enums import BusinessStatus, WebsiteState
from app.demo_data import demo_businesses
from app.models.business import Business
from app.stages.generate import generate_website
from app.stages.research import build_dossier


def _research_then_generate(session):
    out = {}
    extractor = PassthroughExtractor()
    for entry in demo_businesses():
        sources = entry.pop("sources")
        biz = Business(status=BusinessStatus.RESEARCHED, **entry)
        session.add(biz)
        session.flush()
        build_dossier(session, biz, sources, extractor, model_version="test")
        site = generate_website(session, biz)
        out[biz.place_id] = (biz, site)
    session.commit()
    return out


@pytest.mark.functional
def test_generate_from_research_sqlite(session):
    out = _research_then_generate(session)
    depot_biz, depot_site = out["demo-depot"]
    _js_biz, js_site = out["demo-jslawn"]

    # Depot: address + phone were VERIFIED, so the draft renders them (grounded).
    depot_facts = {f["field"] for s in depot_site.content_json["sections"]
                   for f in s.get("facts", [])}
    assert {"address", "phone"} <= depot_facts
    assert depot_biz.status is BusinessStatus.SITE_DRAFTED
    assert depot_site.state is WebsiteState.DRAFT
    assert depot_site.content_json["noindex"] is True

    # JS Lawn: nothing was verified -> no fabricated facts; all flagged to confirm.
    js_facts = [f for s in js_site.content_json["sections"] for f in s.get("facts", [])]
    assert js_facts == []
    assert set(js_site.content_json["needs_confirmation"])

    ok, bad = verify_chain(session)
    assert ok is True, f"audit chain broke at {bad}"


@pytest.mark.functional
@pytest.mark.postgres
def test_generate_from_research_postgres(pg_session):
    out = _research_then_generate(pg_session)
    _b, depot_site = out["demo-depot"]
    facts = {f["field"] for s in depot_site.content_json["sections"] for f in s.get("facts", [])}
    assert {"address", "phone"} <= facts
    ok, bad = verify_chain(pg_session)
    assert ok is True and bad is None
