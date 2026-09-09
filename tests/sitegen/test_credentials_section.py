"""BRIEF §5's contractor sections — the credentials band.

Only facts `contractorfacts.found()` actually matched against the business's
own text ever reach the page; a trade nothing is hunted for, or one with
nothing found, gets no section at all. Two compositions by count: one or two
facts sit as a quiet row of pills, three or four earn a card grid.
"""

from __future__ import annotations

import pytest

from app.site.render import build, material_from_brief, unsupported

pytestmark = pytest.mark.unit


def _plumber(about: str = "", **kw) -> dict:
    base = {
        "name": "Legacy Plumbing Frisco",
        "trade": "Plumber",
        "facts": [{"field": "phone", "value": "(469) 664-0100",
                   "confidence": "verified"}],
        "published": {
            "tagline": "Frisco's own plumbing experts.",
            "about": about,
            "services": ["Drain Cleaning", "Water Heaters", "Leak Repair"],
            "products": [], "hours": ["Mon-Fri 8am-5pm"],
            "menu_items": [], "menu_media": [],
            "photos": [f"https://x/{n}.jpg" for n in range(1, 5)],
            "socials": [], "emails": [], "has_locations_page": False,
            "blocks": [],
        },
        "ratings": [{"source": "google", "value": 4.8, "reviews": 340}],
    }
    return {**base, **kw}


def test_no_section_when_nothing_is_found():
    page, _ = build(_plumber(about="We are Frisco's trusted plumbing team."))
    assert 'id="credentials"' not in page


def test_a_section_appears_when_a_fact_is_corroborated():
    page, _ = build(_plumber(
        about="Licensed and insured technicians on every call."))
    assert 'id="credentials"' in page
    assert "Licensed &amp; insured" in page


def test_one_or_two_facts_render_as_a_quiet_row_of_pills():
    page, _ = build(_plumber(
        about="Licensed and insured, with a 5-year workmanship warranty."))
    section = page[page.index('id="credentials"'):]
    section = section[:section.index("</section>")]
    assert '<div class="stamps">' in section
    assert section.count("<span>") == 2


def test_three_or_four_facts_render_as_a_card_grid():
    page, _ = build(_plumber(
        about="Licensed and insured. Free estimate on every job. Ask about "
              "our workmanship warranty. We answer 24/7 emergency calls."))
    section = page[page.index('id="credentials"'):]
    section = section[:section.index("</section>")]
    assert '<div class="offers">' in section
    assert section.count('class="offer"') == 4


def test_a_trade_this_generator_does_not_hunt_gets_no_section_either_way():
    """A dentist's own page might well say "licensed" somewhere and must not
    grow a contractor section it was never asked to carry — widening the
    hunt to another trade is `tradeprofile.FACT_HUNTS`'s decision, not an
    accident of a phrase happening to appear."""
    dentist = _plumber(
        trade="Dentist",
        about="Our licensed and insured dental team offers a free estimate "
              "for every new patient, backed by our service warranty.")
    page, _ = build(dentist)
    assert 'id="credentials"' not in page


def test_a_credential_found_in_a_block_rather_than_about_still_renders():
    """`about` is not the only place a business's own words live — the raw
    scraped `blocks` carry real published text too, and a fact found there is
    exactly as corroborated as one found in `about`."""
    brief = _plumber(about="Frisco's own plumbing experts, done right.")
    brief["published"]["blocks"] = [
        {"kind": "feature", "heading": "Our Guarantee",
         "text": "24/7 emergency service, every day of the year.",
         "images": [], "entries": []}]
    page, _ = build(brief)
    assert 'id="credentials"' in page
    assert "24/7 emergency service" in page


def test_the_credentials_band_never_trips_the_content_gate():
    """The negative case only means something because `unsupported()` still
    catches a genuine fabrication elsewhere — see
    `test_the_guard_catches_a_fabricated_claim` in `test_render.py`, which
    this section does not touch or weaken."""
    brief = _plumber(
        about="Licensed and insured. Free estimate on every job. Ask about "
              "our workmanship warranty. We answer 24/7 emergency calls.")
    page, _ = build(brief)
    assert unsupported(page, material_from_brief(brief)) == []
