"""The research extraction boundary.

``RawClaim`` and ``SourceRecord`` are the data the corroboration engine consumes.
A ``ClaimExtractor`` turns collected source text into ``RawClaim``s. The demo
path bundles pre-extracted claims (a ``PassthroughExtractor``); the production
path (``ClaudeClaimExtractor``) uses Claude to extract them from raw text.

Design note: the extractor always stamps ``source_url`` onto every claim from the
owning ``SourceRecord`` — the model never supplies provenance, so a claim can
never lack a source. The validator (`app.ai.validators`) enforces this as a hard
guard regardless.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Protocol

from app.core.enums import SourceType
from app.core.errors import RefusalError

DEFAULT_MODEL = "claude-opus-5"  # Opus for research synthesis (per master plan)

_EXTRACTION_SYSTEM = (
    "You extract atomic, factual claims about a local business from source text. "
    "Return ONLY a JSON array; each item is {\"field\": <snake_case field>, "
    "\"value\": <string>}. Extract only facts explicitly stated in the source. "
    "Never infer, guess, or fabricate. If a fact is not present, omit it. "
    "Use fields like: name, address, phone, hours, services, products, "
    "year_opened, owner_name, rating."
)


@dataclass(frozen=True)
class RawClaim:
    field: str
    value: str
    source_url: str
    source_type: SourceType


@dataclass
class SourceRecord:
    """One collected source. Either pre-populated with ``claims`` (demo) or
    carrying ``raw_text`` for the extractor to process (production)."""

    source_type: SourceType
    source_url: str
    entity_name: str
    entity_address: str | None = None
    entity_phone: str | None = None
    raw_text: str | None = None
    claims: list[RawClaim] = field(default_factory=list)


class ClaimExtractor(Protocol):
    def extract(self, sources: list[SourceRecord]) -> list[RawClaim]: ...


class PassthroughExtractor:
    """Flattens claims already attached to each source (demo / fixtures)."""

    def extract(self, sources: list[SourceRecord]) -> list[RawClaim]:
        return [claim for source in sources for claim in source.claims]


def _first_json_array(text: str) -> str:
    match = re.search(r"\[.*\]", text, re.DOTALL)
    return match.group(0) if match else "[]"


class ClaudeClaimExtractor:
    """Extracts claims from source text using Claude.

    ``client`` is injectable so tests can pass a fake (no network, no API key).
    In production, leave it unset and it constructs ``anthropic.Anthropic()``,
    which reads ``ANTHROPIC_API_KEY``.
    """

    def __init__(self, client=None, *, model: str = DEFAULT_MODEL) -> None:  # noqa: ANN001
        self._client = client
        self._model = model

    def _get_client(self):
        if self._client is None:
            import anthropic  # imported lazily so the dep is optional until used

            self._client = anthropic.Anthropic()
        return self._client

    @property
    def model_version(self) -> str:
        return self._model

    def extract(self, sources: list[SourceRecord]) -> list[RawClaim]:
        out: list[RawClaim] = []
        for source in sources:
            if source.claims:
                out.extend(source.claims)
                continue
            if not source.raw_text:
                continue
            resp = self._get_client().messages.create(
                model=self._model,
                max_tokens=4096,
                system=_EXTRACTION_SYSTEM,
                messages=[
                    {
                        "role": "user",
                        "content": (
                            f"Source ({source.source_type.value}) {source.source_url}:\n\n"
                            f"{source.raw_text}"
                        ),
                    }
                ],
            )
            if getattr(resp, "stop_reason", None) == "refusal":
                raise RefusalError(f"extraction refused for {source.source_url}")
            text = "".join(
                b.text for b in resp.content if getattr(b, "type", None) == "text"
            )
            for item in json.loads(_first_json_array(text)):
                if "field" in item and "value" in item:
                    out.append(
                        RawClaim(
                            field=str(item["field"]),
                            value=str(item["value"]),
                            source_url=source.source_url,
                            source_type=source.source_type,
                        )
                    )
        return out
