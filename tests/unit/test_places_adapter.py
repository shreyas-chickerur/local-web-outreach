"""Contract tests for the real HTTP adapters, with the network mocked (respx)."""

from __future__ import annotations

import httpx
import pytest
import respx

from app.adapters.places import GooglePlacesSource
from app.adapters.site_fetch import HttpSiteFetcher

pytestmark = pytest.mark.unit


@respx.mock
def test_google_places_source_parses_results():
    route = respx.get(GooglePlacesSource.BASE_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "results": [
                    {
                        "place_id": "abc123",
                        "name": "The Depot Cafe",
                        "formatted_address": "6733 W Main St, Frisco, TX",
                        "rating": 4.3,
                        "user_ratings_total": 202,
                    }
                ]
            },
        )
    )
    out = GooglePlacesSource(api_key="k").search("Frisco, TX", "restaurant")
    assert route.called
    assert len(out) == 1
    c = out[0]
    assert c.place_id == "abc123"
    assert c.name == "The Depot Cafe"
    assert c.review_count == 202
    assert c.location == "Frisco, TX"


@respx.mock
def test_http_site_fetcher_ok():
    respx.get("https://acme.example").mock(
        return_value=httpx.Response(200, html="<html><body>hi</body></html>")
    )
    r = HttpSiteFetcher().fetch("https://acme.example")
    assert r.ok is True
    assert r.status == 200
    assert "hi" in r.html


@respx.mock
def test_http_site_fetcher_handles_connect_error():
    respx.get("https://dead.example").mock(side_effect=httpx.ConnectError("boom"))
    r = HttpSiteFetcher().fetch("https://dead.example")
    assert r.ok is False
    assert r.status is None
    assert r.error is not None


@respx.mock
def test_http_site_fetcher_4xx_is_not_ok():
    respx.get("https://gone.example").mock(return_value=httpx.Response(404, html="nope"))
    r = HttpSiteFetcher().fetch("https://gone.example")
    assert r.ok is False
    assert r.status == 404
