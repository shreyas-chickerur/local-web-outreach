"""Validating the address a directory publishes, and correcting it.

Every case here came off a real listing. The rule they share: find the spelling
that works, and never quietly repair the fault out of the brief — the fault is
usually the reason to walk in.
"""

from __future__ import annotations

import pytest

from app.adapters.site_fetch import FetchResult
from app.workbench.weburl import candidates, validate

pytestmark = pytest.mark.unit

PAGE = "<html><body>" + "word " * 300 + "</body></html>"


class _Fake:
    """Answers per URL; anything unlisted is a connection failure."""

    def __init__(self, answers: dict):
        self.answers, self.tried = answers, []

    def fetch(self, url):
        self.tried.append(url)
        answer = self.answers.get(url)
        if answer is None:
            return FetchResult(ok=False, status=None, final_url=None, html="",
                               elapsed_ms=1, error="connection refused")
        return answer


def _ok(url, html=PAGE):
    return FetchResult(ok=True, status=200, final_url=url, html=html, elapsed_ms=1)


def _status(code):
    return FetchResult(ok=False, status=code, final_url=None, html="nope",
                       elapsed_ms=1)


def _tls():
    return FetchResult(ok=False, status=None, final_url=None, html="", elapsed_ms=1,
                       error="[SSL: CERTIFICATE_VERIFY_FAILED] Hostname mismatch",
                       tls_error=True)


def test_secure_spellings_are_tried_before_insecure_ones():
    """Whether an https spelling works decides the verdict, not just the speed:
    it is the difference between a stale link and a site with no TLS."""
    order = candidates("http://example.com/menu")
    assert order[0] == "http://example.com/menu"
    assert order.index("https://example.com/menu") < order.index("http://www.example.com/menu")


def test_a_certificate_mismatch_finds_the_working_spelling():
    """yamadallas.com serves a certificate invalid for its www hostname, which
    is the exact address Google publishes."""
    fetcher = _Fake({"https://www.yama.example/": _tls(),
                     "https://yama.example/": _ok("https://yama.example/")})
    check = validate("https://www.yama.example/", fetcher)
    assert check.fault == "certificate"
    assert check.working == "https://yama.example/"
    assert "security warning" in check.note
    assert check.needs_correction


def test_a_listing_on_http_when_https_works_is_a_stale_link():
    fetcher = _Fake({"http://shop.example/": _ok("http://shop.example/"),
                     "https://shop.example/": _ok("https://shop.example/")})
    check = validate("http://shop.example/", fetcher)
    assert check.fault == "http-link"
    assert check.working == "https://shop.example/"


def test_a_site_with_no_https_at_all_is_a_different_problem():
    fetcher = _Fake({"http://old.example/": _ok("http://old.example/")})
    check = validate("http://old.example/", fetcher)
    assert check.fault == "no-https"
    assert check.working == "http://old.example/"
    assert "no https at all" in check.note


def test_a_dead_page_falls_back_to_the_site_root():
    fetcher = _Fake({"https://x.example/old-menu": _status(404),
                     "https://x.example/": _ok("https://x.example/")})
    check = validate("https://x.example/old-menu", fetcher)
    assert check.fault == "not-found"
    assert check.working == "https://x.example/"


def test_a_lapsed_domain_shows_as_parked_not_as_a_website():
    """A registrar's for-sale page answers 200. It is not their site, and
    treating it as one would credit a business with a website it lost."""
    parked = _ok("https://gone.example/",
                 "<html><h1>This domain is for sale</h1> buy this domain</html>")
    fetcher = _Fake({"https://gone.example/": parked})
    check = validate("https://gone.example/", fetcher)
    assert check.fault == "parked"
    assert check.is_broken


def test_nothing_answering_anywhere_is_dead():
    check = validate("https://nowhere.example/", _Fake({}))
    assert check.fault == "dead"
    assert check.working is None


def test_being_refused_is_not_a_verdict():
    """A 403 is their bot filter, not a fault. Reporting anything else — least
    of all a judgement drawn from the body of the error page — would be a lie."""
    blocked = _Fake({url: _status(403) for url in candidates("https://guard.example/")})
    check = validate("https://guard.example/", blocked)
    assert check.blocked is True
    assert check.fault is None
    assert "open it yourself" in check.note


def test_a_working_address_reports_no_fault():
    fetcher = _Fake({"https://fine.example/": _ok("https://fine.example/")})
    check = validate("https://fine.example/", fetcher)
    assert check.fault is None and check.note == ""
    assert not check.needs_correction


def test_a_www_redirect_is_a_spelling_not_a_finding():
    """Landing on the apex from the www address is how the web works."""
    fetcher = _Fake({"https://www.fine.example/": _ok("https://fine.example/")})
    check = validate("https://www.fine.example/", fetcher)
    assert check.fault is None


def test_landing_on_a_different_domain_is_worth_reporting():
    """A listing that lands on a Facebook page is a business without a site."""
    fetcher = _Fake({"https://biz.example/": _ok("https://facebook.com/biz")})
    check = validate("https://biz.example/", fetcher)
    assert check.fault == "redirected"
    assert "facebook.com" in check.note
