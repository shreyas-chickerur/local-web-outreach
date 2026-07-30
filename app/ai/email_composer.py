"""Outreach email composition.

An ``EmailComposer`` turns a business's public identity + the specific weakness we
found + the approved site's preview link into a short, personalized email (one
CTA = the preview). ``TemplateEmailComposer`` is deterministic and grounded
(references only true specifics — name, location, an evidenced weakness, the real
preview link); ``ClaudeEmailComposer`` uses Claude for warmer copy and is
injectable so tests run without a key. Neither adds the footer — that's the
compliance layer's job.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Protocol

from app.core.errors import RefusalError

DEFAULT_MODEL = "claude-opus-5"

# Highest-severity weakness first — pick the most compelling angle. Each value is
# a full clause that reads naturally after "…and noticed ".
_SEVERITY_RANK = {"high": 0, "medium": 1, "low": 2}

_WEAKNESS_CLAUSE = {
    "no_site": "you don't have a website yet",
    "site_unreachable": "your website isn't loading right now",
    "no_https": "your website isn't secure (no HTTPS)",
    "not_mobile_responsive": "your website isn't mobile-friendly",
    "stale_content": "your website looks a bit dated",
    "slow_load": "your website loads slowly",
}
_DEFAULT_CLAUSE = "your website could use a refresh"

_COMPOSER_SYSTEM = (
    "You write short, warm, honest cold outreach emails to local business owners "
    "about a website you built for them. Reference only the specifics given. Never "
    "invent facts, reviews, or urgency. Exactly one call to action: the preview "
    "link. Return ONLY JSON: {\"subject\": ..., \"body\": ...}. No footer."
)


@dataclass(frozen=True)
class EmailDraft:
    subject: str
    body: str


def _observation(weaknesses: list[tuple[str, str]]) -> str:
    """A natural-language clause describing the most severe weakness."""
    if not weaknesses:
        return _DEFAULT_CLAUSE
    top = sorted(weaknesses, key=lambda w: _SEVERITY_RANK.get(w[1], 9))[0][0]
    return _WEAKNESS_CLAUSE.get(top, _DEFAULT_CLAUSE)


class EmailComposer(Protocol):
    def compose(
        self, *, business_name: str, location: str,
        weaknesses: list[tuple[str, str]], preview_url: str,
    ) -> EmailDraft: ...


class TemplateEmailComposer:
    """Deterministic, grounded composer (no API key needed)."""

    def compose(
        self, *, business_name: str, location: str,
        weaknesses: list[tuple[str, str]], preview_url: str,
    ) -> EmailDraft:
        observation = _observation(weaknesses)
        subject = f"A quick idea for {business_name}"
        body = (
            f"Hi {business_name} team,\n\n"
            f"I came across {business_name} in {location} and noticed {observation}. "
            f"I put together a modern website preview you can look at here:\n\n"
            f"{preview_url}\n\n"
            f"If you like it, I can have it live quickly — no obligation, and happy to "
            f"tweak anything.\n\n"
            f"Best"
        )
        return EmailDraft(subject=subject, body=body)


def _first_json_object(text: str) -> str:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return match.group(0) if match else "{}"


class ClaudeEmailComposer:
    """Claude-backed composer. ``client`` is injectable for tests; in production
    it constructs ``anthropic.Anthropic()`` (reads ANTHROPIC_API_KEY)."""

    def __init__(self, client=None, *, model: str = DEFAULT_MODEL) -> None:  # noqa: ANN001
        self._client = client
        self._model = model

    def _get_client(self):
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic()
        return self._client

    def compose(
        self, *, business_name: str, location: str,
        weaknesses: list[tuple[str, str]], preview_url: str,
    ) -> EmailDraft:
        observation = _observation(weaknesses)
        prompt = (
            f"Business: {business_name}\nLocation: {location}\n"
            f"What to mention about their web presence: {observation}\n"
            f"Preview link (the one CTA): {preview_url}\n\n"
            "Write the outreach email."
        )
        resp = self._get_client().messages.create(
            model=self._model, max_tokens=1024, system=_COMPOSER_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        if getattr(resp, "stop_reason", None) == "refusal":
            raise RefusalError(f"email composition refused for {business_name}")
        text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
        data = json.loads(_first_json_object(text))
        return EmailDraft(subject=str(data.get("subject", "")), body=str(data.get("body", "")))
