"""Generating a site from a brief.

The governing rule is the one from the requirements: **no unverified fact
ships**. The site is shown to the owner, so one sentence they know to be false
ends the meeting — a fabricated "serving the neighbourhood since 1994" is worse
than a plain page. Most of what is pinned here is that rule.
"""

from __future__ import annotations

import re

import pytest

from app.site.render import build, material_from_brief, unsupported

pytestmark = pytest.mark.unit


def _brief(**kw) -> dict:
    base = {
        "name": "The Heritage Table",
        "facts": [
            {"field": "address", "value": "7110 Main St, Frisco, TX",
             "confidence": "verified"},
            {"field": "phone", "value": "(469) 664-0100", "confidence": "verified"},
        ],
        "published": {
            "tagline": "A neighbourhood restaurant on Main Street.",
            "about": "Scratch kitchen serving dinner nightly.",
            "services": ["Dinner Service", "Online Ordering"],
            "products": [],
            "hours": ["Mon-Sat 5pm-9pm"],
            "menu_items": [{"name": "Short Rib", "price": "$32",
                            "description": "braised eight hours"}],
            "menu_media": [], "photos": ["https://x/1.jpg", "https://x/2.jpg",
                                         "https://x/3.jpg"],
            "socials": [{"name": "Instagram", "url": "https://instagram.com/x"}],
            "emails": [], "has_locations_page": False,
        },
        "ratings": [{"source": "google", "value": 4.6, "reviews": 676}],
    }
    return {**base, **kw}


def test_nothing_reaches_the_page_that_was_not_established():
    page, _ = build(_brief())
    assert unsupported(page, material_from_brief(_brief())) == []


def test_an_uncorroborated_fact_is_left_off():
    """A phone number one directory guessed is exactly the kind that is wrong,
    and a wrong number on a demo site ends the meeting."""
    brief = _brief(facts=[{"field": "phone", "value": "(000) 000-0000",
                           "confidence": "unverified"}])
    page, _ = build(brief)
    assert "000-0000" not in page


def test_what_you_confirmed_yourself_does_ship():
    brief = _brief(facts=[{"field": "phone", "value": "(469) 111-2222",
                           "confidence": "operator_verified"}])
    page, _ = build(brief)
    assert "(469) 111-2222" in page


def test_a_section_with_no_data_is_absent_not_empty():
    """A placeholder heading reads as a claim that there is nothing there."""
    thin = _brief(published={**_brief()["published"], "menu_items": [],
                             "photos": [], "about": None})
    page, _ = build(thin)
    for missing in ('id="menu"', 'id="gallery"', 'id="about"'):
        assert missing not in page
    assert 'id="contact"' in page          # address and phone are still known


def test_the_spec_changes_the_result():
    warm, _ = build(_brief(), "warm and rustic")
    night, _ = build(_brief(), "dark moody bar")
    assert warm != night


def test_asking_to_lead_with_a_section_moves_it_up():
    page, spec = build(_brief(), "put the gallery first")
    assert spec.lead_with == "gallery"
    assert page.index('id="gallery"') < page.index('id="services"')


def test_an_instruction_that_cannot_be_honoured_is_reported():
    """Silently dropping it leaves you thinking it was applied."""
    no_menu = _brief(published={**_brief()["published"], "menu_items": []})
    _, spec = build(no_menu, "lead with the menu")
    assert any("no menu section" in note for note in spec.unmet)


def test_generation_is_deterministic():
    """The same brief and the same words give the same page, so a difference
    between two versions is always something you asked for."""
    first, _ = build(_brief(), "warm, book a table")
    second, _ = build(_brief(), "warm, book a table")
    assert first == second


def test_content_is_escaped():
    nasty = _brief(name='Bob\'s "Diner" <script>alert(1)</script>')
    page, _ = build(nasty)
    assert "<script>alert(1)</script>" not in page
    assert "&lt;script&gt;" in page


def test_the_call_to_action_is_wired_to_something_real():
    page, _ = build(_brief(), "call us")
    assert 'href="tel:4696640100"' in page

    # With no phone, it must not render a dead button.
    no_phone = _brief(facts=[{"field": "address", "value": "7110 Main St, Frisco, TX",
                              "confidence": "verified"}])
    page2, _ = build(no_phone)
    assert "tel:" not in page2
    assert "google.com/maps" in page2


def test_the_guard_catches_a_fabricated_claim():
    """If a future section starts inventing, this is what fails."""
    material = material_from_brief(_brief())
    invented = "<html><body><p>Family-run since 1994, award-winning</p></body></html>"
    found = unsupported(invented, material)
    assert "since 1994" in found and "award-winning" in found


def test_a_claim_the_business_makes_itself_is_allowed():
    """Their own words are theirs to make. We just must not add any."""
    brief = _brief(published={**_brief()["published"],
                              "about": "Family-run since 1994."})
    page, _ = build(brief)
    assert unsupported(page, material_from_brief(brief)) == []


def test_the_page_is_responsive_and_titled():
    page, _ = build(_brief())
    assert 'name="viewport"' in page
    assert "<title>The Heritage Table</title>" in page
    assert "@media" in page


def test_every_theme_renders():
    for mood in ("warm", "fresh", "bold", "refined", "industrial", "night"):
        page, spec = build(_brief(), mood)
        assert spec.mood == mood
        assert re.search(r"--accent:#[0-9a-f]{6}", page)
