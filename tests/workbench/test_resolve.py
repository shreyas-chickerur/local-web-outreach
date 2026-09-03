"""Slice 1a — whatever the user typed becomes name / location / website."""

from __future__ import annotations

import pytest

from app.workbench.resolve import (
    looks_like_url,
    name_from_domain,
    name_from_title,
    resolve_input,
    split_location,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("text,expected", [
    ("https://craftwaykitchen.com", True),
    ("http://x.com/menu", True),
    ("www.craftwaykitchen.com", True),
    ("craftwaykitchen.com", True),
    ("Craftway Kitchen", False),
    ("Craftway Kitchen, Frisco, TX", False),
    ("", False),
])
def test_url_detection(text, expected):
    assert looks_like_url(text) is expected


def test_a_url_input_is_taken_as_the_business_itself():
    r = resolve_input("craftwaykitchen.com")
    assert r.website_url == "https://craftwaykitchen.com"
    assert r.input_was_url is True
    # the domain-derived name is a guess, and says so
    assert any("guessed from the domain" in a for a in r.assumptions)


@pytest.mark.parametrize("text,name,location", [
    ("Craftway Kitchen, Frisco, TX", "Craftway Kitchen", "Frisco, TX"),
    ("Ryno Lawn Care in Frisco, TX", "Ryno Lawn Care", "Frisco, TX"),
    ("Ryno Lawn Care", "Ryno Lawn Care", None),
])
def test_a_trailing_city_is_pulled_out_of_the_name(text, name, location):
    assert split_location(text) == (name, location)
    r = resolve_input(text)
    assert r.name == name and r.location == location and r.input_was_url is False


def test_an_explicit_location_wins_over_one_in_the_text():
    r = resolve_input("Craftway Kitchen, Frisco, TX", location="Plano, TX")
    assert r.location == "Plano, TX"


def test_empty_input_is_rejected():
    with pytest.raises(ValueError):
        resolve_input("   ")


@pytest.mark.parametrize("url,expected", [
    ("https://craftway-kitchen.com", "Craftway Kitchen"),
    ("https://www.rynolawncare.com/", "Rynolawncare"),
])
def test_name_from_domain(url, expected):
    assert name_from_domain(url) == expected


# --- page titles are written for search engines, not for us ------------------
@pytest.mark.parametrize("title,hint,expected", [
    # the real case: the business name is the SECOND segment
    ("Home | The Heritage Table | Downtown Frisco Restaurants",
     "theheritagetable", "The Heritage Table"),
    ("Welcome | Ryno Lawn Care", "rynolawncare", "Ryno Lawn Care"),
    ("Craftway Kitchen", "craftwaykitchen", "Craftway Kitchen"),
    ("Home", "acme", None),              # nothing but boilerplate
    ("", "acme", None),
])
def test_name_from_title(title, hint, expected):
    assert name_from_title(title, domain_hint=hint) == expected


def test_title_without_a_domain_hint_prefers_the_shortest_real_segment():
    title = "Best Neighborhood Restaurant In All Of Frisco Texas | Acme Grill"
    assert name_from_title(title) == "Acme Grill"


@pytest.mark.parametrize("bad", ["", "   ", "\t\n"])
def test_blank_input_is_a_clean_error_not_a_crash(bad):
    """The CLI turns this into a one-line message; it must stay a ValueError."""
    with pytest.raises(ValueError, match="company name or a website URL"):
        resolve_input(bad)
