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

import base64
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


# What the API will accept. Anything above the byte ceiling is rejected
# outright; anything wider than the pixel ceiling is resized server-side
# anyway, so sending more is paying to have it thrown away.
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_IMAGE_EDGE = 1568


def image_block(data: bytes, media_type: str = "image/jpeg") -> dict:
    """One image, as a content block."""
    return {"type": "image",
            "source": {"type": "base64", "media_type": media_type,
                       "data": base64.b64encode(data).decode()}}


def structured(system: str, prompt: str, tool: dict, *,
               client: httpx.Client | None = None,
               model: str | None = None,
               max_tokens: int = 1024,
               timeout: float | None = None,
               blocks: list[dict] | None = None) -> dict[str, Any]:
    """Ask for one tool call and return its input.

    `tool` is a JSON Schema the answer must satisfy. Forcing the tool means the
    model has no way to reply with prose, which is the property the caller
    depends on: it is being asked for decisions, not for writing.

    `blocks` carries content blocks — images, built with `image_block` — that
    precede the prompt. The prompt is always the last block, so an instruction
    is never buried above the material it refers to.

    `max_tokens` and `timeout` are per call because the calls are not alike: a
    design system needs far more than a thousand tokens to come back, and a
    batched vision call over a dozen photographs needs far more than twenty
    seconds to answer.

    No `temperature`: current models reject it, and it was never what made this
    reproducible. A version replays from its stored spec, so rebuilding v41
    gives the same page whether or not reading the sentence twice would give
    the same spec.
    """
    key = config.anthropic_api_key()
    if not key:
        raise ClaudeError("no ANTHROPIC_API_KEY set")

    content: list[dict] = list(blocks or [])
    content.append({"type": "text", "text": prompt})

    owned = client is None
    http = client or httpx.Client(timeout=timeout or TIMEOUT)
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
                "messages": [{"role": "user", "content": content}],
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
