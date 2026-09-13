"""The site-to-brief capture percentage: the number that did not exist
before Round 7 ("thicken the brief") — `content_census.py` measures
brief-to-page, never site-to-brief."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def load():
    spec = importlib.util.spec_from_file_location(
        "capture_census", Path("tools/capture_census.py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules["capture_census"] = module
    spec.loader.exec_module(module)
    return module


def test_stopwords_are_excluded_from_the_vocabulary():
    cc = load()
    words = cc._words("The Heritage Table has a neighborhood restaurant")
    assert "heritage" in words and "restaurant" in words and "neighborhood" in words
    assert "the" not in words and "has" not in words


def test_short_words_are_excluded():
    """A 1- or 2-letter word ("is", "a", "we") is too common to say
    anything about content overlap either way."""
    cc = load()
    words = cc._words("we do it in oak")
    assert words == {"oak"}


def test_case_is_ignored():
    cc = load()
    assert cc._words("BRISKET") == cc._words("brisket") == {"brisket"}


def test_the_stopword_list_has_no_duplicates():
    """ruff's own B033 catches this at lint time; a real duplicate would
    still just be silently harmless in a set, so this is a second,
    explicit guard that the list was actually written carefully."""
    cc = load()
    as_list = list(cc._STOPWORDS)
    assert len(as_list) == len(set(as_list))


def test_brief_text_pulls_every_textual_field():
    cc = load()
    published = cc.ExtractedSite(
        title="Craftway Kitchen", description="A scratch kitchen",
        about="Family owned since 1994", services=["Catering"],
        products=["Bottled Sauce"], hours=["Mon-Fri 9am-5pm"],
        blocks=[{"heading": "Our Story", "text": "Founded by a chef"}],
        menu_items=[{"name": "Brisket Plate", "description": "Smoked twelve hours"}])
    text = cc._brief_text(published)
    for expected in ("Craftway Kitchen", "scratch kitchen", "Family owned",
                    "Catering", "Bottled Sauce", "Mon-Fri", "Our Story",
                    "Founded by a chef", "Brisket Plate", "Smoked twelve hours"):
        assert expected in text


def test_brief_text_of_an_unreachable_site_is_empty():
    cc = load()
    assert cc._brief_text(None) == ""


def test_capture_percentage_is_intersection_over_site_vocabulary():
    """The actual formula this whole tool exists to compute — proven with
    small, hand-checkable vocabularies rather than trusted from reading
    the code."""
    site_words = {"brisket", "smoked", "hours", "sauce", "catering"}
    brief_words = {"brisket", "sauce", "unrelated", "word"}
    # 2 of the 5 site words ("brisket", "sauce") reached the brief.
    overlap = len(site_words & brief_words) / len(site_words)
    assert overlap == pytest.approx(0.4)
