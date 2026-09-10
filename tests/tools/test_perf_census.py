"""The performance harness's own honesty, Round 6 Phase 2.

Two real measurement bugs found and fixed: every `/photo/` reference
collapsed to the same `MAX_WIDTH` file regardless of which `srcset`/
`image-set` candidate a real mobile browser would select, and every
externally-hosted image (a business's own "recent jobs" photos, pulled
directly from their live site rather than through this project's own
proxy) was silently skipped from the weight total entirely.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import time
from pathlib import Path

import pytest

from tools.contact_sheet import _cdp_session, chrome

pytestmark = pytest.mark.unit


def load():
    spec = importlib.util.spec_from_file_location(
        "perf_census", Path("tools/perf_census.py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules["perf_census"] = module
    spec.loader.exec_module(module)
    return module


def test_the_og_image_absolute_url_survives_width_aware_linking(
        monkeypatch, tmp_path):
    """The exact same class of bug Phase 1a fixed in
    `build_review._copy_photographs` — found again writing this
    function, in new code rather than old. `render.absolute()`'s
    `http://127.0.0.1:8099/photo/1/6` must not be touched: nothing here
    is meant to rewrite an absolute URL, only a bare proxied reference a
    file:// page cannot otherwise reach."""
    pc = load()
    cached = tmp_path / "cache.jpg"
    cached.write_bytes(b"\xff\xd8\xff\xe0")
    monkeypatch.setattr(pc.photos_api, "_cache_path", lambda name, width: cached)
    monkeypatch.setattr(pc.photos_api, "fetch", lambda *a, **kw: None)
    monkeypatch.setattr(pc, "OUT", tmp_path)

    page = '<meta property="og:image" content="http://127.0.0.1:8099/photo/3/0">'
    out = pc._link_photographs_width_aware(page, {"lead_id": 3, "place_photos": ["a"]}, "")

    assert "http://127.0.0.1:8099/photo/3/0" in out
    assert "8099.." not in out and "8099cache" not in out


def test_a_width_tagged_reference_resolves_to_its_own_tier(monkeypatch, tmp_path):
    """The bug itself: `?w=800` and `?w=2400` used to both resolve to the
    identical `MAX_WIDTH` cached file. They must now resolve to two
    DIFFERENT files — proof the width actually reached `_cache_path`."""
    pc = load()
    monkeypatch.setattr(pc, "OUT", tmp_path)

    def fake_cache_path(name, width):
        path = tmp_path / f"cache-{width}.jpg"
        path.write_bytes(b"\xff\xd8\xff\xe0" + bytes(width % 256))
        return path

    monkeypatch.setattr(pc.photos_api, "_cache_path", fake_cache_path)
    monkeypatch.setattr(pc.photos_api, "fetch", lambda *a, **kw: None)

    page = 'srcset="/photo/3/0?w=800 800w, /photo/3/0?w=2400 2400w"'
    out = pc._link_photographs_width_aware(page, {"lead_id": 3, "place_photos": ["a"]}, "")

    assert "cache-800.jpg" in out
    assert "cache-2400.jpg" in out


def test_a_bare_reference_with_no_width_defaults_to_max_width(monkeypatch, tmp_path):
    """Matches `app.web.server`'s own real `/photo/` route: `width =
    nearest_width(asked) if asked else MAX_WIDTH` — a bare `src=` with no
    `?w=` gets the same default a real request without one would."""
    pc = load()
    monkeypatch.setattr(pc, "OUT", tmp_path)
    seen_widths = []

    def fake_cache_path(name, width):
        seen_widths.append(width)
        path = tmp_path / "cache.jpg"
        path.write_bytes(b"\xff\xd8\xff\xe0")
        return path

    monkeypatch.setattr(pc.photos_api, "_cache_path", fake_cache_path)
    monkeypatch.setattr(pc.photos_api, "fetch", lambda *a, **kw: None)

    pc._link_photographs_width_aware(
        '<img src="/photo/3/0">', {"lead_id": 3, "place_photos": ["a"]}, "")

    assert seen_widths == [pc.photos_api.MAX_WIDTH]


