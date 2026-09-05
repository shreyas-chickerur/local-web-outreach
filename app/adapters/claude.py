"""Claude — one request, one structured answer.

Raw httpx for the same reason every other adapter here uses it: the SDK is a
dependency this project does not otherwise need, and the Messages API is one
POST.

The call is made with a tool schema rather than by asking for JSON in prose,
so the shape of the answer is enforced by the API rather than hoped for. What
comes back is still validated field by field before anything acts on it — see
`app.site.understand`. A model is a source, and sources get corroborated.
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from app.core import config

MESSAGES_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"

# An instruction is a sentence. There is nothing here worth a long timeout, and
# a slow answer is worse than falling back to the phrase parser.
TIMEOUT = 20.0


class ClaudeError(RuntimeError):
    """The API refused, timed out, or answered in a shape we cannot use."""


def available() -> bool:
    return config.anthropic_api_key() is not None


def structured(system: str, prompt: str, tool: dict, *,
               client: httpx.Client | None = None,
               model: str | None = None,
               max_tokens: int = 1024) -> dict[str, Any]:
    """Ask for one tool call and return its input.

    `tool` is a JSON Schema the answer must satisfy. Forcing the tool means the
    model has no way to reply with prose, which is the property the caller
    depends on: it is being asked for decisions, not for writing.

    No `temperature`: current models reject it, and it was never what made this
    reproducible. A version replays from its stored spec, so rebuilding v41
    gives the same page whether or not reading the sentence twice would give
    the same spec.
    """
    key = config.anthropic_api_key()
    if not key:
        raise ClaudeError("no ANTHROPIC_API_KEY set")

    owned = client is None
    http = client or httpx.Client(timeout=TIMEOUT)
    try:
        response = http.post(
            MESSAGES_URL,
            headers={"x-api-key": key, "anthropic-version": API_VERSION,
                     "content-type": "application/json"},
            json={
                "model": model or config.anthropic_model(),
                "max_tokens": max_tokens,
                "system": system,
                "tools": [tool],
                "tool_choice": {"type": "tool", "name": tool["name"]},
                "messages": [{"role": "user", "content": prompt}],
            })
    except httpx.HTTPError as exc:
        raise ClaudeError(f"could not reach the API: {exc}") from exc
    finally:
        if owned:
            http.close()

    if response.status_code != 200:
        raise ClaudeError(f"HTTP {response.status_code}: {response.text[:300]}")
    try:
        payload = response.json()
    except json.JSONDecodeError as exc:
        raise ClaudeError("the API returned something that is not JSON") from exc

    for block in payload.get("content") or []:
        if block.get("type") == "tool_use" and block.get("name") == tool["name"]:
            found = block.get("input")
            if isinstance(found, dict):
                return found
    raise ClaudeError("the answer contained no tool call")
