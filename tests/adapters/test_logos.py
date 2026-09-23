"""A business's logo, fetched once and served by the workbench."""

from __future__ import annotations

import pytest

from app.adapters import logos

pytestmark = pytest.mark.unit


def test_a_logo_is_downloaded_once_and_its_type_read_from_its_bytes(tmp_path, monkeypatch):
    """Every page view asks for the logo; the business's server should be asked
    once. Fish Shack's logo is a JPEG and The Heritage Table's a PNG, and the
    address does not always say which."""
    monkeypatch.setattr(logos, "CACHE", tmp_path)
    calls = []
    monkeypatch.setattr(logos, "download", lambda url, timeout=15.0:
                        calls.append(url) or (b"\x89PNG\r\n\x1a\nlogo", ""))
    first = logos.fetch("https://heritage.test/logo")
    second = logos.fetch("https://heritage.test/logo")
    assert first == second == (b"\x89PNG\r\n\x1a\nlogo", "image/png")
    assert len(calls) == 1


def test_a_logo_that_cannot_be_downloaded_is_none(tmp_path, monkeypatch):
    monkeypatch.setattr(logos, "CACHE", tmp_path)
    monkeypatch.setattr(logos, "download", lambda url, timeout=15.0: (None, "status 404"))
    assert logos.fetch("https://gone.test/logo.png") is None
