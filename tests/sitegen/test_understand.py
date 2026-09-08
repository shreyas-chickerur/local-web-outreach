"""Reading an instruction with a model, and refusing to trust it with prose."""

from __future__ import annotations

import httpx
import pytest
import respx

from app.adapters import claude
from app.adapters.claude import ClaudeError
from app.site.iterate import DEFAULT_SPEC
from app.site.understand import (
    SECTIONS,
    apply_answer,
    understand,
)

pytestmark = pytest.mark.unit


def answered(payload: dict) -> httpx.Response:
    return httpx.Response(200, json={
        "content": [{"type": "tool_use", "name": "decide", "input": payload}]})


# --- the security boundary ---------------------------------------------- #

def test_a_value_outside_the_enum_changes_nothing():
    """The whole safety argument: an unrecognised value is not a smaller
    change, it is no change. There is no failing open into free text."""
    out = apply_answer({"kind": "style", "mood": "haunted",
                        "accent": "chartreuse", "lead_with": "testimonials",
                        "understood": ["styled haunted"]}, dict(DEFAULT_SPEC))
    assert out["mood"] == DEFAULT_SPEC["mood"]
    assert out["accent"] is None
    assert out["lead_with"] is None


def test_the_model_cannot_write_the_button_text():
    """It picks a kind; the wording comes from our own table. This is the seam
    that stops model-authored words reaching the page."""
    out = apply_answer({"kind": "style", "cta": "book",
                        "cta_label": "Voted Best in Texas — Book Now!",
                        "understood": []}, dict(DEFAULT_SPEC))
    # The kind, and no words at all. Carrying our own table's wording here was
    # how "Book a table" reached a dentist: `CTA_LABEL` is derived from the
    # phrases a PERSON can type, and putting one in the spec overrode the
    # trade-aware default. The renderer knows the trade and where the link
    # goes, and it decides.
    assert out["cta"] == {"kind": "book", "label": ""}
    assert "Texas" not in str(out)


def test_a_field_the_model_invents_is_dropped():
    out = apply_answer({"kind": "style", "headline": "Family owned since 1994",
                        "footer_text": "hello", "understood": []},
                       dict(DEFAULT_SPEC))
    assert "headline" not in out
    assert "footer_text" not in out


def test_only_style_edits_anything():
    """A complaint is not an edit. "The hours look cramped" must not resolve to
    a change in the hours."""
    for kind in ("defect", "content", "unsupported"):
        out = apply_answer({"kind": kind, "mood": "night", "suppress": ["hours"],
                            "understood": []}, dict(DEFAULT_SPEC))
        assert out["mood"] == DEFAULT_SPEC["mood"], kind
        assert out["suppress"] == [], kind
        assert out["kind"] == kind


def test_an_unreadable_kind_is_treated_as_unsupported():
    out = apply_answer({"kind": "please just do it", "mood": "night",
                        "understood": []}, dict(DEFAULT_SPEC))
    assert out["kind"] == "unsupported"
    assert out["mood"] == DEFAULT_SPEC["mood"]


# --- the ordinary path --------------------------------------------------- #

def test_a_style_answer_is_folded_in():
    out = apply_answer({"kind": "style", "mood": "night", "accent": "navy",
                        "lead_with": "gallery", "cta": "book",
                        "understood": ["styled night", "led with the gallery"]},
                       dict(DEFAULT_SPEC))
    assert (out["mood"], out["accent"], out["lead_with"]) == \
        ("night", "navy", "gallery")
    assert out["cta"]["kind"] == "book"


def test_suppressing_a_section_clears_it_from_everywhere_else():
    current = {**DEFAULT_SPEC, "lead_with": "reviews", "emphasis": ["reviews"]}
    out = apply_answer({"kind": "style", "suppress": ["reviews"],
                        "understood": []}, current)
    assert out["suppress"] == ["reviews"]
    assert out["emphasis"] == []
    assert out["lead_with"] is None


def test_fields_left_out_carry_forward():
    current = {**DEFAULT_SPEC, "mood": "warm", "accent": "navy"}
    out = apply_answer({"kind": "style", "lead_with": "menu",
                        "understood": []}, current)
    assert (out["mood"], out["accent"]) == ("warm", "navy")


def test_every_section_the_model_may_name_is_one_the_plan_knows():
    from app.site.plan import SECTION_RULES
    assert set(SECTIONS) <= {key for key, _, _ in SECTION_RULES}


# --- the transport ------------------------------------------------------- #

@respx.mock
def test_understand_calls_the_api_and_validates_the_answer(monkeypatch):
    monkeypatch.setattr(claude.config, "anthropic_api_key",
                        lambda: "test-key")  # pragma: allowlist secret
    route = respx.post(claude.MESSAGES_URL).mock(
        return_value=answered({"kind": "style", "accent": "blue",
                               "understood": ["accented blue"]}))
    out = understand("the page should have more blue", dict(DEFAULT_SPEC))
    assert out["accent"] == "blue"
    assert route.called
    body = route.calls[0].request.content.decode()
    # Forced, so the model cannot answer with prose. No temperature: current
    # models reject it, and the stored spec is what makes a rebuild identical.
    assert '"tool_choice"' in body
    assert "temperature" not in body


@respx.mock
def test_prose_instead_of_a_tool_call_is_an_error_not_a_guess(monkeypatch):
    monkeypatch.setattr(claude.config, "anthropic_api_key",
                        lambda: "test-key")  # pragma: allowlist secret
    respx.post(claude.MESSAGES_URL).mock(return_value=httpx.Response(
        200, json={"content": [{"type": "text", "text": "Sure! Here you go."}]}))
    with pytest.raises(ClaudeError):
        understand("more blue", dict(DEFAULT_SPEC))


@respx.mock
def test_an_api_refusal_is_reported_rather_than_swallowed(monkeypatch):
    monkeypatch.setattr(claude.config, "anthropic_api_key",
                        lambda: "test-key")  # pragma: allowlist secret
    respx.post(claude.MESSAGES_URL).mock(
        return_value=httpx.Response(429, text="rate limited"))
    with pytest.raises(ClaudeError):
        understand("more blue", dict(DEFAULT_SPEC))


def test_no_key_is_an_error_the_caller_can_fall_back_from(monkeypatch):
    monkeypatch.setattr(claude.config, "anthropic_api_key", lambda: None)
    assert claude.available() is False
    with pytest.raises(ClaudeError):
        understand("more blue", dict(DEFAULT_SPEC))


def test_the_suite_never_has_a_live_key():
    """Guards the guard: without this, a key in the developer's environment
    silently turns every pipeline test into a billable network call that passes
    only because the fallback catches it."""
    assert claude.available() is False
