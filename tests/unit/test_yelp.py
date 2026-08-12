"""Yelp Fusion source — the directory that covers local service businesses."""

from __future__ import annotations

import httpx
import pytest

from app.adapters.yelp import YelpSource, parse_yelp_business

pytestmark = pytest.mark.unit

_ROW = {
    "name": "Ryno Lawn Care",
    "display_phone": "(972) 992-5296",
    "phone": "+19729925296",
    "url": "https://www.yelp.com/biz/ryno-lawn-care-frisco",
    "location": {"display_address": ["1310 W Main St", "Frisco, TX 75033"]},
}


def test_parse_yelp_business_maps_address_and_phone():
    place = parse_yelp_business(_ROW)
    assert place.name == "Ryno Lawn Care"
    assert place.address == "1310 W Main St, Frisco, TX 75033"
    assert place.phone == "(972) 992-5296"
    assert place.source_url == "https://www.yelp.com/biz/ryno-lawn-care-frisco"
    assert place.website is None  # Yelp gives its own page, not the business's


def test_parse_falls_back_to_the_raw_phone():
    place = parse_yelp_business({**_ROW, "display_phone": ""})
    assert place.phone == "+19729925296"


def test_parse_handles_a_row_with_no_address():
    place = parse_yelp_business({"name": "X", "location": {}})
    assert place.address is None


def test_lookup_returns_none_without_an_api_key(monkeypatch):
    """No key -> the source is simply absent; it never guesses.

    Clears the env var so a real key in the developer's .env can't mask this.
    """
    monkeypatch.delenv("YELP_API_KEY", raising=False)
    assert YelpSource(api_key=None).lookup("Ryno Lawn Care", "Frisco, TX") is None


def test_lookup_parses_a_live_style_response():
    def handler(request):
        assert request.headers["Authorization"] == "Bearer test-key"  # pragma: allowlist secret
        return httpx.Response(200, json={"businesses": [_ROW]})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    place = YelpSource(api_key="test-key", client=client).lookup(  # pragma: allowlist secret
        "Ryno Lawn Care", "Frisco, TX")
    assert place is not None and place.phone == "(972) 992-5296"


def test_lookup_survives_an_api_error():
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(500)))
    src = YelpSource(api_key="k", client=client)  # pragma: allowlist secret
    assert src.lookup("X", "Y") is None


def test_lookup_handles_no_results():
    client = httpx.Client(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json={"businesses": []})))
    src = YelpSource(api_key="k", client=client)  # pragma: allowlist secret
    assert src.lookup("X", "Y") is None
