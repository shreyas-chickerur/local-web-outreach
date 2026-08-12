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

# We do NOT open by criticising their website. Telling an owner their site is
# dated or insecure is a poor first impression and invites a defensive reply —
# the offer stands on its own. The weakness now decides exactly ONE thing:
# whether it is truthful to say we looked at their site. Saying "I had a look at
# your website" to someone whose site is down, or who has none, is false.
_SEVERITY_RANK = {"high": 0, "medium": 1, "low": 2}

# Weaknesses meaning there was no working site for us to have seen.
_NO_SITE_ISSUES = {"no_site", "site_unreachable"}

_COMPOSER_SYSTEM = (
    "You write short, warm, honest cold outreach emails to local business owners, "
    "offering a modern website you have already built for them. Reference only the "
    "specifics given. NEVER criticise, grade, or comment on the quality of their "
    "current website — do not call it dated, slow, insecure, or broken. Lead with "
    "the offer, not a problem. Never invent facts, reviews, or urgency. Exactly one "
    "call to action: the preview link. Return ONLY JSON: "
    "{\"subject\": ..., \"body\": ...}. No footer."
)


@dataclass(frozen=True)
class EmailDraft:
    subject: str
    body: str


def has_working_site(weaknesses: list[tuple[str, str]]) -> bool:
    """False when the evidence says there is no reachable site to have seen."""
    return not any(issue in _NO_SITE_ISSUES for issue, _ in (weaknesses or []))


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
        opener = (
            f"I came across {business_name} in {location} and had a look at your website."
            if has_working_site(weaknesses)
            else f"I came across {business_name} in {location} and couldn't find a "
                 f"website for you."
        )
        subject = f"A modern website for {business_name}"
        body = (
            f"Hi {business_name} team,\n\n"
            f"{opener} I build modern, fast, mobile-friendly sites for local "
            f"businesses, and I wondered whether I could set one up for you — so I "
            f"went ahead and built a preview you can look at here:\n\n"
            f"{preview_url}\n\n"
            f"It's a real working page, not a mock-up. If you like it I can have it "
            f"live quickly — no obligation, and happy to change anything.\n\n"
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
        prompt = (
            f"Business: {business_name}\nLocation: {location}\n"
            f"They currently have a working website: "
            f"{'yes' if has_working_site(weaknesses) else 'no'}\n"
            f"Preview link (the one CTA): {preview_url}\n\n"
            "Write the outreach email offering them this modern site. Do not "
            "comment on the quality of their existing site."
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
