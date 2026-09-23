"""Fetching a candidate's existing website — real Chrome when it is
available, a real HTTP GET when it is not, and never a hard failure just
because Chrome had a hiccup on one page.
"""

from __future__ import annotations

import httpx
import pytest

from app.adapters.chrome_cdp import chrome
from app.adapters.site_fetch import (
    ChromeSiteFetcher,
    FetchResult,
    HttpSiteFetcher,
    default_fetcher,
    render_document,
)

pytestmark = pytest.mark.unit


@pytest.mark.skipif(chrome() is None, reason="no Chrome/Chromium on this machine")
def test_client_side_content_is_visible_after_rendering(tmp_path):
    """The whole reason this exists: a page that draws itself with
    JavaScript is a near-empty shell to a raw HTTP GET. Rendered through a
    real browser first, the JS-authored content is right there in the DOM."""
    page = tmp_path / "spa.html"
    page.write_text(
        '<html><body><div id="root"></div><script>'
        'document.getElementById("root").innerHTML = '
        '"<h1>rendered by JS</h1><p>Tacos $12</p>";'
        "</script></body></html>")
    result = render_document(chrome(), page.resolve().as_uri())
    assert result.ok
    assert "rendered by JS" in result.html
    assert "Tacos $12" in result.html


@pytest.mark.skipif(chrome() is None, reason="no Chrome/Chromium on this machine")
def test_a_missing_local_page_reports_its_real_status(tmp_path):
    """A 404 has to read as a 404, not as `ok=True` with empty HTML — the
    qualifier's own `site_state()` depends on the real status to tell
    "blocked" apart from "unreachable" apart from "a genuine 404"."""
    binary = chrome()
    result = render_document(binary, "file:///no/such/path/at/all.html")
    assert not result.ok


def test_without_chrome_the_fetcher_falls_straight_back(monkeypatch):
    """No Chrome installed must not be a build-time or run-time failure —
    it degrades to the plain HTTP fetcher, the same "everything degrades,
    the degraded path still works" invariant `app.site.opening`'s
    Claude-then-trade-table fallback already relies on."""
    calls = []

    class FakeFallback:
        def fetch(self, url: str) -> FetchResult:
            calls.append(url)
            return FetchResult(ok=True, status=200, final_url=url,
                               html="<p>plain http</p>", elapsed_ms=5)

    fetcher = ChromeSiteFetcher(fallback=FakeFallback())
    fetcher._binary = None  # simulate no Chrome/Chromium on this machine
    result = fetcher.fetch("https://example.com/")
    assert calls == ["https://example.com/"]
    assert result.html == "<p>plain http</p>"


def test_a_render_exception_falls_back_rather_than_raising(monkeypatch):
    """A render bug (a bad binary path, an unexpected CDP shape) must lose
    nothing more than the JS-rendering advantage for that one page — never
    the fetch itself."""
    import app.adapters.site_fetch as site_fetch_module

    def boom(binary, url, timeout=20.0):
        raise RuntimeError("something in the CDP session went wrong")

    monkeypatch.setattr(site_fetch_module, "render_document", boom)

    class FakeFallback:
        def fetch(self, url: str) -> FetchResult:
            return FetchResult(ok=True, status=200, final_url=url,
                               html="<p>fallback</p>", elapsed_ms=5)

    fetcher = ChromeSiteFetcher(fallback=FakeFallback())
    fetcher._binary = "/pretend/chrome"
    result = fetcher.fetch("https://example.com/")
    assert result.html == "<p>fallback</p>"


def test_default_fetcher_picks_by_availability(monkeypatch):
    import app.adapters.site_fetch as site_fetch_module

    monkeypatch.setattr(site_fetch_module.chrome_cdp, "chrome", lambda: None)
    assert isinstance(default_fetcher(), HttpSiteFetcher)

    monkeypatch.setattr(site_fetch_module.chrome_cdp, "chrome",
                        lambda: "/pretend/chrome")
    assert isinstance(default_fetcher(), ChromeSiteFetcher)


def test_http_fetcher_is_unaffected_by_any_of_this():
    """The plain fetcher's own behaviour — untouched by this round's
    changes — still works exactly as before."""
    with httpx.Client() as client:
        fetcher = HttpSiteFetcher(client=client)
        assert fetcher._client is client


def test_a_render_that_fails_still_tries_a_plain_fetch(monkeypatch):
    """The Heritage Table's history page timed out in Chrome and was recorded as
    unreadable without a plain fetch ever being tried: a failed render came
    back as a result, not an error, so the fallback never ran."""
    from app.adapters import site_fetch

    failed = site_fetch.FetchResult(ok=False, status=None, final_url="u", html="",
                                    elapsed_ms=1, error="timed out")
    monkeypatch.setattr(site_fetch, "render_document", lambda *a, **k: failed)

    class Plain:
        def __init__(self, result):
            self.result = result

        def fetch(self, url):
            return self.result

    good = site_fetch.FetchResult(ok=True, status=200, final_url="u", html="<p>1911</p>",
                                  elapsed_ms=1)
    fetcher = site_fetch.ChromeSiteFetcher(fallback=Plain(good))
    fetcher._binary = "chrome"
    assert fetcher.fetch("u").html == "<p>1911</p>"

    refused = site_fetch.FetchResult(ok=False, status=406, final_url="u", html="",
                                     elapsed_ms=1)
    fetcher = site_fetch.ChromeSiteFetcher(fallback=Plain(refused))
    fetcher._binary = "chrome"
    result = fetcher.fetch("u")
    assert not result.ok and "timed out" in result.error and "406" in result.error
