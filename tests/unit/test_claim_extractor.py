"""ClaudeClaimExtractor tests with a fake Anthropic client (no network / no key)."""

from __future__ import annotations

import pytest

from app.ai.research_runner import (
    ClaudeClaimExtractor,
    PassthroughExtractor,
    RawClaim,
    SourceRecord,
)
from app.core.enums import SourceType
from app.core.errors import RefusalError

pytestmark = pytest.mark.unit


class _Block:
    def __init__(self, text):
        self.type = "text"
        self.text = text


class _Resp:
    def __init__(self, text, stop_reason="end_turn"):
        self.content = [_Block(text)]
        self.stop_reason = stop_reason


class _FakeMessages:
    def __init__(self, resp):
        self._resp = resp
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self._resp


class _FakeClient:
    def __init__(self, resp):
        self.messages = _FakeMessages(resp)


def _src(raw_text):
    return SourceRecord(
        source_type=SourceType.YELP, source_url="https://yelp.com/x",
        entity_name="Acme", raw_text=raw_text,
    )


def test_extractor_parses_json_and_stamps_source():
    resp = _Resp('Here are the claims: [{"field": "phone", "value": "555-1212"}, '
                 '{"field": "address", "value": "1 Main St"}]')
    extractor = ClaudeClaimExtractor(client=_FakeClient(resp), model="claude-opus-5")
    claims = extractor.extract([_src("Acme, 1 Main St, 555-1212")])

    assert {c.field for c in claims} == {"phone", "address"}
    # source_url + source_type are stamped from the SourceRecord, never the model
    assert all(c.source_url == "https://yelp.com/x" for c in claims)
    assert all(c.source_type is SourceType.YELP for c in claims)
    # correct model was requested
    assert extractor._client.messages.calls[0]["model"] == "claude-opus-5"


def test_extractor_raises_on_refusal():
    extractor = ClaudeClaimExtractor(client=_FakeClient(_Resp("", stop_reason="refusal")))
    with pytest.raises(RefusalError):
        extractor.extract([_src("some text")])


def test_extractor_uses_prebaked_claims_without_calling_model():
    pre = RawClaim(field="phone", value="555", source_url="https://x", source_type=SourceType.GBP)
    src = SourceRecord(source_type=SourceType.GBP, source_url="https://x",
                       entity_name="Acme", claims=[pre])
    client = _FakeClient(_Resp("[]"))
    claims = ClaudeClaimExtractor(client=client).extract([src])
    assert claims == [pre]
    assert client.messages.calls == []  # model not consulted when claims exist


def test_passthrough_extractor_flattens_claims():
    a = RawClaim("phone", "1", "https://a", SourceType.GBP)
    b = RawClaim("address", "2", "https://b", SourceType.YELP)
    sources = [
        SourceRecord(SourceType.GBP, "https://a", "Acme", claims=[a]),
        SourceRecord(SourceType.YELP, "https://b", "Acme", claims=[b]),
    ]
    assert PassthroughExtractor().extract(sources) == [a, b]