def test_a_missing_width_variant_is_fetched(monkeypatch, tmp_path):
    """Not just resolved to the right filename — actually fetched (the
    real Google Places API call `app.web.server`'s live route would
    make) when that tier is not already cached, so the file genuinely
    exists for measurement to read afterward."""
    pc = load()
    monkeypatch.setattr(pc, "OUT", tmp_path)
    fetched = []

    def _slug(name: str, width: int) -> str:
        return f"{name.replace('/', '_')}-{width}.jpg"

    def fake_cache_path(name, width):
        return tmp_path / _slug(name, width)

    def fake_fetch(api_key, name, width=None, **kw):
        fetched.append((name, width))
        (tmp_path / _slug(name, width)).write_bytes(b"\xff\xd8\xff\xe0")
        return b"\xff\xd8\xff\xe0"

    monkeypatch.setattr(pc.photos_api, "_cache_path", fake_cache_path)
    monkeypatch.setattr(pc.photos_api, "fetch", fake_fetch)

    pc._link_photographs_width_aware(
        '<img src="/photo/3/0?w=800">', {"lead_id": 3, "place_photos": ["places/x"]},
        "real-key")

    assert fetched == [("places/x", 800)]


def test_an_external_image_is_cached_and_reused(monkeypatch, tmp_path):
    pc = load()
    monkeypatch.setattr(pc, "EXTERNAL_CACHE", tmp_path / "external")
    monkeypatch.setattr(pc, "OUT", tmp_path)
    calls = []

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b"fake-image-bytes"

    def fake_urlopen(req, timeout=None):
        calls.append(req.full_url)
        return FakeResponse()

    monkeypatch.setattr(pc.urllib.request, "urlopen", fake_urlopen)

    page = 'src="https://example.com/photo.jpg"'
    first = pc._link_external_images(page)
    second = pc._link_external_images(page)

    assert len(calls) == 1, "the second call must reuse the cache, not re-fetch"
    assert "example.com" not in first
    assert first == second
    rewritten_path = first.split('"')[1]
    assert (pc.OUT / rewritten_path).exists()
    assert (pc.OUT / rewritten_path).read_bytes() == b"fake-image-bytes"


def test_an_unreachable_external_image_is_left_as_its_original_url(monkeypatch, tmp_path):
    """A business's site having moved or removed an asset since this
    fixture was captured is a real, disclosed fact — the reference is
    left pointing at the real (now-broken) URL rather than faked with a
    placeholder file that would silently read as content that exists."""
    pc = load()
    monkeypatch.setattr(pc, "EXTERNAL_CACHE", tmp_path / "external")

    def fake_urlopen(req, timeout=None):
        raise pc.urllib.error.URLError("not found")

    monkeypatch.setattr(pc.urllib.request, "urlopen", fake_urlopen)

    page = 'src="https://example.com/gone.jpg"'
    out = pc._link_external_images(page)
    assert out == page


@pytest.mark.skipif(chrome() is None, reason="no Chrome/Chromium on this machine")
def test_the_synthetic_inp_click_never_actually_navigates_the_tab(tmp_path):
    """A real, previously-undiscovered bug, found running this fix against
    `bare-trade`: both of its CTAs are plain `<a href>` links straight to a
    Google Maps search, and the synthetic click `_FIND_CLICK_TARGET`/
    `Input.dispatchMouseEvent` dispatches for an INP sample actually
    navigated the headless tab there — replacing the fixture's own
    document with Google Maps' mid-measurement, which is what hung the
    weight-measurement scroll step that runs afterward, not anything
    about the fixture itself. `_OBSERVER_SCRIPT`'s capture-phase click
    guard must survive on ANY page carrying a real external link as its
    first clickable element, confirmed here with a real browser and a
    real click, not just a JS syntax check."""
    pc = load()
    page = tmp_path / "external-cta.html"
    page.write_text(
        '<!doctype html><html><body>'
        '<a class="cta" href="https://www.google.com/maps/search/?q=x">'
        'Get directions</a>'
        '</body></html>')

    binary = chrome()
    with _cdp_session(binary, page, 390, 844, 1.0) as call:
        call("Runtime.evaluate", {"expression": pc._OBSERVER_SCRIPT})
        target = call("Runtime.evaluate", {
            "expression": pc._FIND_CLICK_TARGET, "returnByValue": True})
        point = target["result"]["result"]["value"]
        assert point, "the test page's own CTA was not found"
        xy = json.loads(point)
        call("Input.dispatchMouseEvent", {
            "type": "mousePressed", "x": xy["x"], "y": xy["y"],
            "button": "left", "clickCount": 1})
        call("Input.dispatchMouseEvent", {
            "type": "mouseReleased", "x": xy["x"], "y": xy["y"],
            "button": "left", "clickCount": 1})
        time.sleep(0.5)
        location = call("Runtime.evaluate", {
            "expression": "location.href", "returnByValue": True})
        href = location["result"]["result"]["value"]
        assert "google.com/maps" not in href, (
            f"the synthetic click navigated the tab away: {href}")
