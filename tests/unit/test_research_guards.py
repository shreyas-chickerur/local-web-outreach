"""Guard + engine tests for Stage 3 research (invariant #1 and entity resolution)."""

from __future__ import annotations

import pytest

from app.ai.research_runner import RawClaim, SourceRecord
from app.ai.validators import validate_raw_claims
from app.core.enums import ClaimStatus, SourceType
from app.core.errors import ResearchIntegrityError
from app.stages.entity_resolution import TargetEntity, resolve
from app.stages.research import corroborate

pytestmark = pytest.mark.unit


def _claim(field, value, url, stype=SourceType.DIRECTORY):
    return RawClaim(field=field, value=value, source_url=url, source_type=stype)


# --------------------------- invariant #1 guards --------------------------- #
def test_guard_no_claim_without_source():
    with pytest.raises(ResearchIntegrityError):
        validate_raw_claims([_claim("phone", "555-1212", "")])


def test_guard_no_claim_with_empty_value():
    with pytest.raises(ResearchIntegrityError):
        validate_raw_claims([_claim("phone", "   ", "https://x")])


def test_valid_claims_pass_through():
    claims = [_claim("phone", "555-1212", "https://x")]
    assert validate_raw_claims(claims) == claims


# ------------------------------ corroboration ------------------------------ #
def test_corroboration_requires_two_sources():
    # single source -> UNVERIFIED
    one = corroborate([_claim("address", "1 Main St", "https://a")])
    assert one[0].status is ClaimStatus.UNVERIFIED

    # two independent sources agreeing -> VERIFIED
    two = corroborate([
        _claim("address", "1 Main St", "https://a"),
        _claim("address", "1 Main St", "https://b"),
    ])
    assert two[0].status is ClaimStatus.VERIFIED
    assert two[0].corroborations == 2


def test_confidence_threshold_enforced():
    one = corroborate([_claim("address", "1 Main St", "https://a")])
    assert one[0].confidence < 0.85  # sub-threshold; cannot ship as fact
    two = corroborate([
        _claim("address", "1 Main St", "https://a"),
        _claim("address", "1 Main St", "https://b"),
    ])
    assert two[0].confidence >= 0.85


def test_same_source_twice_does_not_verify():
    # two claims from the SAME url must not count as independent corroboration
    claims = [
        _claim("phone", "555-1212", "https://a"),
        _claim("phone", "555-1212", "https://a"),
    ]
    assert corroborate(claims)[0].status is ClaimStatus.UNVERIFIED


def test_conflict_flagged_not_guessed():
    # two sources give DIFFERENT phone numbers -> CONFLICT, never silently one
    claims = [
        _claim("phone", "815-777-9110", "https://a"),
        _claim("phone", "815-994-3647", "https://b"),
    ]
    resolved = corroborate(claims)[0]
    assert resolved.status is ClaimStatus.CONFLICT
    assert "815-777-9110" in resolved.value and "815-994-3647" in resolved.value


def test_corroborate_empty_returns_empty():
    assert corroborate([]) == []


def test_confidence_caps_at_098():
    # many agreeing sources must not push confidence past the ceiling
    claims = [_claim("address", "1 Main St", f"https://src{i}") for i in range(8)]
    resolved = corroborate(claims)[0]
    assert resolved.status is ClaimStatus.VERIFIED
    assert resolved.confidence <= 0.98
    assert resolved.corroborations == 8


# --------------------------- entity resolution ----------------------------- #
def _source(name, phone=None, address=None):
    return SourceRecord(
        source_type=SourceType.DIRECTORY, source_url=f"https://x/{name}",
        entity_name=name, entity_phone=phone, entity_address=address,
    )


def test_guard_entity_disambiguation_rejects_lookalike():
    target = TargetEntity(name="JS Lawn Care Service", address="7934 Milestone Ridge Dr")
    kept, rejected = resolve(target, [
        _source("JS Lawn Care Service", address="7934 Milestone Ridge Dr"),
        _source("J.S.M. Lawn Care", phone="(469) 555-0148"),  # different business
    ])
    assert [s.entity_name for s in kept] == ["JS Lawn Care Service"]
    assert [s.entity_name for s in rejected] == ["J.S.M. Lawn Care"]


def test_guard_entity_conflicting_phone_rejected():
    target = TargetEntity(name="Acme Diner", phone="972-377-0707")
    kept, rejected = resolve(target, [
        _source("Acme Diner", phone="972-377-0707"),
        _source("Acme Diner", phone="972-000-0000"),  # name matches but phone disagrees
    ])
    assert len(kept) == 1 and len(rejected) == 1


def test_entity_resolution_matches_on_phone():
    target = TargetEntity(name="Totally Different Name", phone="972-377-0707")
    kept, _ = resolve(target, [_source("The Depot Cafe", phone="(972) 377-0707")])
    assert len(kept) == 1  # phone triangulation ties them despite the name


