"""BRIEF §5 (Slice E): the backdrop preference ladder — their own video,
a sequence of their own stills, an abstract backdrop generated from the
palette. Licensed stock is not integrated and is never reached by
fabricating a source.
"""

from __future__ import annotations

import pytest

from app.site.backdrop import select_backdrop

pytestmark = pytest.mark.unit


class _Material:
    def __init__(self, images=(), videos=(), photo_vision=None, photos=()):
        self.images = images
        self.videos = videos
        self.photo_labels = {}
        self.photo_vision = photo_vision or {}
        self.photos = photos
        self.trade_kind = "default"

    def size_of(self, url):
        return (1600, 1000)


def test_their_own_video_wins_when_one_exists():
    m = _Material(videos=("https://x/clip.mp4",))
    backdrop = select_backdrop(m)
    assert backdrop.kind == "video"
    assert backdrop.stills == ("https://x/clip.mp4",)


def test_two_or_more_usable_photos_become_a_stills_sequence():
    m = _Material(images=("/a", "/b", "/c"))
    backdrop = select_backdrop(m)
    assert backdrop.kind == "stills"
    assert len(backdrop.stills) >= 2


def test_a_single_photo_is_not_enough_for_a_sequence():
    """One photograph is a hero, not a sequence — the ladder falls to the
    generated rung rather than "cycling" through one image."""
    m = _Material(images=("/only",))
    assert select_backdrop(m).kind == "generated"


def test_a_condemned_photo_never_joins_the_sequence():
    """The same floor `pick_hero` enforces — a backdrop can never show
    what vision already refused to let lead the page."""
    m = _Material(images=("/good1", "/good2", "/bad"),
                  photo_vision={"/bad": {"is_hero_candidate": False}})
    backdrop = select_backdrop(m)
    assert "/bad" not in backdrop.stills


def test_nothing_usable_falls_to_the_generated_backdrop():
    m = _Material(images=())
    assert select_backdrop(m).kind == "generated"


def test_licensed_stock_is_never_fabricated():
    """The bottom rung has no source integrated — reached only in the
    sense that `generated` is always available first, so `stock`/`none`
    is never actually the answer in this codebase today. Documented here
    so a future stock integration has a test to change, not a silent gap."""
    m = _Material(images=())
    assert select_backdrop(m).kind != "stock"
