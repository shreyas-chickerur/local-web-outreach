"""The review bundle must actually stand alone.

Mirrors tests/tools/test_contact_sheet.py's own reasoning for the same
class of bug: a photograph that silently fails to resolve is worse than a
slow build, because it changes what a reader concludes without them
noticing anything is wrong.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

FIXTURES = Path("tests/fixtures/briefs")
OUT = Path(".reviews/review")


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


def test_the_committed_review_bundle_shows_the_corpus_that_shipped(
        monkeypatch, tmp_path):
    """The same defect `test_the_committed_sheet_shows_the_corpus_that_
    shipped` (tests/test_the_instrument_reproduces.py) already caught once
    for the contact sheet — a bundle captured before a code fix landed,
    still showing the pre-fix page — but nothing guarded `.reviews/review/`
    itself, which is why it happened again: `dentist.html` still read "What
    we cook and serve" (the restaurant heading) after Round 4 Phase 3a's
    fix to `_offer_heading` had already landed and every fixture's own
    `render_snapshots.json` hash had already moved.

    Regenerates every fixture through the identical path
    `tools/build_review.py`'s own `main()` uses (frozen direction, in-memory
    db, the same `_copy_photographs` rewrite) and diffs the fresh bytes
    against the committed file. A photo-cache directory is monkeypatched to
    a temp path so this does not write into the real, gitignored
    `.reviews/review/photos/` on every test run — the rewritten HTML string
    itself only depends on the cached file's own name, not which directory
    it was copied into, so this changes nothing about what is compared.
    """
    from app.site.pipeline import STAGES, run_stage, spec_from_config
    from app.site.render import build_from_spec
    from app.store import db, leads, sites

    br = load()
    monkeypatch.setattr(br, "PHOTOS", tmp_path / "photos")
    (tmp_path / "photos").mkdir()

    stale: list[str] = []
    for path in sorted(FIXTURES.glob("*.json")):
        slug = path.stem
        committed = OUT / f"{slug}.html"
        if not committed.exists():
            stale.append(f"{slug} (no committed page at all)")
            continue
        with db.session(":memory:") as conn:
            lead_id = leads.save_brief(conn, json.loads(path.read_text()))
            for stage in STAGES:
                run_stage(conn, lead_id, stage)
            brief = leads.brief_with_overrides(conn, lead_id)
            stored = sites.recall_stage(conn, lead_id, "direction") or {}
            config = dict(stored.get("config") or {})
            assert config.get("read_by") == "frozen", (
                f"{slug} did not replay a frozen direction — this bundle "
                f"would be checked against a different system than the one "
                f"that shipped it")
            spec = spec_from_config(config)
            fresh = br._copy_photographs(build_from_spec(brief, spec), brief)
        if fresh != committed.read_text():
            stale.append(slug)

    assert not stale, (
        f"{stale} in .reviews/review/ no longer match a fresh render — "
        f"regenerate with tools/build_review.py (do not hand-edit the "
        f"committed pages)")
