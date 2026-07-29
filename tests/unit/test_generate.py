"""Unit tests for Stage 4 website generation — grounding + no-fabrication guards."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.core.audit import verify_chain
from app.core.enums import BusinessStatus as S
from app.core.enums import ClaimStatus, WebsiteState
from app.core.errors import SiteIntegrityError
from app.models.business import Business
from app.models.research_claim import ResearchClaim
from app.stages.generate import (
    generate_website,
    industry_template,
    validate_site_content,
)

pytestmark = pytest.mark.unit


def _biz(session, *, name="Acme", category="restaurant") -> Business:
    biz = Business(name=name, location="Frisco, TX", category=category, status=S.RESEARCHED)
    session.add(biz)
    session.flush()
    return biz


def _verified(session, biz, field, value, conf=0.9) -> ResearchClaim:
    claim = ResearchClaim(
        business_id=biz.id, field=field, value=value, status=ClaimStatus.VERIFIED,
        confidence=conf, corroborations=2,
        sources=[{"source_type": "yelp", "source_url": "https://x"}],
    )
    session.add(claim)
    session.flush()
    return claim


def _all_facts(content):
    return [f for s in content["sections"] for f in s.get("facts", [])]


# ------------------------------ templates ---------------------------------- #
def test_industry_template_selection():
    assert industry_template("restaurant")[0] == "restaurant"
    assert industry_template("lawn")[0] == "service"
    assert industry_template("bookstore")[0] == "generic"
    assert industry_template(None)[0] == "generic"


# --------------------------- grounding / traceability ----------------------- #
def test_generated_site_is_fully_grounded(session):
    biz = _biz(session)
    _verified(session, biz, "address", "6733 W Main St")
    _verified(session, biz, "phone", "(972) 377-0707")
    site = generate_website(session, biz)

    facts = _all_facts(site.content_json)
    verified_ids = {
        str(c.id) for c in session.execute(select(ResearchClaim)).scalars()
    }
    assert facts, "expected some verified facts rendered"
    # every rendered fact traces to a verified claim
    assert all(f["claim_id"] in verified_ids for f in facts)
    assert {f["field"] for f in facts} == {"address", "phone"}


def test_guard_unverified_fact_rejected():
    content = {"sections": [
        {"type": "contact", "facts": [
            {"field": "phone", "value": "x", "claim_id": "not-a-real-id"}
        ]}
    ]}
    with pytest.raises(SiteIntegrityError):
        validate_site_content(content, verified_claim_ids={"real-id"})


def test_guard_fact_without_claim_id_rejected():
    content = {"sections": [{"type": "contact", "facts": [{"field": "phone", "value": "x"}]}]}
    with pytest.raises(SiteIntegrityError):
        validate_site_content(content, verified_claim_ids=set())


def test_guard_no_fabricated_reviews():
    content = {"sections": [
        {"type": "reviews", "facts": [{"field": "review", "value": "Great!", "claim_id": "z"}]}
    ]}
    with pytest.raises(SiteIntegrityError):
        validate_site_content(content, verified_claim_ids={"z"})


def test_unverified_claims_are_not_rendered(session):
    biz = _biz(session)
    _verified(session, biz, "address", "6733 W Main St")
    # an UNVERIFIED services claim must not appear as a fact
    session.add(ResearchClaim(
        business_id=biz.id, field="services", value="catfish", status=ClaimStatus.UNVERIFIED,
        confidence=0.5, corroborations=1, sources=[{"source_type": "yelp", "source_url": "https://x"}],
    ))
    session.flush()
    site = generate_website(session, biz)
    rendered_fields = {f["field"] for f in _all_facts(site.content_json)}
    assert "services" not in rendered_fields
    assert "services" in site.content_json["needs_confirmation"]


def test_highest_confidence_claim_wins(session):
    biz = _biz(session)
    _verified(session, biz, "phone", "(972) 377-0707", conf=0.98)
    _verified(session, biz, "phone", "(972) 000-0000", conf=0.90)
    site = generate_website(session, biz)
    phone_fact = next(f for f in _all_facts(site.content_json) if f["field"] == "phone")
    assert phone_fact["value"] == "(972) 377-0707"


# ------------------------------ private preview ----------------------------- #
def test_preview_is_private(session):
    biz = _biz(session)
    _verified(session, biz, "phone", "(972) 377-0707")
    site = generate_website(session, biz)
    assert site.state is WebsiteState.DRAFT
    assert site.preview_token and site.preview_token in site.preview_url
    assert site.content_json["noindex"] is True


# ------------------------------ spine integration --------------------------- #
def test_generate_advances_to_site_drafted_and_audits(session):
    biz = _biz(session)
    _verified(session, biz, "phone", "(972) 377-0707")
    generate_website(session, biz)
    assert biz.status is S.SITE_DRAFTED
    ok, bad = verify_chain(session)
    assert ok is True and bad is None


def test_thin_business_generates_grounded_draft_without_fabricating(session):
    # No verified claims at all -> a valid draft with only hero+cta and everything
    # flagged for owner confirmation; NOT a fabricated site.
    biz = _biz(session, category="lawn")
    site = generate_website(session, biz)
    assert _all_facts(site.content_json) == []
    assert set(site.content_json["needs_confirmation"])  # non-empty
    assert biz.status is S.SITE_DRAFTED
