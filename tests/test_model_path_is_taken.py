"""With a key, the model is actually asked.

`tests/conftest.py` removes the API key from every test, which stops a key in
the developer's environment turning the suite into billable network calls. That
guards one direction only: every "the fallback ran" assertion elsewhere is
green because no key exists, and would stay green if the model path were
deleted outright.

So this file injects a fake key, stubs the transport, and asserts each of the
three call sites reaches the API. Both branches are then covered on purpose
rather than one of them by accident.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from app.adapters import claude, vision
from app.core import config
from app.site import opening, pipeline
from app.site.iterate import DEFAULT_SPEC

pytestmark = pytest.mark.unit

BRIEF = {"name": "Ichika", "trade": "Japanese Restaurant",
         "published": {"tagline": "Kaiseki, twelve seats."}}


@pytest.fixture
def keyed(monkeypatch):
    """Undo the suite-wide key removal, for this test only."""
    monkeypatch.setattr(config, "anthropic_api_key",
                        lambda: "test-key")       # pragma: allowlist secret
    assert claude.available() is True
    return "test-key"                             # pragma: allowlist secret


def replies(name: str, payload: dict) -> httpx.Response:
    return httpx.Response(200, json={
        "content": [{"type": "tool_use", "name": name, "input": payload}]})


@respx.mock
def test_an_instruction_is_read_by_the_model_when_a_key_exists(keyed):
    route = respx.post(claude.MESSAGES_URL).mock(return_value=replies(
        "decide", {"kind": "style", "accent": "navy",
                   "understood": ["accented navy"]}))
    out = pipeline.read_instruction("something cooler", dict(DEFAULT_SPEC))
    assert route.called, "the model was never asked"
    assert out["read_by"] == "claude"
    assert out["accent"] == "navy"


@respx.mock
def test_the_opening_design_is_asked_for_when_a_key_exists(keyed):
    route = respx.post(claude.MESSAGES_URL).mock(return_value=replies(
        "design", {"mood": "refined", "accent": "charcoal", "cta": "book",
                   "rationale": "a twelve-seat counter"}))
    config_out = opening.opening_spec(BRIEF)
    assert route.called, "the model was never asked"
    assert config_out["read_by"] == "claude"
    assert config_out["mood"] == "refined"


@respx.mock
def test_the_photographs_are_looked_at_when_a_key_exists(keyed, monkeypatch):
    monkeypatch.setattr(vision, "thumbnail",
                        lambda url, names: b"\xff\xd8\xff\xe0" + b"\x00" * 32)
    route = respx.post(claude.MESSAGES_URL).mock(return_value=replies(
        "describe", {"images": [{"index": 0, "subject": "dish",
                                 "is_hero_candidate": True, "quality": 4,
                                 "alt_text": "A plate of food"}]}))
    seen = vision.look(["/photo/1/0"])
    assert route.called, "the model was never asked"
    assert seen["/photo/1/0"]["subject"] == "dish"


def test_and_without_a_key_none_of_them_reach_the_network():
    """The other half, stated here so the pair is visible in one file."""
    assert claude.available() is False
    assert vision.look(["/photo/1/0"]) == {}
    assert opening.opening_spec(BRIEF)["read_by"] == "trade table"
    assert pipeline.read_instruction("more blue",
                                     dict(DEFAULT_SPEC))["read_by"] == "phrases"
