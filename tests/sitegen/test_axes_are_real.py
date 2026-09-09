"""Every axis in the fingerprint must actually change the page.

Five defects of one shape have now shipped: a dead `rank_for_hero` with six
tests still green against it; a `HERO_PREFERENCE` literal every key of which
was overwritten below it; a suite passing because a real API key was in the
environment; a TLD list that broke its own asymmetry along the customer base;
and `layout_bias`, which declares itself structural and renders nothing above
the fold. Each was something that looked like it was in force and was not.

Catching them one at a time is the wrong strategy, so this is the standing
version: flip one axis, and the page must change. For an axis claimed to be
visible in the first screen, the first 820 pixels must change.

An axis that can be flipped with no visible effect is a lie in the instrument.
It inflates every distance it appears in, which is the specific way a vector
gets louder and less accurate at the same time.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.site import fingerprint as fp
from app.site.architecture import ARRANGEMENTS
from app.site.firstscreen import POSITIONS
from app.site.render import build_from_spec
from app.site.spec import SiteSpec

pytestmark = pytest.mark.unit

FIXTURES = Path("tests/fixtures/briefs")

# The height the fold sheet is cropped to. Above this is what the owner sees
# when the laptop is turned around.
FOLD_PX = 820

BRIEF = {
    "name": "The Heritage Table",
    "trade": "Restaurant",
    "facts": [{"field": "address", "value": "7110 Main St, Frisco, TX",
               "confidence": "verified"},
              {"field": "phone", "value": "(469) 664-0100",
               "confidence": "verified"}],
    "published": {
        "tagline": "A neighbourhood restaurant on Main Street.",
        "about": "A scratch kitchen serving dinner nightly to the neighbourhood.",
        "services": ["Dinner Service", "Online Ordering", "Private Events"],
        "products": [], "hours": ["Mon-Sat 5pm-9pm"],
        "menu_items": [{"name": "Short Rib", "price": "$32"}],
        "menu_media": [], "photos": [f"https://x/{n}.jpg" for n in range(1, 7)],
        "socials": [], "emails": [], "has_locations_page": False, "blocks": [],
    },
    "ratings": [{"source": "google", "value": 4.6, "reviews": 676}],
    "lead_id": 1,
}

# One pair of values per axis, and the spec field that moves it. `section_order`
# and `compositions` are consequences of the material rather than fields, so
# they are exercised through the field that reorders them.
FLIPS: dict[str, tuple[str, object, object]] = {
    "first_screen": ("first_screen", "photo", "proof"),
    "type_treatment": ("type_treatment", "quiet", "wide"),
    "architecture": ("architecture", "stacked", "ledger"),
    "signature": ("signature", "none", "ledger"),
    "mood": ("mood", "warm", "night"),
    "accent": ("accent", "navy", "gold"),
    "leads_with": ("lead_with", "gallery", "reviews"),
    "section_order": ("lead_with", "gallery", "hours"),
    "compositions": ("suppress", [], ["services"]),
    "action": ("cta", "book", "call"),
    "hero_subject": ("hero_offset", 0, 1),
}

# Axes whose difference is claimed to show in the first screen. An axis here
# that only changes the page on scroll is scored as if the owner sees it and
# does not.
FIRST_SCREEN = {"first_screen", "type_treatment", "mood", "accent",
                "hero_subject", "action"}


def render(**kw) -> str:
    return build_from_spec(BRIEF, SiteSpec(**kw))


def above_the_fold(page: str) -> str:
    """Everything the browser paints in the first screen.

    Approximated by the document up to the end of the hero, which is what
    occupies it — the fold sheet crops at 820px and the hero is taller than
    that at every width we render.
    """
    end = page.find("</header>")
    return page[:end] if end > 0 else page


@pytest.mark.parametrize("axis", sorted(FLIPS))
def test_changing_one_axis_changes_the_page(axis):
    field, one, two = FLIPS[axis]
    assert render(**{field: one}) != render(**{field: two}), (
        f"{axis} can be flipped with no effect on the rendered page — it "
        f"inflates every distance it appears in")


@pytest.mark.parametrize("axis", sorted(FIRST_SCREEN))
def test_a_first_screen_axis_changes_the_first_screen(axis):
    field, one, two = FLIPS[axis]
    assert above_the_fold(render(**{field: one})) != \
        above_the_fold(render(**{field: two})), (
        f"{axis} is weighted as visible in the first screen and is not")


def test_every_first_screen_position_renders_a_different_first_screen():
    """Five declared positions, and two of them were the same page.

    `photo` and `facts` differed above the fold by the class attribute and
    nothing else — the CSS then centred the block, shrank the heading and
    spaced the figures out, which is a setting applied to the same arrangement.
    Side by side, `barbecue` and `contractor-bare` were one page.

    `test_a_first_screen_axis_changes_the_first_screen` passed it, because a
    class name is markup. This strips the class attribute before comparing, so
    a position has to earn its difference in what is rendered rather than in
    what it is called.

    This is `layout_bias` in the axis weighted heaviest — see `BRIEF` §3. Every
    distance across a colliding pair of positions was overstated by a quarter.
    """
    import itertools
    import re

    def fold(position: str) -> str:
        page = above_the_fold(render(first_screen=position))
        return re.sub(r'class="[^"]*"', 'class=""', page)

    same = [(one, two) for one, two in itertools.combinations(POSITIONS, 2)
            if fold(one) == fold(two)]
    assert not same, (
        f"these first-screen positions render an identical first screen once "
        f"the class attribute is taken out of it: {same}. Give them "
        f"above-the-fold consequence or drop the axis's weight — BRIEF §3.")


def test_every_architecture_renders_a_different_page():
    """The same check `photo`/`facts` failed, applied to this axis on purpose.

    Two positions that differ only by what they are called is a defect this
    project shipped once, in the axis weighted heaviest, for two commits. So
    the class attribute comes out before comparing here too — an arrangement
    has to be legible in what the page says, not in the hook it hangs on.

    Whole page rather than the first screen: this axis is deliberately below
    the fold, and `test_the_hero_is_untouched_by_the_arrangement` holds that.
    """
    import itertools
    import re

    def page(arrangement: str) -> str:
        return re.sub(r'class="[^"]*"', 'class=""',
                      render(architecture=arrangement))

    same = [(one, two) for one, two in itertools.combinations(ARRANGEMENTS, 2)
            if page(one) == page(two)]
    assert not same, (
        f"these arrangements render an identical page once the class "
        f"attribute is taken out of it: {same}")


def test_the_hero_is_untouched_by_the_arrangement():
    """Axis three must not reach into axis one's decision.

    One decision, one axis — and if the arrangement moved the first screen it
    would be competing with `first_screen` for the same difference, which is
    how `layout_bias` came to be a function of `mood`.
    """
    def header(page: str) -> str:
        # From inside <body>: the stylesheet carries a comment mentioning
        # "<header>", and searching the whole document found that instead.
        body = page.index("<body")
        start = page.index("<header", body)
        return page[start:page.index("</header>", start)]

    folds = {header(render(architecture=a)) for a in ARRANGEMENTS}
    assert len(folds) == 1, (
        "an arrangement changed the first screen, which belongs to axis one")


def test_every_available_device_renders_something_different():
    """One mark per site, and no two marks the same band under another name.

    Only the devices this brief can carry: a device chosen for a business
    without the material renders nothing, which is correct and would make it
    identical to `none`. `available()` is the constraint and this checks what
    it offers.

    Class attribute stripped, for the reason `photo`/`facts` made necessary.
    """
    import itertools
    import re

    from app.site.render import material_from_brief
    from app.site.signature import available

    offered = available(material_from_brief({**BRIEF, "lead_id": 1}), 6)
    assert len(offered) >= 8, offered

    def page(device: str) -> str:
        return re.sub(r'class="[^"]*"', 'class=""', render(signature=device))

    same = [(one, two) for one, two in itertools.combinations(offered, 2)
            if page(one) == page(two)]
    assert not same, f"these devices render the same page: {same}"


def test_the_device_never_reaches_the_first_screen():
    """§2.3: a hero treatment is not a device, it is a position on axis one."""
    from app.site.signature import DEVICES

    def header(page: str) -> str:
        body = page.index("<body")
        start = page.index("<header", body)
        return page[start:page.index("</header>", start)]

    assert len({header(render(signature=d)) for d in DEVICES}) == 1


def test_no_axis_is_a_function_of_another():
    """One decision, one axis.

    `layout_bias` was in this vector and is a pure function of `mood` — six
    moods onto four biases, nothing else able to set it. It could never differ
    when mood matched, and whenever mood crossed a bias boundary it counted the
    same decision twice, inflating the distance for free.

    Swept across the fixture corpus rather than one brief, because that is the
    space the vector actually compares: different businesses. Within a single
    brief `section_order` IS determined by `leads_with` — which is exactly why
    its decidedness is scored low — but across businesses the material moves it
    independently, and that is the difference the vector has to be able to see.
    """
    import json

    from app.site.render import material_from_brief, plan_for

    briefs = [json.loads(path.read_text())
              for path in sorted(FIXTURES.glob("*.json"))]
    assert len(briefs) >= 6, "too few businesses to tell correlation apart"

    # A cross product, so no two axes are confounded by the sweep itself —
    # pairing each mood with its own accent would "prove" mood is a function of
    # accent, which says nothing about the code.
    specs = [SiteSpec(mood=mood, accent=accent, lead_with=lead, cta=cta,
                      first_screen=screen, type_treatment=treatment,
                      architecture=arch, signature=mark)
             for mood in ("warm", "night", "fresh")
             for accent in (None, "navy", "gold")
             for lead in (None, "reviews")
             for cta in ("book", "call")
             for screen in ("photo", "proof")
             for treatment in ("quiet", "stamped")
             for arch in ("stacked", "ledger")
             for mark in ("none", "ticker")]

    subjects = ("dish", "room", "people", "exterior", "work")
    rows: list[fp.Fingerprint] = []
    for index, brief in enumerate(briefs, start=1):
        loaded = {**brief, "lead_id": index}
        # Photo labels live in the database, not in a frozen brief, so without
        # this `hero_subject` is constant across the sweep — and a constant
        # axis looks like a function of every other one.
        material = material_from_brief(loaded)
        loaded["photo_labels"] = {
            url: subjects[(index + n) % len(subjects)]
            for n, url in enumerate(material.images)}
        material = material_from_brief(loaded)
        rows.extend(fp.of(plan_for(loaded, spec), spec, material)
                    for spec in specs)

    for axis in fp.AXES:
        values = {row.values[axis] for row in rows}
        assert len(values) > 1, (
            f"{axis} never varies across the corpus — it contributes nothing "
            f"to any distance and inflates the denominator")

    for one in fp.AXES:
        for two in fp.AXES:
            if one == two:
                continue
            pairs = {(row.values[two], row.values[one]) for row in rows}
            keys = {key for key, _ in pairs}
            assert len(pairs) > len(keys), (
                f"{one} is a function of {two} across the corpus — it can "
                f"never differ when {two} matches, so it counts the same "
                f"decision twice")


def test_every_axis_in_the_vector_is_covered_here():
    """A new axis must arrive with a flip, or it is scored without ever being
    checked — which is exactly how layout_bias got in."""
    assert set(FLIPS) == set(fp.AXES), set(fp.AXES) ^ set(FLIPS)


def test_every_axis_claimed_visible_is_declared_first_screen():
    """The two lists have to agree, or an axis can be weighted for visibility
    without anything asserting it has any."""
    weighted_visible = {axis for axis in fp.AXES
                        if fp.VISIBILITY.get(axis, 1.0) > 1.0}
    assert weighted_visible <= FIRST_SCREEN, weighted_visible - FIRST_SCREEN
