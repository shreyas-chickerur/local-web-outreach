"""Live source collection: two defensible sources, honest corroboration."""

from __future__ import annotations

import pytest

from app.adapters.directory import NullDirectorySource
from app.adapters.site_fetch import FetchResult
from app.core.enums import SourceType
from app.stages.collect import collect_sources, find_contact_email, find_phone, html_to_text

pytestmark = pytest.mark.unit


class _Biz:
    def __init__(self, **kw):
        self.name = kw.get("name", "Acme Lawn")
        self.location = kw.get("location", "Frisco, TX")
        self.place_id = kw.get("place_id", "pid123")
        self.address = kw.get("address", "1 Main St, Frisco, TX")
        self.phone = kw.get("phone", "(972) 555-0148")
        self.existing_site_url = kw.get("existing_site_url")
        self.contact_email = None


class _Fetcher:
    def __init__(self, html="", ok=True):
        self._r = FetchResult(ok=ok, status=200 if ok else None, final_url="https://acme.example/",
                              html=html, elapsed_ms=10, error=None)

    def fetch(self, url):
        return self._r


def test_html_to_text_strips_scripts_and_tags():
    text = html_to_text("<style>a{}</style><script>x()</script><p>Hello <b>there</b></p>")
    assert "Hello there" in text
    assert "x()" not in text and "a{}" not in text


@pytest.mark.parametrize("html,expected", [
    ('<a href="mailto:info@acme.com">mail</a>', "info@acme.com"),
    ("owner@acme.com and info@acme.com", "info@acme.com"),   # role address preferred
    ("bob@acme.com", "bob@acme.com"),                        # falls back to what's there
    ("noreply@example.com", None),                           # blocklisted domain
    ("logo@2x.png", None),                                   # asset, not an address
    ("no address here", None),
])
def test_find_contact_email(html, expected):
    assert find_contact_email(html) == expected


def test_find_phone():
    assert find_phone("call (972) 555-0148 today") == "(972) 555-0148"
    assert find_phone("no digits") is None


def test_collect_uses_gbp_alone_when_there_is_no_site():
    collected = collect_sources(_Biz(existing_site_url=None), _Fetcher(), [NullDirectorySource()])
    assert len(collected.sources) == 1
    assert collected.sources[0].source_type is SourceType.GBP
    assert {c.field for c in collected.sources[0].claims} == {"address", "phone"}
    assert collected.contact_email is None


def test_collect_adds_the_businesss_own_site_as_a_second_source():
    html = "<p>Acme Lawn — call (972) 555-0148 or email info@acme.com</p>"
    collected = collect_sources(_Biz(existing_site_url="https://acme.example/"), _Fetcher(html),
                                [NullDirectorySource()])

    types = [s.source_type for s in collected.sources]
    assert types == [SourceType.GBP, SourceType.EXISTING_SITE]
    assert collected.contact_email == "info@acme.com"
    # the phone is asserted by BOTH sources -> corroboration is real, not invented
    site = collected.sources[1]
    assert [c.field for c in site.claims] == ["phone"]
    assert site.claims[0].value == "(972) 555-0148"


def test_collect_tolerates_an_unreachable_site():
    collected = collect_sources(_Biz(existing_site_url="https://down.example/"),
                                _Fetcher(ok=False), [NullDirectorySource()])
    assert len(collected.sources) == 1  # only GBP; nothing fabricated
    assert collected.contact_email is None


def test_qualified_to_researched_is_a_legal_transition():
    """`advance` walks QUALIFIED -> RESEARCHED -> SITE_DRAFTED; the first hop was
    never exercised by the demos (they created businesses already RESEARCHED)."""
    from app.core.enums import BusinessStatus as S
    from app.core.state_machine import can_transition

    assert can_transition(S.QUALIFIED, S.RESEARCHED)
    assert can_transition(S.RESEARCHED, S.SITE_DRAFTED)
