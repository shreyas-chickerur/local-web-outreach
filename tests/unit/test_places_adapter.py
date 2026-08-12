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
    details = respx.get(GooglePlacesSource.DETAILS_URL).mock(
        return_value=httpx.Response(200, json={"result": {}})
    )
    out = GooglePlacesSource(api_key="k").search("Frisco, TX", "restaurant")
    assert route.called
    assert details.called  # contact fields are always enriched
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


# --- Place Details enrichment (Text Search omits website + phone) ------------
def _details_client(search_results, details_result):
    def handler(request):
        if "details" in str(request.url):
            return httpx.Response(200, json={"result": details_result})
        return httpx.Response(200, json={"results": search_results})

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_search_enriches_website_and_phone_from_place_details():
    """Regression: Text Search returns neither, so every business looked like it
    had no website and no phone — the email would then claim so, wrongly."""
    client = _details_client(
        [{"place_id": "p1", "name": "Ryno Lawn Care", "formatted_address": "1 Main St"}],
        {"website": "https://rynolawncare.com", "formatted_phone_number": "(972) 992-5296"},
    )
    src = GooglePlacesSource(api_key="k", client=client)  # pragma: allowlist secret
    out = src.search("Frisco, TX", "lawn")
    assert out[0].website == "https://rynolawncare.com"
    assert out[0].phone == "(972) 992-5296"


def test_search_survives_a_failing_details_call():
    def handler(request):
        if "details" in str(request.url):
            return httpx.Response(500)
        return httpx.Response(200, json={"results": [
            {"place_id": "p1", "name": "X", "formatted_address": "1 Main St"}]})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    src = GooglePlacesSource(api_key="k", client=client)  # pragma: allowlist secret
    out = src.search("Frisco, TX")
    assert len(out) == 1 and out[0].website is None  # candidate kept, fields absent


def test_details_can_be_disabled():
    client = _details_client([{"place_id": "p1", "name": "X"}], {"website": "https://x.com"})
    out = GooglePlacesSource(api_key="k", client=client,  # pragma: allowlist secret
                             fetch_details=False).search("Frisco, TX")
    assert out[0].website is None
