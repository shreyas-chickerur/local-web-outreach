"""The contact sheet has to be trustworthy before it is useful.

Its first output was eleven grey rectangles — a generated page asks our own
server for `/photo/<lead>/<n>`, and a screenshot taken from a file:// URL has
no server to ask. I nearly read a conclusion off that: two law firms that
looked identical because neither had loaded its hero.

An instrument that has not been checked against something it should say is not
evidence, so this checks it.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def load():
    spec = importlib.util.spec_from_file_location(
        "contact_sheet", Path("tools/contact_sheet.py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules["contact_sheet"] = module
    spec.loader.exec_module(module)
    return module


def test_a_captured_page_links_its_photographs(monkeypatch, tmp_path):
    """Relative paths to the on-disk cache, not base64 — inlining made a
    single fixture's page 105MB and the whole directory 731MB, which is not
    a large file, it is millions of tokens waiting to truncate a read."""
    sheet = load()
    cached = tmp_path / "somehash.jpg"
    cached.write_bytes(b"\xff\xd8\xff\xe0")
    monkeypatch.setattr(sheet.photos_api, "_cache_path",
                        lambda name, width: cached)
    monkeypatch.setattr(sheet, "OUT", tmp_path / "contact-sheet")
    page = ('<div class="bgimg" style="background-image:url(&quot;'
            '/photo/7/2?w=2400&quot;)"></div>'
            '<img src="/photo/7/0" srcset="/photo/7/0?w=800 800w">')
    out = sheet._link_photographs(
        page, {"lead_id": 7, "place_photos": ["a", "b", "c"]})
    assert "/photo/7/" not in out, "a proxied photograph survived the capture"
    assert "data:" not in out, "a photograph was inlined rather than linked"
    assert out.count("somehash.jpg") == 3


def test_a_photograph_with_no_names_is_left_alone_not_blanked():
    """Better a visibly broken image in the capture than a silently missing
    one — the silent kind is what produced the grey rectangles."""
    sheet = load()
    page = '<img src="/photo/7/0">'
    out = sheet._link_photographs(page, {"lead_id": 7, "place_photos": []})
    assert out == page


def test_a_photograph_not_yet_cached_is_left_alone_not_blanked(monkeypatch):
    """Named but never fetched — `_cache_path` computes a path deterministically
    whether or not the file behind it exists."""
    sheet = load()
    monkeypatch.setattr(sheet.photos_api, "_cache_path",
                        lambda name, width: Path("no/such/file.jpg"))
    page = '<img src="/photo/9/0">'
    out = sheet._link_photographs(page, {"lead_id": 9, "place_photos": ["a"]})
    assert out == page


def test_the_closest_pair_leads_the_sheet():
    """The whole point of looking is to check the instrument, and that is only
    possible with the two most-alike sites side by side."""
    sheet = load()
    cards = [
        {"slug": "far", "axes": [("mood", "night"), ("accent", "teal")]},
        {"slug": "one", "axes": [("mood", "warm"), ("accent", "navy")]},
        {"slug": "two", "axes": [("mood", "warm"), ("accent", "navy")]},
    ]
    ordered = sheet._closest_first(cards)
    assert [c["slug"] for c in ordered[:2]] == ["one", "two"]
    assert "closest pair" in ordered[0]["flag"]
