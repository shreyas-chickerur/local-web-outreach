"""The first-screen contract, and proof that each position is really different.

The first axis, first because two pages identical above the fold are the same
site to the owner being shown them. Eleven fixtures currently open the same way
— a photograph behind white type flush left — and the two the fingerprint calls
closest are two law firms a stranger would not tell apart.

An axis that can be flipped with no visible effect is a lie in the instrument,
so every position here is asserted to change the first 820 pixels before the
axis is allowed into the vector.
"""

from __future__ import annotations

import re

import pytest

from app.site import firstscreen
from app.site.render import Material, build_from_spec
from app.site.spec import SiteSpec

pytestmark = pytest.mark.unit

SIZES = {f"https://x/{n}.jpg": (2400, 1350) for n in range(1, 7)}

BRIEF = {
    "name": "The Heritage Table",
    "trade": "Restaurant",
    "facts": [{"field": "address", "value": "7110 Main St, Frisco, TX 75033",
               "confidence": "verified"},
              {"field": "phone", "value": "(469) 664-0100",
               "confidence": "verified"}],
    "published": {"tagline": "A neighbourhood restaurant on Main Street.",
                  "about": "A scratch kitchen serving dinner nightly.",
                  "services": ["Dinner Service"], "hours": ["Mon-Sat 5pm-9pm"],
                  "menu_items": [], "menu_media": [], "photos": list(SIZES),
                  "socials": [], "emails": [], "blocks": [], "products": [],
                  "has_locations_page": False},
    "ratings": [{"source": "google", "value": 4.6, "reviews": 676}],
    "lead_id": 1,
    "photo_sizes": {url: list(size) for url, size in SIZES.items()},
}


def first_screen(position: str) -> str:
    """The hero band itself.

    From `<header` to `</header>`, not from the top of the document — the
    stylesheet sits above it and mentions every class, so slicing from the
    start finds `bgimg` in the CSS whether or not the page renders one.
    """
    return band(build_from_spec(BRIEF, SiteSpec(first_screen=position)))


def band(page: str) -> str:
    """The hero element.

    Matched on `<header class="hero`, not on `<header` — the stylesheet above
    it contains the word inside a comment, and a substring search finds that
    instead.
    """
    start = page.find('<header class="hero')
    end = page.find("</header>", start)
    assert start > 0 and end > start, "no hero rendered"
    return page[start:end]


@pytest.mark.parametrize("position", firstscreen.POSITIONS)
def test_every_position_renders(position):
    assert f"first-{position}" in first_screen(position)


def test_no_two_positions_open_the_same_way():
    """The whole axis. If two of these are byte-identical above the fold, the
    vector counts a difference nobody can see."""
    screens = {p: first_screen(p) for p in firstscreen.POSITIONS}
    for one in firstscreen.POSITIONS:
        for two in firstscreen.POSITIONS:
            if one < two:
                assert screens[one] != screens[two], (one, two)


def test_type_leads_with_no_photograph_at_all():
    """Not a photographic hero with a missing image — a page composed for type,
    which is what a business whose pictures were all condemned should get."""
    screen = first_screen("type")
    assert "bgimg" not in screen
    assert "has-photo" not in screen


def test_split_sets_nothing_over_the_picture():
    """Type and photograph each take half, so there is nothing to veil."""
    screen = first_screen("split")
    assert "bgimg" in screen
    assert "veil" not in screen


def test_proof_leads_with_what_a_visitor_checks():
    screen = first_screen("proof")
    assert "<ul class=\"proof\"" in screen
    assert "676 reviews" in screen or "676" in screen


def test_facts_leads_with_the_numbers_not_a_paragraph():
    screen = first_screen("facts")
    assert 'class="facts"' in screen
    assert "676" in screen


def test_a_position_needing_a_photograph_falls_back_rather_than_framing_nothing():
    """The floor can take the hero away after the position was chosen — a
    business whose only picture was condemned must not get an empty frame."""
    bare = {**BRIEF, "published": {**BRIEF["published"], "photos": []},
            "place_photos": [], "photo_sizes": {}}
    for position in ("photo", "split"):
        assert f"first-{position}" not in band(
            build_from_spec(bare, SiteSpec(first_screen=position)))


def test_only_positions_the_material_supports_are_offered():
    """A position that cannot be built is not a choice, it is a broken page."""
    from app.site.render import material_from_brief

    rich = material_from_brief(BRIEF)
    assert set(firstscreen.available(rich, "https://x/1.jpg")) == \
        set(firstscreen.POSITIONS)

    nothing = Material(name="S.Handyman")
    assert firstscreen.available(nothing, None) == ["type"]


def test_every_position_has_styling_of_its_own():
    """A position with no rules renders as the default and the axis is a lie."""
    from app.site.styles import css
    from app.site.theme import THEMES

    sheet = css(THEMES["warm"])
    for position in firstscreen.POSITIONS:
        if position == "photo":
            continue          # the base .hero rules are its styling
        assert f"first-{position}" in sheet, position


def test_the_positions_are_the_ones_the_brief_names():
    assert firstscreen.POSITIONS == ("photo", "type", "split", "facts", "proof")


def test_the_first_screen_survives_a_round_trip_through_the_spec():
    """It has to reach the renderer from a stored spec, or a rebuilt version
    silently reverts to the default."""
    from app.site.pipeline import spec_from_config

    assert spec_from_config({"first_screen": "proof"}).first_screen == "proof"
    assert spec_from_config({}).first_screen == "photo"


def test_the_scroll_cue_only_appears_when_there_is_a_photograph_to_scroll_past():
    assert "scrollcue" not in first_screen("type")
    assert "scrollcue" in first_screen("photo")


def test_the_hero_band_is_never_a_full_viewport_that_pushes_the_page_out():
    """A forbidden default in the brief: a hero sized to the whole viewport
    leaves nothing of the actual page in the first screen."""
    from app.site.styles import css
    from app.site.theme import THEMES

    sheet = css(THEMES["warm"])
    for match in re.findall(r"min-height:min\((\d+)vh", sheet):
        assert int(match) <= 94, f"{match}vh hero pushes the page out"
