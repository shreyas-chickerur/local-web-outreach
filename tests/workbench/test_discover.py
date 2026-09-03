"""Finding prospects near a point."""

from __future__ import annotations

import pytest

from app.adapters.directory import DirectoryPlace
from app.adapters.site_fetch import FetchResult
from app.store import db
from app.workbench import discover
from app.workbench.categories import BY_KEY

pytestmark = pytest.mark.unit


@pytest.fixture()
def conn(tmp_path):
    connection = db.connect(tmp_path / "t.db")
    yield connection
    connection.close()


class _Fetcher:
    def __init__(self, html="<html><body>" + "word " * 400 + "</body></html>"):
        self.html, self.calls = html, 0

    def fetch(self, url):
        self.calls += 1
        return FetchResult(ok=True, status=200, final_url=url, html=self.html,
                           elapsed_ms=1)


def _fake_places(monkeypatch, rows):
    monkeypatch.setattr(discover, "places", lambda *a, **k: rows)


def test_a_repeated_name_in_one_search_is_a_chain(monkeypatch, conn):
    rows = [DirectoryPlace(name="Big Brand", address=f"{i} Main St", phone=None,
                           website=None, source_url=f"https://g/{i}")
            for i in range(3)]
    _fake_places(monkeypatch, rows)
    found = discover.find(conn, "key", 33.1, -96.8, BY_KEY["shops"],
                          fetcher=_Fetcher())
    assert all(p["is_chain"] for p in found)


def test_results_are_cached_so_a_reload_costs_nothing(monkeypatch, conn):
    calls = {"n": 0}

    def counted(*a, **k):
        calls["n"] += 1
        return [DirectoryPlace(name="Solo Shop", address="1 Main St", phone=None,
                               website=None, source_url="https://g/1")]
    monkeypatch.setattr(discover, "places", counted)

    fetcher = _Fetcher()
    discover.find(conn, "key", 33.1, -96.8, BY_KEY["shops"], fetcher=fetcher)
    discover.find(conn, "key", 33.1, -96.8, BY_KEY["shops"], fetcher=fetcher)
    assert calls["n"] == 1

    discover.find(conn, "key", 33.1, -96.8, BY_KEY["shops"], fetcher=fetcher,
                  refresh=True)
    assert calls["n"] == 2


def test_a_site_that_will_not_load_does_not_sink_the_page(monkeypatch, conn):
    class Boom:
        def fetch(self, url):
            raise RuntimeError("connection reset")

    _fake_places(monkeypatch, [DirectoryPlace(
        name="Solo Shop", address="1 Main St", phone=None,
        website="https://broken.example", source_url="https://g/1")])
    found = discover.find(conn, "key", 33.1, -96.8, BY_KEY["shops"], fetcher=Boom())
    assert len(found) == 1


def test_a_blocked_site_is_not_recorded_as_down(monkeypatch, conn):
    """Being refused says nothing about the business, so it must not be scored
    as though their site were broken."""
    class Blocked:
        def fetch(self, url):
            return FetchResult(ok=False, status=403, final_url=url, html="",
                               elapsed_ms=1)

    _fake_places(monkeypatch, [DirectoryPlace(
        name="Solo Shop", address="1 Main St", phone=None,
        website="https://guarded.example", source_url="https://g/1")])
    found = discover.find(conn, "key", 33.1, -96.8, BY_KEY["shops"],
                          fetcher=Blocked())
    assert found[0]["site_reachable"] is None
    assert not any("does not load" in r for r in found[0]["reasons"])
