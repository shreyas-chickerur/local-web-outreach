"""Two sources agreeing is what makes a fact. Deciding whether they agree is
the hard part — they never write it identically."""

from __future__ import annotations

import pytest

from app.workbench.corroborate import corroborate, normalize
from app.workbench.types import RawClaim, SourceType

pytestmark = pytest.mark.unit


def _c(field, value, url, kind=SourceType.GBP):
    return RawClaim(field=field, value=value, source_url=url, source_type=kind)


def test_two_independent_sources_verify_a_fact():
    facts = corroborate([
        _c("phone", "(469) 294-0067", "https://maps.google/x", SourceType.GBP),
        _c("phone", "469-294-0067", "https://yelp.com/x", SourceType.YELP),
    ])
    assert facts[0].confidence.value == "verified"
    assert facts[0].corroborations == 2 and facts[0].is_fact


def test_one_source_is_only_unverified():
    facts = corroborate([_c("phone", "(469) 294-0067", "https://maps.google/x")])
    assert facts[0].confidence.value == "unverified"
    assert facts[0].is_fact is False


def test_disagreement_is_a_conflict_that_names_both_sources():
    facts = corroborate([
        _c("rating", "4.8", "https://maps.google/x", SourceType.GBP),
        _c("rating", "2.4", "https://yelp.com/x", SourceType.YELP),
    ])
    fact = facts[0]
    assert fact.confidence.value == "conflict" and not fact.is_fact
    by_source = {c["source_type"]: c["value"] for c in fact.candidates}
    assert by_source["google"] == "4.8" and by_source["yelp"] == "2.4"


@pytest.mark.parametrize("a,b", [
    # the real cases that used to produce false conflicts
    ("9500 Frisco St, Frisco, TX 75033", "9500 Frisco St, Frisco, TX 75033, USA"),
    ("1800 Preston On The Lake Blvd, Little Elm, TX", "1800 Preston On The Lake, Little Elm, TX"),
    ("5729 Lebanon Rd #100, Frisco, TX 75034", "5729 Lebanon Rd, Suite 100, Frisco, TX 75034"),
    ("123 Elm Street, Frisco TX", "123 Elm St., Frisco TX"),
])
def test_addresses_written_differently_still_agree(a, b):
    facts = corroborate([_c("address", a, "https://one/"), _c("address", b, "https://two/")])
    assert facts[0].confidence.value == "verified"


def test_genuinely_different_addresses_still_conflict():
    facts = corroborate([
        _c("address", "1800 Preston Rd, Frisco, TX", "https://one/"),
        _c("address", "1900 Preston Rd, Frisco, TX", "https://two/"),
    ])
    assert facts[0].confidence.value == "conflict"


@pytest.mark.parametrize("a,b,expected", [
    ("4.6", "4.5", "verified"),
    ("4.7", "5.0", "verified"),      # 0.3 apart is the same verdict
    ("4.8", "2.4", "conflict"),      # a real disagreement
])
def test_ratings_agree_within_a_tolerance(a, b, expected):
    facts = corroborate([_c("rating", a, "https://one/"), _c("rating", b, "https://two/")])
    assert facts[0].confidence.value == expected


@pytest.mark.parametrize("a,b", [
    ("(972) 377-0707", "+1 972-377-0707"),
    ("972.377.0707", "9723770707"),
])
def test_phones_compare_by_digits(a, b):
    assert normalize(a, "phone") == normalize(b, "phone")


def test_the_same_source_twice_does_not_corroborate_itself():
    """Independence is the whole point of the rule."""
    facts = corroborate([
        _c("phone", "(469) 294-0067", "https://maps.google/x"),
        _c("phone", "(469) 294-0067", "https://maps.google/x"),
    ])
    assert facts[0].confidence.value == "unverified"
    assert facts[0].corroborations == 1


def test_a_state_spelled_out_matches_its_abbreviation():
    """OpenStreetMap writes 'Texas' where Google and Yelp write 'TX', which made
    three sources reporting one address look like a three-way disagreement."""
    facts = corroborate([
        _c("address", "9225 Preston Rd, Frisco, TX 75033, USA", "https://g/"),
        _c("address", "9225 Preston Rd, Frisco, TX 75033", "https://y/"),
        _c("address", "9225 Preston Road, Frisco, Texas, 75033", "https://o/"),
    ])
    assert facts[0].confidence.value == "verified"
    assert facts[0].corroborations == 3
