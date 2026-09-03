"""A lookup returns its best guess, which is regularly a different company."""

from __future__ import annotations

import pytest

from app.workbench.match import name_similarity, same_business

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("a,b", [
    ("Ryno Lawn Care", "Ryno Lawn Care, LLC"),
    ("Craftway Kitchen", "Craftway Kitchen Frisco"),
    ("The Heritage Table", "Heritage Table"),
])
def test_the_same_business_written_differently_matches(a, b):
    assert same_business(a, b)


@pytest.mark.parametrize("a,b", [
    ("Ryno Lawn Care", "Totally Different Diner"),
    ("Town and Country Roofing", "Dwell Roofing & Exteriors"),
    ("Craftway Kitchen", "Legacy Plumbing"),
])
def test_a_different_business_is_refused(a, b):
    """Two Frisco roofers once matched one unrelated listing, and its phone
    number then looked like evidence our own data was wrong."""
    assert not same_business(a, b)


def test_empty_names_never_match():
    assert name_similarity("", "Acme") == 0.0


# --- being too strict throws away correct data, which costs just as much ----
@pytest.mark.parametrize("a,b", [
    # a possessive must not make two spellings look like different companies
    ("JS Lawn Care Service", "J's Lawn Care"),
    ("JC's Landscaping", "JCs Landscaping"),
    # a shorter form of the same name
    ("Starbucks", "Starbucks Coffee Company"),
    ("The Heritage Table", "Heritage Table"),
    ("Craftway Kitchen", "Craftway Kitchen Frisco"),
])
def test_the_same_business_written_more_loosely_still_matches(a, b):
    assert same_business(a, b)


@pytest.mark.parametrize("a,b", [
    # every shared word is a trade description, which identifies nothing
    ("Ryno Lawn Care", "Lawn Care"),
    ("Frisco Lawn", "Frisco Dental"),
    ("Acme Roofing", "Best Roofing"),
    # a real near-miss seen in the wild
    ("JS Lawn Care Service", "J's Landscaping Solutions & more LLC"),
])
def test_a_generic_overlap_is_not_evidence(a, b):
    assert not same_business(a, b)


def test_an_apostrophe_does_not_split_a_token():
    from app.workbench.match import name_tokens
    assert name_tokens("J's Lawn Care") == name_tokens("JS Lawn Care")