# ---- field-aware value normalization (false conflicts from formatting) ------
def test_address_formatting_differences_do_not_create_a_conflict():
    """Real case: Google omits ', USA'; Yelp appends it. Same address."""
    from app.ai.research_runner import RawClaim
    from app.core.enums import ClaimStatus, SourceType
    from app.stages.research import corroborate

    resolved = corroborate([
        RawClaim(field="address", value="9500 Frisco St, Frisco, TX 75033",
                 source_url="https://maps.google.com/x", source_type=SourceType.GBP),
        RawClaim(field="address", value="9500 Frisco St, Frisco, TX 75033, USA",
                 source_url="https://yelp.com/biz/x", source_type=SourceType.DIRECTORY),
    ])
    assert len(resolved) == 1
    assert resolved[0].status is ClaimStatus.VERIFIED
    assert resolved[0].corroborations == 2
    assert resolved[0].value == "9500 Frisco St, Frisco, TX 75033"  # cleaner form kept


def test_genuinely_different_addresses_still_conflict():
    """Executive Mowing: Google says Custer Rd, Yelp says Warren Pkwy."""
    from app.ai.research_runner import RawClaim
    from app.core.enums import ClaimStatus, SourceType
    from app.stages.research import corroborate

    resolved = corroborate([
        RawClaim(field="address", value="11625 Custer Rd, Frisco, TX 75035",
                 source_url="https://maps.google.com/x", source_type=SourceType.GBP),
        RawClaim(field="address", value="6160 Warren Pkwy Suite, 100, Frisco, TX 75034, USA",
                 source_url="https://yelp.com/biz/x", source_type=SourceType.DIRECTORY),
    ])
    assert resolved[0].status is ClaimStatus.CONFLICT


@pytest.mark.parametrize("a,b", [
    ("(972) 377-0707", "+1 972-377-0707"),
    ("972.377.0707", "9723770707"),
    ("(972) 377-0707", "972-377-0707"),
])
def test_phone_formatting_differences_corroborate(a, b):
    from app.ai.research_runner import RawClaim
    from app.core.enums import ClaimStatus, SourceType
    from app.stages.research import corroborate

    resolved = corroborate([
        RawClaim(field="phone", value=a, source_url="https://one/", source_type=SourceType.GBP),
        RawClaim(field="phone", value=b, source_url="https://two/",
                 source_type=SourceType.DIRECTORY),
    ])
    assert resolved[0].status is ClaimStatus.VERIFIED


def test_street_abbreviations_fold_together():
    from app.stages.research import _norm_address

    assert _norm_address("123 Elm Street, Frisco, TX") == _norm_address("123 Elm St., Frisco TX")
    assert _norm_address("1 North Main Ave") == _norm_address("1 N Main Avenue")


# ------------------------- rating corroboration ------------------------------
@pytest.mark.parametrize("g,y,status", [
    ("4.6", "4.5", "verified"),
    ("4.9", "5.0", "verified"),
    ("4.7", "5.0", "verified"),   # real case: Camero's — 0.3 apart is agreement
    ("4.5", "5.0", "verified"),   # exactly at tolerance
    ("4.6", "3.9", "conflict"),   # genuinely different standing
    ("4.0", "2.5", "conflict"),
])
def test_ratings_corroborate_within_a_tolerance(g, y, status):
    """Google and Yelp poll different crowds; they agree in substance, not to
    the decimal. A tolerance avoids the arbitrary split a bucket boundary makes
    (4.7 and 5.0 would land in different half-star buckets)."""
    from app.ai.research_runner import RawClaim
    from app.core.enums import SourceType
    from app.stages.research import corroborate

    resolved = corroborate([
        RawClaim(field="rating", value=g, source_url="https://maps.google/x",
                 source_type=SourceType.GBP),
        RawClaim(field="rating", value=y, source_url="https://yelp.com/x",
                 source_type=SourceType.DIRECTORY),
    ])
    assert resolved[0].status.value == status


def test_address_matches_when_one_source_omits_the_street_type():
    """Real case: Google 'Preston On The Lake Blvd' vs Yelp 'Preston On The Lake'."""
    from app.ai.research_runner import RawClaim
    from app.core.enums import ClaimStatus, SourceType
    from app.stages.research import corroborate

    resolved = corroborate([
        RawClaim(field="address", value="1800 Preston On The Lake Blvd, Little Elm, TX 75068",
                 source_url="https://maps.google/x", source_type=SourceType.GBP),
        RawClaim(field="address", value="1800 Preston On The Lake, Little Elm, TX 75068",
                 source_url="https://yelp.com/x", source_type=SourceType.DIRECTORY),
    ])
    assert resolved[0].status is ClaimStatus.VERIFIED


def test_different_house_numbers_still_conflict():
    """Dropping street types must not make distinct addresses look identical."""
    from app.ai.research_runner import RawClaim
    from app.core.enums import ClaimStatus, SourceType
    from app.stages.research import corroborate

    resolved = corroborate([
        RawClaim(field="address", value="1800 Preston Rd, Frisco, TX 75034",
                 source_url="https://maps.google/x", source_type=SourceType.GBP),
        RawClaim(field="address", value="1900 Preston Rd, Frisco, TX 75034",
                 source_url="https://yelp.com/x", source_type=SourceType.DIRECTORY),
    ])
    assert resolved[0].status is ClaimStatus.CONFLICT
