"""Email composer tests: grounded template output + mocked Claude composer."""

from __future__ import annotations

import pytest

from app.ai.email_composer import ClaudeEmailComposer, EmailDraft, TemplateEmailComposer
from app.core.errors import RefusalError

pytestmark = pytest.mark.unit


def test_template_composer_is_grounded_with_one_cta():
    draft = TemplateEmailComposer().compose(
        business_name="Acme Diner", location="Frisco, TX",
        weaknesses=[("no_site", "high")], preview_url="https://preview-x.example/",
    )
    assert isinstance(draft, EmailDraft)
    assert "Acme Diner" in draft.subject
    assert "Acme Diner" in draft.body
    assert "Frisco, TX" in draft.body
    assert draft.body.count("https://preview-x.example/") == 1  # exactly one CTA
    assert "you don't have a website yet" in draft.body  # natural clause for no_site


def test_template_composer_no_weakness_still_grounded():
    draft = TemplateEmailComposer().compose(
        business_name="Acme", location="Frisco, TX", weaknesses=[],
        preview_url="https://p.example/",
    )
    assert "https://p.example/" in draft.body
    assert "could use a refresh" in draft.body


def test_template_composer_picks_highest_severity():
    draft = TemplateEmailComposer().compose(
        business_name="Acme", location="Frisco, TX",
        weaknesses=[("slow_load", "low"), ("no_https", "high")], preview_url="https://p/",
    )
    assert "isn't secure" in draft.body  # HIGH no_https beats LOW slow_load


# --- mocked Claude composer (no network / no key) ---
class _Block:
    def __init__(self, text):
        self.type = "text"
        self.text = text


class _Resp:
    def __init__(self, text, stop_reason="end_turn"):
        self.content = [_Block(text)]
        self.stop_reason = stop_reason


class _Messages:
    def __init__(self, resp):
        self._resp = resp
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self._resp


class _Client:
    def __init__(self, resp):
        self.messages = _Messages(resp)


def test_claude_composer_parses_json():
    resp = _Resp('Here you go: {"subject": "Hi Acme", "body": "Hello — see https://p/"}')
    draft = ClaudeEmailComposer(client=_Client(resp), model="claude-opus-5").compose(
        business_name="Acme", location="Frisco", weaknesses=[("no_https", "high")],
        preview_url="https://p/",
    )
    assert draft.subject == "Hi Acme"
    assert "https://p/" in draft.body


def test_claude_composer_raises_on_refusal():
    composer = ClaudeEmailComposer(client=_Client(_Resp("", stop_reason="refusal")))
    with pytest.raises(RefusalError):
        composer.compose(business_name="A", location="B", weaknesses=[], preview_url="https://p/")
