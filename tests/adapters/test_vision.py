"""Looking at the photographs.

The vision pass is a source like any other, so nothing it returns is trusted
because it came back: every field is checked against a closed set, and the one
piece of text it may put on a page is checked against the same claim expression
that guards every other sentence.
"""

from __future__ import annotations

import re

import httpx
import pytest

from app.adapters import claude, vision

pytestmark = pytest.mark.unit


def answered(payload: dict) -> httpx.Response:
    return httpx.Response(200, json={
        "content": [{"type": "tool_use", "name": "describe", "input": payload}]})


# Bytes that actually are a JPEG. The media type is read from these now, so a
# placeholder string is rejected before anything is sent — which is the point.
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 32

ENTRY = {"index": 0, "subject": "dish", "is_hero_candidate": True,
         "quality": 5, "alt_text": "A plated fish with greens"}


# --- validation ---------------------------------------------------------- #

def test_a_subject_outside_the_enumeration_becomes_unclear():
    out = vision._clean({**ENTRY, "subject": "banquet"}, "/a")
    assert out["subject"] == "unclear"


def test_a_quality_outside_one_to_five_is_not_believed():
    for bad in (0, 9, "five", None):
        assert vision._clean({**ENTRY, "quality": bad}, "/a")["quality"] == 1


def test_alt_text_that_asserts_something_is_dropped():
    """The one place model-written text reaches the page. Describing what is
    visible is checkable by looking; "award-winning" is not."""
    out = vision._clean(
        {**ENTRY, "alt_text": "Chef Marco's award-winning signature dish"}, "/a")
    assert out["alt_text"] == ""


def test_alt_text_that_only_describes_survives():
    out = vision._clean(ENTRY, "/a")
    assert out["alt_text"] == "A plated fish with greens"


def test_a_colour_that_is_not_a_colour_is_dropped():
    out = vision._clean(
        {**ENTRY, "dominant_colours": ["#a83400", "cobalt", "#fff", "#zzz"]},
        "/a")
    assert out["dominant_colours"] == ["#a83400", "#fff"]


def test_unknown_positions_and_luminances_fall_back():
    out = vision._clean(
        {**ENTRY, "subject_position": "diagonal",
         "headline_region_luminance": "glowing"}, "/a")
    assert out["subject_position"] == "full"
    assert out["headline_region_luminance"] == "mixed"


# --- the call ------------------------------------------------------------ #

def test_no_key_means_no_answer_and_no_crash(monkeypatch):
    monkeypatch.setattr(claude, "available", lambda: False)
    assert vision.look(["/photo/1/0"]) == {}


def test_a_failed_call_loses_the_batch_not_the_build(monkeypatch):
    """A lead whose photographs cannot be looked at has fewer facts, not a
    broken build."""
    monkeypatch.setattr(claude, "available", lambda: True)
    monkeypatch.setattr(vision, "thumbnail", lambda url, names: JPEG)

    def boom(*a, **kw):
        raise claude.ClaudeError("rate limited")

    monkeypatch.setattr(claude, "structured", boom)
    assert vision.look(["/photo/1/0"]) == {}


def test_answers_are_matched_to_images_by_index(monkeypatch):
    monkeypatch.setattr(claude, "available", lambda: True)
    monkeypatch.setattr(vision, "thumbnail", lambda url, names: JPEG)
    monkeypatch.setattr(claude, "structured", lambda *a, **kw: {"images": [
        {**ENTRY, "index": 1, "subject": "room"},
        {**ENTRY, "index": 0, "subject": "dish"},
    ]})
    seen = vision.look(["/photo/1/0", "/photo/1/1"])
    assert seen["/photo/1/0"]["subject"] == "dish"
    assert seen["/photo/1/1"]["subject"] == "room"


def test_an_index_pointing_nowhere_is_discarded(monkeypatch):
    monkeypatch.setattr(claude, "available", lambda: True)
    monkeypatch.setattr(vision, "thumbnail", lambda url, names: JPEG)
    monkeypatch.setattr(claude, "structured", lambda *a, **kw: {"images": [
        {**ENTRY, "index": 7}, {**ENTRY, "index": -1}, {**ENTRY, "index": "0"},
    ]})
    assert vision.look(["/photo/1/0"]) == {}


def test_an_image_we_cannot_thumbnail_is_skipped_not_sent(monkeypatch):
    sent = {}
    monkeypatch.setattr(claude, "available", lambda: True)
    monkeypatch.setattr(vision, "thumbnail",
                        lambda url, names: None if url.endswith("0") else JPEG)

    def capture(system, prompt, tool, **kw):
        sent["blocks"] = len(kw.get("blocks") or [])
        return {"images": [{**ENTRY, "index": 0}]}

    monkeypatch.setattr(claude, "structured", capture)
    seen = vision.look(["/photo/1/0", "/photo/1/1"])
    assert sent["blocks"] == 1
    assert "/photo/1/1" in seen and "/photo/1/0" not in seen


