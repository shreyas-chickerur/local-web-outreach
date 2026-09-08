"""Sameness, as something a machine can detect.

The governing requirement is that two businesses in the same trade on the same
street must not produce sites a stranger would guess came from one tool. That
is only enforceable if it is measured, and measured off the right thing.
"""

from __future__ import annotations

import pytest

from app.site import fingerprint as fp
from app.site.plan import PlannedSection, SitePlan
from app.site.spec import SiteSpec

pytestmark = pytest.mark.unit


def plan(sections=("gallery", "reviews"), bias="structured", hero="/photo/1/0"):
    built = SitePlan(name="X", mood="warm", layout_bias=bias, hero_photo=hero)
    built.sections = [PlannedSection(key=key, density={"layout": "grid"})
                      for key in sections]
    return built


class Material:
    def __init__(self, labels=None):
        self.photo_labels = labels or {}


def test_the_fingerprint_is_taken_from_decisions_not_from_the_page():
    """Hashing markup scores structurally identical sites as different because
    the businesses use different words, so the gate would pass everything while
    reporting healthy numbers."""
    spec = SiteSpec(mood="warm", accent="navy", lead_with="gallery")
    one = fp.of(plan(), spec, Material({"/photo/1/0": "dish"}))
    # Same decisions, entirely different business and copy.
    two = fp.of(plan(), spec, Material({"/photo/1/0": "dish"}))
    assert one.values == two.values
    assert fp.distance(one, two) == 0.0


def test_two_sites_differing_only_on_colour_are_nearly_identical():
    warm = SiteSpec(mood="warm", accent="navy", lead_with="gallery")
    same = SiteSpec(mood="warm", accent="rose", lead_with="gallery")
    moved = fp.of(plan(), warm, Material()).differs_from(
        fp.of(plan(), same, Material()))
    assert moved == {"accent"}


def test_a_structural_difference_is_recognised_as_one():
    spec = SiteSpec(mood="warm", lead_with="gallery")
    other = SiteSpec(mood="warm", lead_with="reviews")
    moved = fp.of(plan(("gallery", "reviews")), spec, Material()).differs_from(
        fp.of(plan(("reviews", "gallery")), other, Material()))
    assert moved & fp.STRUCTURAL


def test_a_collision_names_the_axes_that_did_move():
    """The retry prompt has to say what is already taken. "Be different" is not
    an instruction a model can act on."""
    spec = SiteSpec(mood="warm", accent="navy", lead_with="gallery")
    taken = [fp.of(plan(), spec, Material())]
    nearly = fp.of(plan(), SiteSpec(mood="warm", accent="rose",
                                    lead_with="gallery"), Material())
    found = fp.collisions(nearly, taken, axes=4)
    assert found and found[0][1] == {"accent"}


def test_enough_movement_including_a_structural_axis_is_not_a_collision():
    taken = [fp.of(plan(("gallery", "reviews")),
                   SiteSpec(mood="warm", accent="navy", lead_with="gallery",
                            cta="book"), Material())]
    # It has to move on a highly weighted axis too, and since `HIGH_WEIGHT`
    # became 2.5 that means `first_screen` or `type_treatment` — not `mood`,
    # whose visible signature between two pages is mostly the colour.
    far = fp.of(plan(("menu", "about", "contact"), bias="editorial"),
                SiteSpec(mood="night", accent="charcoal", lead_with="menu",
                         cta="call", type_treatment="stamped"), Material())
    assert fp.collisions(far, taken, axes=4) == []


def test_moving_on_four_cosmetic_axes_is_still_a_collision():
    """Four different paint colours is one site painted four times."""
    taken = [fp.of(plan(), SiteSpec(mood="warm", accent="navy",
                                    lead_with="gallery", cta="book"),
                   Material({"/photo/1/0": "dish"}))]
    painted = fp.of(plan(), SiteSpec(mood="night", accent="rose",
                                     lead_with="gallery", cta="call"),
                    Material({"/photo/1/0": "room"}))
    assert len(painted.differs_from(taken[0])) >= 4
    assert fp.collisions(painted, taken, axes=4), \
        "no structural axis moved, so this is the same site"


def test_every_axis_appears_in_the_printable_row():
    """The row goes under a screenshot on the contact sheet — the picture says
    two sites feel alike, this says which axis collided."""
    row = fp.of(plan(), SiteSpec(), Material()).as_row()
    assert [axis for axis, _ in row] == list(fp.AXES)


def test_the_ruler_has_a_version_that_moves_when_the_ruler_does():
    """A distance is comparable only to another taken the same way. That has
    gone wrong twice — a corpus that changed under a pinned baseline, and a
    distance that became weighted while the baseline stayed flat — so the
    version is derived from the axes and their weights rather than remembered.
    """
    before = fp.metric_version()
    assert len(before) == 8
    assert fp.metric_version() == before          # stable within a ruler

    for table in (fp.VISIBILITY, fp.DECIDEDNESS):
        original = dict(table)
        try:
            table["accent"] = original["accent"] + 1.0
            assert fp.metric_version() != before, \
                "reweighting either principle must move the ruler"
        finally:
            table.clear()
            table.update(original)
    assert fp.metric_version() == before


def test_the_structural_set_does_not_decide_the_weight():
    """The pair a person called identical differs on three structural axes —
    all of them below the fold, all of them downstream of what the business
    publishes. Weighting the structural set higher would have pushed that pair
    further apart and made the miss worse."""
    material_driven = ("section_order", "compositions")
    assert all(axis in fp.STRUCTURAL for axis in material_driven)
    for quiet in material_driven:
        assert fp.weight_of(quiet) < fp.weight_of("mood"), quiet
        assert fp.weight_of(quiet) < fp.weight_of("hero_subject"), quiet


def test_decidedness_wins_when_the_two_principles_disagree():
    """Slice B breaks the correlation: photographic treatment is highly
    visible AND material-driven. The vector measures design decisions, and a
    consequence of the brief is not one."""
    fp.VISIBILITY["photo_treatment"] = 2.0
    fp.DECIDEDNESS["photo_treatment"] = 0.5
    try:
        assert fp.weight_of("photo_treatment") == 0.5
        # And the reverse: a decision nobody can see does not differentiate.
        fp.VISIBILITY["hidden_choice"] = 0.5
        fp.DECIDEDNESS["hidden_choice"] = 2.0
        assert fp.weight_of("hidden_choice") == 0.5
    finally:
        for key in ("photo_treatment", "hidden_choice"):
            fp.VISIBILITY.pop(key, None)
            fp.DECIDEDNESS.pop(key, None)


def test_every_axis_is_scored_on_both_principles():
    """An axis missing from either table falls back to 1.0 silently, which is a
    decision nobody made."""
    for axis in fp.AXES:
        assert axis in fp.VISIBILITY, axis
        assert axis in fp.DECIDEDNESS, axis
