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
