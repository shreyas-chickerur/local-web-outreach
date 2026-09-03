"""Two sources agreeing is what makes a fact. Deciding whether they agree is
the hard part — they never write it identically."""

from __future__ import annotations

import pytest

from app.workbench.corroborate import corroborate, normalize
from app.workbench.types import Confidence, RawClaim, SourceType

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
        _c("address", "2770 Main St, Frisco, TX", "https://maps.google/x",
           SourceType.GBP),
        _c("address", "1740 N Stemmons Fwy, Lewisville, TX", "https://yelp.com/x",
           SourceType.YELP),
    ])
    fact = facts[0]
    assert fact.confidence.value == "conflict" and not fact.is_fact
    by_source = {c["source_type"]: c["value"] for c in fact.candidates}
    assert by_source["google"].startswith("2770 Main St")
    assert by_source["yelp"].startswith("1740 N Stemmons")


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


def test_two_agreeing_sources_beat_one_dissenter():
    """Ryno Lawn Care's own site lists a different number than its listings.
    That is worth knowing, but it should not erase the fact that Google and
    Yelp agree — a single dissenter used to drop the field to a 30% conflict."""
    claims = [
        RawClaim(field="phone", value="(469) 496-2778",
                 source_url="https://g", source_type=SourceType.GBP),
        RawClaim(field="phone", value="(469) 496-2778",
                 source_url="https://y", source_type=SourceType.YELP),
        RawClaim(field="phone", value="(214) 728-8894",
                 source_url="https://their-site",
                 source_type=SourceType.EXISTING_SITE),
    ]
    fact = corroborate(claims)[0]
    assert fact.confidence is Confidence.VERIFIED
    assert fact.value == "(469) 496-2778"
    assert [d["value"] for d in fact.dissent] == ["(214) 728-8894"]
    # Disagreement is not free: it costs confidence without hiding the answer.
    assert fact.score < 0.9


def test_an_even_split_stays_a_conflict():
    """With one source each way there is no reason to prefer either."""
    claims = [
        RawClaim(field="phone", value="(111) 111-1111",
                 source_url="https://g", source_type=SourceType.GBP),
        RawClaim(field="phone", value="(222) 222-2222",
                 source_url="https://y", source_type=SourceType.YELP),
    ]
    assert corroborate(claims)[0].confidence is Confidence.CONFLICT
