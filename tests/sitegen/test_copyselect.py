"""BRIEF §5: the model selects and orders the business's own sentences,
never writes one. `select()` returns indices into the exact list handed
in, never retyped text — the by-construction guarantee this whole
feature rests on.
"""

from __future__ import annotations

import pytest

from app.site.copyselect import groups_for, select

pytestmark = pytest.mark.unit


class _Material:
    def __init__(self, about=None, blocks=()):
        self.about = about
        self._blocks = blocks

    def blocks_of(self, kind):
        return tuple(b for b in self._blocks if b.get("kind") == kind)

    @property
    def blocks(self):
        return self._blocks


def test_groups_for_reads_about_and_a_story_block_the_same_way__about():
    material = _Material(about="First sentence. Second sentence. Third one.")
    groups = groups_for(material)
    assert groups["about"] == [
        "First sentence.", "Second sentence.", "Third one."]


def test_a_story_block_outranks_published_about():
    """`_about()` prefers a headed story block outright — the freeze step
    has to offer the same source it will actually render from."""
    material = _Material(about="Never shown.", blocks=[
        {"kind": "story", "heading": "Philosophy",
         "text": "Our story starts here. It continues."}])
    groups = groups_for(material)
    assert groups["about"] == ["Our story starts here.", "It continues."]


def test_feature_blocks_use_the_same_candidates_render_would():
    long_text = " ".join(["This sentence has enough words in it to pass."] * 2)
    material = _Material(blocks=[
        {"kind": "feature", "heading": "A", "text": long_text},
        {"kind": "press", "heading": "B", "text": long_text},
        {"kind": "feature", "heading": "C", "text": "Too short."},
    ])
    groups = groups_for(material)
    assert "feature_0" in groups and "feature_1" in groups
    # The third block is under the 18-word floor `feature_candidates` and
    # `_features()` both enforce — never offered as a group at all.
    assert "feature_2" not in groups


def test_no_key_returns_nothing_to_select(monkeypatch):
    from app.adapters import claude
    monkeypatch.setattr(claude, "available", lambda: False)
    result = select({"about": ["One.", "Two."]})
    assert result == {}


def test_empty_groups_never_call_the_model(monkeypatch):
    from app.adapters import claude

    def _boom(*a, **kw):
        raise AssertionError("should never be called with nothing to select")
    monkeypatch.setattr(claude, "structured", _boom)
    monkeypatch.setattr(claude, "available", lambda: True)
    assert select({}) == {}
    assert select({"about": []}) == {}


def test_an_out_of_range_or_non_integer_index_is_dropped(monkeypatch):
    """The model's answer is data, not trusted structure — an index
    outside the list it was given is dropped rather than crashing the
    build or silently indexing something else."""
    from app.adapters import claude

    monkeypatch.setattr(claude, "available", lambda: True)
    monkeypatch.setattr(claude, "structured",
                        lambda *a, **kw: {"about": [0, 99, "x", 1]})
    result = select({"about": ["First.", "Second."]})
    assert result == {"about": [0, 1]}


def test_a_group_the_model_answers_with_nothing_useful_is_omitted(monkeypatch):
    from app.adapters import claude

    monkeypatch.setattr(claude, "available", lambda: True)
    monkeypatch.setattr(claude, "structured",
                        lambda *a, **kw: {"about": ["not a list"]})
    assert select({"about": ["First."]}) == {}


def test_a_failed_call_returns_nothing_rather_than_raising(monkeypatch):
    from app.adapters import claude

    monkeypatch.setattr(claude, "available", lambda: True)

    def _fail(*a, **kw):
        raise claude.ClaudeError("down")
    monkeypatch.setattr(claude, "structured", _fail)
    assert select({"about": ["First.", "Second."]}) == {}
