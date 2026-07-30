"""CLI smoke tests — the no-key demo commands run offline and end-to-end."""

from __future__ import annotations

import pytest

from app.cli import main

pytestmark = pytest.mark.functional


def test_research_demo_runs(capsys):
    assert main(["research-demo"]) == 0
    out = capsys.readouterr().out
    assert "The Depot Cafe" in out
    assert "verified" in out
    # entity resolution rejection is surfaced
    assert "J.S.M. Lawn Care" in out


def test_site_demo_runs(capsys):
    assert main(["site-demo"]) == 0
    out = capsys.readouterr().out
    assert "The Depot Cafe" in out
    assert "preview:" in out
    assert "claim" in out  # facts show their backing claim id


def test_discover_without_key_errors(capsys, monkeypatch):
    monkeypatch.setenv("PLACES_PROVIDER", "google")
    monkeypatch.delenv("GOOGLE_PLACES_API_KEY", raising=False)
    assert main(["discover", "Frisco, TX"]) == 2
    assert "GOOGLE_PLACES_API_KEY" in capsys.readouterr().err
