"""Content volume as an explicit input to layout.

The bug this exists to prevent: `repeat(auto-fit, minmax(260px, 1fr))` collapses
its empty tracks, so a business with two services gets two half-width slabs and
a gutter of dead space — which is what a template looks like when it is fed too
little. Volume now picks the composition instead of being absorbed by it.
"""

from __future__ import annotations

import pytest

from app.site.density import (
    MODIFIERS,
    calculate_density_signal,
    density_attrs,
    profile_for,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("count,profile", [
    (0, "empty"), (1, "sparse"), (2, "sparse"),
    (3, "balanced"), (4, "dense"), (12, "dense"),
])
def test_the_bands(count, profile):
    assert profile_for(count) == profile
    assert calculate_density_signal(["x"] * count)["profile"] == profile


def test_each_profile_gets_its_own_composition():
    """Not the same grid with different numbers in it."""
    layouts = {calculate_density_signal(["x"] * n)["layout"] for n in (1, 3, 5)}
    assert layouts == {"editorial", "feature", "grid"}


def test_the_scale_runs_inversely_to_volume():
    """Sparse copy has to carry the section alone, so it is set larger; a long
    list is read as a list and wants to be quieter."""
    sparse = calculate_density_signal(["x"])["modifier"]
    balanced = calculate_density_signal(["x"] * 3)["modifier"]
    dense = calculate_density_signal(["x"] * 9)["modifier"]
    assert sparse > balanced > dense
    assert MODIFIERS["balanced"] == 1.0          # the untouched middle


def test_nothing_renders_from_nothing():
    """The data-safety rule outranks the layout rule."""
    signal = calculate_density_signal([])
    assert signal["renders"] is False
    assert signal["layout"] == "none"


def test_it_measures_what_is_being_laid_out():
    """Takes the collection, not a count, so a caller cannot disagree with
    itself about what was counted."""
    items = ["a", "b", "c", "d"]
    assert calculate_density_signal(items)["count"] == len(items)


def test_the_signal_is_a_pure_function_of_the_collection():
    """The generator's determinism depends on this: same content, same page."""
    first = calculate_density_signal(["a", "b"])
    second = calculate_density_signal(["a", "b"])
    assert first == second


def test_the_attributes_carry_both_hooks():
    """One selects the layout, the other scales the type; the stylesheet needs
    both and neither belongs in a class name."""
    attrs = density_attrs(calculate_density_signal(["x", "y"]))
    assert 'data-density="sparse"' in attrs
    assert "--density-scale:1.25" in attrs


def test_the_scale_is_written_without_float_noise():
    """`--density-scale:1` beats `1.0`, and nothing downstream should ever see
    `0.8500000000000001`."""
    balanced = density_attrs(calculate_density_signal(["a", "b", "c"]))
    assert balanced.endswith('--density-scale:1"')
    assert density_attrs(calculate_density_signal(["a"] * 5)).endswith(
        '--density-scale:0.85"')