def test_an_oversized_scraped_image_is_not_uploaded(monkeypatch):
    """The API rejects anything past five megabytes and resizes past 1568px
    anyway, so this is checked here rather than discovered in production."""
    huge = b"\x89PNG\r\n\x1a\n" + b"\x00" * 4 + b"IHDR" + \
        (9000).to_bytes(4, "big") + (9000).to_bytes(4, "big")

    class Response:
        status_code = 200
        content = huge

    monkeypatch.setattr(vision.httpx, "get", lambda *a, **kw: Response())
    assert vision.thumbnail("https://x/huge.png", ()) is None


def test_the_request_carries_images_and_forces_the_tool(monkeypatch):
    monkeypatch.setattr(claude.config, "anthropic_api_key",
                        lambda: "k")  # pragma: allowlist secret
    import respx
    with respx.mock:
        route = respx.post(claude.MESSAGES_URL).mock(
            return_value=answered({"images": [ENTRY]}))
        claude.structured("sys", "go", vision._tool(1),
                          blocks=[claude.image_block(b"bytes")])
        body = route.calls[0].request.content.decode()
    assert '"type": "image"' in body or '"type":"image"' in body
    assert "tool_choice" in body


# --- one bad picture must not take the batch with it --------------------- #

def test_the_media_type_comes_from_the_bytes_not_the_file_name(monkeypatch):
    """PNG bytes sent as image/jpeg are rejected, and the API rejects the whole
    request when any one block is unusable — so eighteen photographs came back
    undescribed because four of them were PNGs behind a .jpg-shaped guess."""
    sent = {}
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 40
    monkeypatch.setattr(claude, "available", lambda: True)
    monkeypatch.setattr(vision, "thumbnail", lambda url, names: png)

    def capture(system, prompt, tool, **kw):
        sent["type"] = (kw["blocks"][0]["source"]["media_type"])
        return {"images": [{**ENTRY, "index": 0}]}

    monkeypatch.setattr(claude, "structured", capture)
    vision.look(["/photo/1/0"])
    assert sent["type"] == "image/png"


def test_a_format_the_api_cannot_read_is_skipped_not_guessed(monkeypatch):
    avif = b"\x00\x00\x00 ftypavif" + b"\x00" * 40
    monkeypatch.setattr(claude, "available", lambda: True)
    monkeypatch.setattr(vision, "thumbnail", lambda url, names: avif)
    monkeypatch.setattr(claude, "structured",
                        lambda *a, **kw: pytest.fail("should not have asked"))
    assert vision.look(["/photo/1/0"]) == {}


def test_a_failing_batch_is_split_so_the_good_pictures_survive(monkeypatch):
    """The failure that lost both law firms: one unusable block, eighteen
    photographs undescribed, and the build blocked on all of them."""
    monkeypatch.setattr(claude, "available", lambda: True)
    monkeypatch.setattr(vision, "thumbnail",
                        lambda url, names: b"\xff\xd8\xff" + url.encode())

    calls = {"n": 0}

    def flaky(system, prompt, tool, **kw):
        calls["n"] += 1
        urls = re.findall(r"image \d+: (\S+)", prompt)
        if any(u.endswith("/2") for u in urls) and len(urls) > 1:
            raise claude.ClaudeError("could not process image 2")
        if any(u.endswith("/2") for u in urls):
            raise claude.ClaudeError("could not process image 2")
        return {"images": [{**ENTRY, "index": i} for i in range(len(urls))]}

    monkeypatch.setattr(claude, "structured", flaky)
    seen = vision.look([f"/photo/1/{i}" for i in range(4)])
    assert set(seen) == {"/photo/1/0", "/photo/1/1", "/photo/1/3"}
    assert calls["n"] > 1, "the batch was never split"


def test_a_single_bad_picture_gives_up_rather_than_recursing(monkeypatch):
    monkeypatch.setattr(claude, "available", lambda: True)
    monkeypatch.setattr(vision, "thumbnail", lambda url, names: b"\xff\xd8\xffx")

    def always(*a, **kw):
        raise claude.ClaudeError("no")

    monkeypatch.setattr(claude, "structured", always)
    assert vision.look(["/photo/1/0"]) == {}


def test_an_answer_that_is_not_shaped_like_the_schema_is_survived(monkeypatch):
    """A schema is not a guarantee. Bare strings came back in this array for
    two of eleven fixtures, and an unguarded `.get` took the whole lead down at
    the first stage."""
    monkeypatch.setattr(claude, "available", lambda: True)
    monkeypatch.setattr(vision, "thumbnail", lambda url, names: JPEG)
    monkeypatch.setattr(claude, "structured", lambda *a, **kw: {"images": [
        "a plate of food", None, 42, {**ENTRY, "index": 0}]})
    seen = vision.look(["/photo/1/0"])
    assert seen["/photo/1/0"]["subject"] == "dish"
