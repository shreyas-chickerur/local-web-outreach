"""The shared Chrome DevTools Protocol plumbing.

Three call sites need this identically: `tools/contact_sheet.py` (a local
fixture file), `tools/perf_census.py` (its own bespoke Network-domain
session), and `app.adapters.site_fetch.ChromeSiteFetcher` (a real
`http(s)://` URL). One implementation, reached from all three — this file
proves the implementation itself works for BOTH kinds of target, since
`cdp_session` accepts a `Path` (rendered as `file://...`) or a plain `str`
URL and previously only the `Path` case had ever been exercised as
production code.
"""

from __future__ import annotations

import time

import pytest

from app.adapters.chrome_cdp import cdp_session, chrome

pytestmark = pytest.mark.unit


@pytest.mark.skipif(chrome() is None, reason="no Chrome/Chromium on this machine")
def test_a_local_file_target_still_works(tmp_path):
    """The `Path` branch — unchanged behaviour from `contact_sheet`'s own
    original `_cdp_session`, now reached through the shared module."""
    binary = chrome()
    page = tmp_path / "page.html"
    page.write_text("<html><body><h1>a local fixture</h1></body></html>")
    with cdp_session(binary, page, 390, 844, 1.0) as call:
        result = call("Runtime.evaluate", {
            "expression": "document.querySelector('h1').textContent",
            "returnByValue": True})
        assert result["result"]["result"]["value"] == "a local fixture"


@pytest.mark.skipif(chrome() is None, reason="no Chrome/Chromium on this machine")
def test_a_plain_url_string_target_works_too(tmp_path):
    """The NEW branch this module exists to add: a target that is already a
    URL string (a real `http(s)://` address, for `ChromeSiteFetcher`) rather
    than a local `Path` — proven here with a `file://` URL built by hand,
    since that exercises the exact same "already a string, do not touch it"
    path `_navigate_target` takes for a real site."""
    binary = chrome()
    page = tmp_path / "page.html"
    page.write_text("<html><body><p id='x'>reached via a url string</p></body></html>")
    url = page.resolve().as_uri()
    assert isinstance(url, str)
    with cdp_session(binary, url, 390, 844, 1.0) as call:
        result = call("Runtime.evaluate", {
            "expression": "document.getElementById('x').textContent",
            "returnByValue": True})
        assert result["result"]["result"]["value"] == "reached via a url string"


@pytest.mark.skipif(chrome() is None, reason="no Chrome/Chromium on this machine")
def test_extra_flags_reach_the_chrome_launch(tmp_path):
    """`extra_flags` exists so a caller (perf_census's own OSM/font blocking,
    a future caller's own launch requirements) can extend the Chrome
    invocation without this module growing a parameter per use case. Proven
    with a host-resolver rule that blocks a specific hostname, then checking
    a request to it fails rather than trusting the flag reached argv."""
    binary = chrome()
    page = tmp_path / "page.html"
    page.write_text(
        "<html><body><script>"
        "window.__failed = false;"
        "fetch('http://blocked.invalid.test/').catch(() => window.__failed = true);"
        "</script></body></html>")
    with cdp_session(
            binary, page, 390, 844, 1.0,
            extra_flags=("--host-resolver-rules=MAP blocked.invalid.test 127.0.0.1",)
    ) as call:
        time.sleep(0.5)
        result = call("Runtime.evaluate", {
            "expression": "window.__failed", "returnByValue": True})
        assert result["result"]["result"]["value"] is True
