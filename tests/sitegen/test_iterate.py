"""Turning a sentence into changes to a site's configuration."""

from __future__ import annotations

import pytest

from app.site.iterate import DEFAULT_SPEC, parse_iteration_instruction

pytestmark = pytest.mark.unit


def parse(sentence: str, spec: dict | None = None) -> dict:
    return parse_iteration_instruction(sentence, spec or dict(DEFAULT_SPEC))


# ------------------------------------------------------------- moods ------ #
@pytest.mark.parametrize("sentence,mood", [
    ("make it rustic", "warm"), ("more minimal please", "fresh"),
    ("go bold", "bold"), ("something upscale", "refined"),
    ("industrial look", "industrial"), ("dark and moody", "night"),
])
def test_synonyms_map_to_the_core_moods(sentence, mood):
    assert parse(sentence)["mood"] == mood


def test_a_conflicting_sentence_takes_the_first_and_says_so():
    """Silent last-wins is the trap; refusing to act is no better."""
    result = parse("make it warm but clean")
    assert result["mood"] == "warm"
    assert result["contradictions"]
    assert "clean" in result["contradictions"][0]
    assert "fresh" in result["contradictions"][0]


def test_two_words_for_the_same_mood_are_not_a_conflict():
    assert parse("warm and rustic")["contradictions"] == []


# --------------------------------------------------------- re-ordering ---- #
@pytest.mark.parametrize("sentence", [
    "lead with the gallery", "put the gallery first", "move the gallery to the top",
    "start with the gallery", "gallery at the top",
])
def test_hoisting_is_understood_however_it_is_phrased(sentence):
    assert parse(sentence)["lead_with"] == "gallery"


@pytest.mark.parametrize("sentence", [
    "remove the reviews", "drop the reviews", "hide the reviews",
    "lose the reviews", "no reviews",
])
def test_dropping_a_section_is_understood(sentence):
    assert parse(sentence)["suppress"] == ["reviews"]


def test_the_verb_decides_not_the_noun():
    """"Move the gallery up" and "remove the gallery" name the same section."""
    assert parse("move the gallery up")["lead_with"] == "gallery"
    assert parse("remove the gallery")["suppress"] == ["gallery"]
    assert parse("remove the gallery")["lead_with"] is None


def test_mentioning_a_section_without_a_verb_emphasises_it():
    assert parse("more about the menu")["emphasis"] == ["menu"]


def test_a_later_instruction_can_undo_an_earlier_one():
    dropped = parse("remove the gallery")
    restored = parse("bring back the gallery first", dropped)
    assert restored["suppress"] == []
    assert restored["lead_with"] == "gallery"


# ---------------------------------------------------------------- CTA ----- #
def test_the_call_to_action_carries_its_label():
    cta = parse("add a book a table button")["cta"]
    assert cta == {"kind": "book", "label": "Book a table"}


def test_the_longer_phrase_wins():
    """"book a table" must beat "book", or the label is wrong."""
    assert parse("book a table")["cta"]["label"] == "Book a table"
    assert parse("let them book")["cta"]["label"] == "Book now"


# ------------------------------------------------------------- deltas ---- #
def test_an_iteration_only_changes_what_it_mentions():
    first = parse("warm and rustic, lead with the gallery, book a table")
    second = parse("actually make it darker", first)
    assert second["mood"] == "night"
    assert second["lead_with"] == "gallery"          # carried forward
    assert second["cta"]["kind"] == "book"           # carried forward


def test_the_current_spec_is_never_mutated():
    """A stored version's configuration has to stay what produced it."""
    original = dict(DEFAULT_SPEC)
    original["emphasis"] = ["menu"]
    snapshot = dict(original)
    snapshot["emphasis"] = list(original["emphasis"])
    parse("lead with the gallery and remove the reviews", original)
    assert original == snapshot


# ------------------------------------------------------- ignored tokens --- #
def test_words_it_could_not_use_are_named():
    result = parse("make it feel like a surf shack with hammocks")
    assert "hammocks" in result["ignored_tokens"]
    assert "surf" in result["ignored_tokens"]


def test_words_it_acted_on_are_not_reported_as_ignored():
    """Reporting "remove" as unused after honouring it is worse than silence."""
    result = parse("remove the reviews and move the menu to the top")
    assert result["ignored_tokens"] == []


def test_grammar_is_not_reported_as_ignored():
    assert parse("please make the site a bit more modern")["ignored_tokens"] == []


def test_the_ignored_list_is_ordered_so_output_is_stable():
    result = parse("zebra hammock antelope")
    assert result["ignored_tokens"] == sorted(result["ignored_tokens"])


# -------------------------------------------------------- determinism ---- #
def test_the_same_sentence_gives_the_same_configuration():
    """The generator's guarantee depends on this being a pure function."""
    a = parse("warm and rustic, lead with gallery, book a table")
    b = parse("warm and rustic, lead with gallery, book a table")
    assert a == b


def test_an_empty_sentence_changes_nothing():
    before = parse("warm, lead with the menu")
    after = parse("", before)
    assert after["mood"] == before["mood"]
    assert after["lead_with"] == before["lead_with"]


def test_the_lead_photograph_can_be_cycled_and_reset():
    """A label is a more precise instruction than "show me another one", so
    there has to be a way back to the top of the ranking."""
    spec = parse("different hero photo")
    assert spec["hero_offset"] == 1
    spec = parse("another hero photo", spec)
    assert spec["hero_offset"] == 2
    spec = parse("use the first hero photo", spec)
    assert spec["hero_offset"] == 0
