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


def test_the_og_image_absolute_url_is_never_corrupted(monkeypatch, tmp_path):
    """`app.site.render.absolute()` builds a real, server-reachable URL for
    the og:image meta tag — `http://127.0.0.1:8099/photo/1/6` — the one
    place `/photo/<lead>/<n>` appears NOT freshly preceded by a quote,
    `&quot;`, or a `srcset` comma, but by the port number's own last digit.
    The old regex matched there anyway and ate the leading slash: found on
    17 of 19 committed pages as
    `http://127.0.0.1:8099photos/<hash>.jpg`. This is metadata only — no
    `<img>` tag uses `absolute()` — but a malformed URL there is still a
    real, checkable bug a link-preview fetch would hit."""
    br = load()
    cached = tmp_path / "cache" / "somehash.jpg"
    cached.parent.mkdir(parents=True)
    cached.write_bytes(b"\xff\xd8\xff\xe0")
    dest_dir = tmp_path / "review" / "photos"
    dest_dir.mkdir(parents=True)
    monkeypatch.setattr(br, "PHOTOS", dest_dir)
    monkeypatch.setattr(br.photos_api, "_cache_path", lambda name, width: cached)

    page = ('<meta property="og:image" '
           'content="http://127.0.0.1:8099/photo/3/0">')
    out = br._copy_photographs(page, {"lead_id": 3, "place_photos": ["a"]})

    assert "http://127.0.0.1:8099/photo/3/0" in out, (
        "the og:image URL must survive untouched — it is the one legitimate "
        "absolute reference this function is not meant to rewrite")
    assert "8099photos/" not in out, "the leading slash was eaten again"


def test_a_full_srcset_list_rewrites_every_entry(monkeypatch, tmp_path):
    """The one legitimate context where `/photo/` is NOT preceded by a
    fresh quote or `&quot;` — a later width entry in the same `srcset`
    list is preceded by `, ` instead. The lookbehind fix must not
    over-correct and leave these unmatched."""
    br = load()
    cached = tmp_path / "cache" / "somehash.jpg"
    cached.parent.mkdir(parents=True)
    cached.write_bytes(b"\xff\xd8\xff\xe0")
    dest_dir = tmp_path / "review" / "photos"
    dest_dir.mkdir(parents=True)
    monkeypatch.setattr(br, "PHOTOS", dest_dir)
    monkeypatch.setattr(br.photos_api, "_cache_path", lambda name, width: cached)

    page = ('srcset="/photo/3/0?w=800 800w, /photo/3/0?w=1600 1600w, '
           '/photo/3/0?w=2400 2400w"')
    out = br._copy_photographs(page, {"lead_id": 3, "place_photos": ["a"]})

    assert "/photo/3/" not in out
    assert out.count("photos/somehash.jpg") == 3


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

    # An empty local photo cache is an environment fact, not staleness —
    # `_copy_photographs` can only rewrite a `/photo/` URL when the cached
    # file it points at exists on disk (see `_cache_path`/`cached.exists()`
    # above); with nothing cached, every URL comes back UNCHANGED, which
    # will never match a committed page that WAS built with a populated
    # cache. That reads as all nineteen fixtures stale regardless of
    # whether anything actually moved — hit directly on a machine that
    # has run `make check` but never `tools/contact_sheet.py` or
    # `tools/build_review.py` against a live key. Skipped, not xfailed:
    # there is no assertion this can make either way without the cache.
    if not any(br.photos_api.CACHE.glob("*.jpg")):
        pytest.skip(
            f"{br.photos_api.CACHE} is empty — this machine has never "
            f"cached a photograph, so _copy_photographs cannot rewrite a "
            f"single /photo/ URL and every fixture would read as stale "
            f"regardless of whether the bundle actually moved. Run "
            f"tools/build_review.py once (needs a Google Places API key) "
            f"to populate the cache, then re-run this test.")

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


# Real image formats this bundle actually contains, sniffed from the first
# bytes rather than trusted from the `.jpg` extension every cached file
# gets regardless of its real format — a real reviewer's browser sniffs
# content the same way, but this test should not need one running to say
# whether a referenced file is a real image or a truncated/empty one.
_MAGIC = (
    (b"\xff\xd8\xff", "JPEG"),
    (b"\x89PNG\r\n\x1a\n", "PNG"),
    (b"GIF87a", "GIF"), (b"GIF89a", "GIF"),
    (b"RIFF", "WEBP"),  # a real WEBP also has "WEBP" at offset 8; close enough to rule out garbage
)


def test_every_referenced_photograph_is_a_real_non_empty_image():
    """Round 5's freshness guard proves the referenced FILENAMES match a
    fresh render; it does not open any of them. A page whose <img> silently
    404s or points at zero bytes is exactly how this project nearly read a
    conclusion off eleven grey rectangles (BRIEF §1) — checked here without
    needing a browser, so it runs on every `make check` rather than only
    when someone remembers to look."""
    import re

    missing: list[str] = []
    empty: list[str] = []
    unrecognised: list[str] = []
    for html_file in sorted(OUT.glob("*.html")):
        if html_file.name == "index.html":
            continue
        text = html_file.read_text()
        for ref in sorted(set(re.findall(r'photos/[a-f0-9]+\.(?:jpg|png|webp|gif)',
                                         text))):
            path = OUT / ref
            if not path.exists():
                missing.append(f"{html_file.name} -> {ref}")
                continue
            data = path.read_bytes()[:16]
            if not data:
                empty.append(f"{html_file.name} -> {ref}")
            elif not any(data.startswith(magic) for magic, _ in _MAGIC):
                unrecognised.append(f"{html_file.name} -> {ref}")

    assert not missing, f"referenced but absent from disk: {missing}"
    assert not empty, f"referenced but zero bytes: {empty}"
    assert not unrecognised, (
        f"referenced files whose content is not a recognised image format "
        f"(garbage or truncated, whatever the extension claims): "
        f"{unrecognised}")
