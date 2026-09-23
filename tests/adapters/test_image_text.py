"""Reading a menu that exists only as an image."""

from __future__ import annotations

import pytest

from app.adapters import image_text

pytestmark = pytest.mark.unit


def test_the_same_image_is_sent_to_the_model_once(tmp_path, monkeypatch):
    """A re-crawl of an unchanged menu must cost nothing. The cache is keyed on
    the image's bytes, not its address, so a renamed upload is still free."""
    monkeypatch.setattr(image_text, "CACHE", tmp_path)
    monkeypatch.setattr(image_text.language_model, "available", lambda: True)
    calls = []

    def ask(system, prompt, tool, **kw):
        calls.append(kw["blocks"])
        return {"legible": True, "text": "Cabernet Sauvignon 14"}

    monkeypatch.setattr(image_text.language_model, "structured", ask)
    first = image_text.read(b"\xff\xd8wine-list")
    second = image_text.read(b"\xff\xd8wine-list")
    assert first == second == ("Cabernet Sauvignon 14", "")
    assert len(calls) == 1


def test_without_a_key_the_reason_says_so_and_nothing_is_cached(tmp_path, monkeypatch):
    monkeypatch.setattr(image_text, "CACHE", tmp_path)
    monkeypatch.setattr(image_text.language_model, "available", lambda: False)
    assert image_text.read(b"\xff\xd8x") == (None, "no Anthropic key configured")
    assert list(tmp_path.iterdir()) == []


def test_an_image_the_model_cannot_read_says_so(tmp_path, monkeypatch):
    monkeypatch.setattr(image_text, "CACHE", tmp_path)
    monkeypatch.setattr(image_text.language_model, "available", lambda: True)
    monkeypatch.setattr(image_text.language_model, "structured",
                        lambda *a, **k: {"legible": False, "text": ""})
    assert image_text.read(b"\xff\xd8blur") == (None, "the model could not read it")


def test_a_png_is_sent_as_a_png(tmp_path, monkeypatch):
    """The Heritage Table's bourbon, scotch and beer list is a PNG. Every image
    was labelled JPEG, the API refused it, and every whisky on the page came
    back unsourced."""
    monkeypatch.setattr(image_text, "CACHE", tmp_path)
    monkeypatch.setattr(image_text.language_model, "available", lambda: True)
    sent = []
    monkeypatch.setattr(image_text.language_model, "structured",
                        lambda *a, **k: sent.append(k["blocks"][0])
                        or {"legible": True, "text": "x"})
    image_text.read(b"\x89PNG\r\n\x1a\nrest")
    assert sent[0]["source"]["media_type"] == "image/png"
