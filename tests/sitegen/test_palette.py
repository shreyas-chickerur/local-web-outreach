"""§2.2: the palette candidates read off a business's own photographs.

Nothing here re-derives colour from pixels — the vision pass already did
that and validated it (`app.adapters.vision._is_hex`). This proves the
mapping onto the closed accent set, the logo-first ordering, and that it
degrades to nothing rather than fabricating a colour when there is no
vision data to read.
"""

from __future__ import annotations

import pytest

from app.site import palette
from app.site.render import Material
from app.site.theme import ACCENT_NAMES

pytestmark = pytest.mark.unit


def material_with(vision: dict, images: list[str]) -> Material:
    return Material(name="Test", trade="Restaurant", photos=tuple(images),
                    photo_vision=vision)


def test_every_sampled_name_is_a_real_accent():
    """No new kind of value reaches `identity.py` — only names the closed
    enum already validates against."""
    vision = {
        "/photo/1/0": {"dominant_colours": ["#1a5c3a", "#2f7a4f"],
                       "quality": 5, "is_logo_or_badge": False},
        "/photo/1/1": {"dominant_colours": ["#c0392b"],
                       "quality": 4, "is_logo_or_badge": False},
    }
    m = material_with(vision, list(vision))
    names = palette.sample_accents(m, "/photo/1/0")
    assert names
    assert set(names) <= set(ACCENT_NAMES)


def test_no_vision_data_samples_nothing():
    """Degrades cleanly — everything degrades without a key, and a photo
    that was never looked at contributes no colour rather than a guessed
    one."""
    m = material_with({}, ["/photo/1/0", "/photo/1/1"])
    assert palette.sample_accents(m, "/photo/1/0") == []


def test_near_neutral_colours_contribute_nothing():
    """A photograph's own contrast range pads `dominant_colours` with
    near-black and near-white entries. Naming one of those an accent would
    be reading noise as a decision."""
    vision = {"/photo/1/0": {"dominant_colours": ["#1a1a1a", "#f5f5f0",
                                                  "#808080"],
                             "quality": 5, "is_logo_or_badge": False}}
    m = material_with(vision, list(vision))
    assert palette.sample_accents(m, "/photo/1/0") == []


def test_a_logo_photo_is_offered_first():
    """The nearest thing to a declared brand colour this system corroborates.
    A logo's colour should out-rank the hero's when both are read."""
    vision = {
        "/photo/1/0": {"dominant_colours": ["#1e88e5"],  # hero: blue
                       "quality": 5, "is_logo_or_badge": False},
        "/photo/1/1": {"dominant_colours": ["#c0392b"],  # logo: red
                       "quality": 3, "is_logo_or_badge": True},
    }
    m = material_with(vision, list(vision))
    names = palette.sample_accents(m, "/photo/1/0")
    assert names[0] == "red"


def test_grey_and_charcoal_are_never_sampled():
    """`grey`/`charcoal` exist so a THEME can ask for a neutral accent, not
    so a saturated photograph colour has somewhere neutral to fall into —
    hue 0 is shared with `red`, so a warm reddish-brown must not resolve to
    grey purely on hue distance."""
    vision = {"/photo/1/0": {"dominant_colours": ["#8a4a3a"],
                             "quality": 5, "is_logo_or_badge": False}}
    m = material_with(vision, list(vision))
    names = palette.sample_accents(m, "/photo/1/0")
    assert "grey" not in names and "charcoal" not in names


def test_the_corpus_samples_something_for_every_fixture_with_vision():
    """Run against the real corpus rather than a synthetic brief — the vision
    data shipped is what this is actually scored against."""
    import json
    from pathlib import Path

    from app.site.render import material_from_brief, pick_hero

    empty = 0
    for path in sorted(Path("tests/fixtures/briefs").glob("*.json")):
        brief = {**json.loads(path.read_text()), "lead_id": 1}
        material = material_from_brief(brief)
        hero = pick_hero(material.images, 0, material.photo_labels,
                         material.trade_kind, material.size_of,
                         material.photo_vision)
        names = palette.sample_accents(material, hero)
        if not names:
            empty += 1
        else:
            assert set(names) <= set(ACCENT_NAMES)
    # `threadbare` has one condemned photograph; the rest all carry vision.
    assert empty <= 1, f"{empty} fixtures sampled nothing"
