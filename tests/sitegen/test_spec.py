"""Reading intent out of a sentence."""

from __future__ import annotations

import pytest

from app.site.spec import parse_spec

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("text,mood", [
    ("warm and rustic, family feel", "warm"),
    ("clean modern minimal", "fresh"),
    ("bold and punchy", "bold"),
    ("elegant upscale dining", "refined"),
    ("industrial garage look", "industrial"),
    ("dark moody izakaya", "night"),
])
def test_mood_is_read_from_ordinary_words(text, mood):
    assert parse_spec(text).mood == mood


def test_an_empty_spec_still_produces_a_usable_default():
    spec = parse_spec("")
    assert spec.mood == "fresh" and spec.lead_with is None


@pytest.mark.parametrize("text,section", [
    ("put the menu first", "menu"),
    ("lead with the gallery", "gallery"),
    ("photos at the top", "gallery"),
    ("start with the services", "services"),
])
def test_leading_section_is_understood(text, section):
    assert parse_spec(text).lead_with == section


def test_the_call_to_action_is_picked_up():
    assert parse_spec("add a book a table button").cta == "book"
    assert parse_spec("they want people to call").cta == "call"
    assert parse_spec("get a quote form").cta == "quote"


def test_what_landed_is_reported_back():
    spec = parse_spec("warm and rustic, lead with the menu, book a table")
    assert any("warm" in u for u in spec.understood)
    assert any("menu" in u for u in spec.understood)
    assert any("book" in u for u in spec.understood)


def test_words_it_could_not_use_are_named_rather_than_dropped():
    """Half-understanding a sentence in silence is how you end up rebuilding
    the same thing three times."""
    spec = parse_spec("make it feel like a surf shack with hammocks")
    assert "hammocks" in spec.ignored or "surf" in spec.ignored
