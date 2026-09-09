"""The review bundle must actually stand alone.

Mirrors tests/tools/test_contact_sheet.py's own reasoning for the same
class of bug: a photograph that silently fails to resolve is worse than a
slow build, because it changes what a reader concludes without them
noticing anything is wrong.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def load():
    spec = importlib.util.spec_from_file_location(
        "build_review", Path("tools/build_review.py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules["build_review"] = module
    spec.loader.exec_module(module)
    return module


def test_a_photograph_is_copied_and_linked_relatively(monkeypatch, tmp_path):
    br = load()
    cached = tmp_path / "cache" / "somehash.jpg"
    cached.parent.mkdir(parents=True)
    cached.write_bytes(b"\xff\xd8\xff\xe0")
    dest_dir = tmp_path / "review" / "photos"
    dest_dir.mkdir(parents=True)
    monkeypatch.setattr(br, "PHOTOS", dest_dir)
    monkeypatch.setattr(br.photos_api, "_cache_path", lambda name, width: cached)

    page = '<img src="/photo/3/0">'
    out = br._copy_photographs(page, {"lead_id": 3, "place_photos": ["a"]})

    assert "/photo/3/" not in out
    assert "data:" not in out, "a photograph was inlined rather than linked"
    assert 'src="photos/somehash.jpg"' in out
    copied = dest_dir / "somehash.jpg"
    assert copied.exists() and copied.read_bytes() == cached.read_bytes()


def test_a_photograph_with_no_names_is_left_alone():
    br = load()
    page = '<img src="/photo/3/0">'
    out = br._copy_photographs(page, {"lead_id": 3, "place_photos": []})
    assert out == page


def test_a_photograph_not_yet_cached_is_left_alone_not_blanked(monkeypatch, tmp_path):
    """Better a visibly broken image than a silently missing one — the
    silent kind is what produced the grey rectangles this project's
    contact-sheet tests already guard against."""
    br = load()
    monkeypatch.setattr(br, "PHOTOS", tmp_path / "photos")
    monkeypatch.setattr(br.photos_api, "_cache_path",
                        lambda name, width: tmp_path / "no-such-file.jpg")
    page = '<img src="/photo/9/0">'
    out = br._copy_photographs(page, {"lead_id": 9, "place_photos": ["a"]})
    assert out == page
