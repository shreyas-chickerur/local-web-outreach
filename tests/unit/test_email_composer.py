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
    # no working site -> we must NOT claim we looked at one
    assert "couldn't find a website" in draft.body
    assert "had a look at your website" not in draft.body


def test_template_composer_no_weakness_still_grounded():
    draft = TemplateEmailComposer().compose(
        business_name="Acme", location="Frisco, TX", weaknesses=[],
        preview_url="https://p.example/",
    )
    assert "https://p.example/" in draft.body
    assert "Acme" in draft.body


# Wording that criticises the owner's current site. The offer stands on its own;
# leading with a fault is a poor first impression and invites a defensive reply.
_CRITICISM = ("dated", "outdated", "not secure", "isn\'t secure", "insecure", "slow",
              "loads slowly", "not mobile", "isn\'t mobile", "broken", "isn\'t loading",
              "needs work", "could use a refresh", "poor", "old")


@pytest.mark.parametrize("weaknesses", [
    [("stale_content", "medium")],
    [("no_https", "high")],
    [("slow_load", "low"), ("no_https", "high")],
    [("not_mobile_responsive", "medium")],
    [("no_site", "high")],
    [],
])
def test_email_never_criticises_their_current_site(weaknesses):
    draft = TemplateEmailComposer().compose(
        business_name="Acme", location="Frisco, TX",
        weaknesses=weaknesses, preview_url="https://p/",
    )
    lowered = draft.body.lower()
    found = [w for w in _CRITICISM if w in lowered]
    assert not found, f"email criticises their site: {found}"


def test_email_only_claims_to_have_seen_a_site_that_exists():
    """Saying 'I had a look at your website' to a business with none is false."""
    with_site = TemplateEmailComposer().compose(
        business_name="Acme", location="Frisco, TX",
        weaknesses=[("stale_content", "medium")], preview_url="https://p/")
    assert "had a look at your website" in with_site.body

    for issue in ("no_site", "site_unreachable"):
        without = TemplateEmailComposer().compose(
            business_name="Acme", location="Frisco, TX",
            weaknesses=[(issue, "high")], preview_url="https://p/")
        assert "couldn't find a website" in without.body


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
