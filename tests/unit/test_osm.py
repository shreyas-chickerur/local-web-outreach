"""OpenStreetMap second-source adapter + its effect on corroboration."""

from __future__ import annotations

import pytest

from app.adapters.directory import DirectoryPlace, NullDirectorySource
from app.adapters.osm import parse_nominatim_row
from app.core.enums import SourceType
from app.stages.collect import collect_sources

pytestmark = pytest.mark.unit

_ROW = {
    "osm_type": "node", "osm_id": 12345, "name": "JS Lawn Care",
    "address": {"house_number": "7934", "road": "Milestone Ridge Dr",
                "city": "Frisco", "state": "Texas", "postcode": "75035"},
    "extratags": {"phone": "+1-972-555-0148", "website": "https://jslawn.example"},
}


def test_parse_nominatim_row_maps_every_field():
    place = parse_nominatim_row(_ROW)
    assert place.name == "JS Lawn Care"
    assert place.address == "7934 Milestone Ridge Dr, Frisco, Texas, 75035"
    assert place.phone == "+1-972-555-0148"
    assert place.website == "https://jslawn.example"
    assert place.source_url == "https://www.openstreetmap.org/node/12345"


def test_parse_handles_a_row_with_no_street_or_tags():
    place = parse_nominatim_row({"address": {"city": "Frisco"}}, fallback_name="Acme")
    assert place.name == "Acme"
    assert place.address is None  # no street -> no address claimed
    assert place.phone is None and place.website is None


def test_parse_reads_the_contact_prefixed_tags():
    place = parse_nominatim_row(
        {**_ROW, "extratags": {"contact:phone": "(972) 555-0100",
                               "contact:website": "https://x.example"}}
    )
    assert place.phone == "(972) 555-0100"
    assert place.website == "https://x.example"


class _Biz:
    name, location, place_id = "JS Lawn Care", "Frisco, TX", "pid1"
    address, phone = "7934 Milestone Ridge Dr, Frisco, TX 75035", "(972) 555-0148"
    existing_site_url, contact_email = None, None


class _Dir:
    name = 'test'

    def __init__(self, place):
        self._p = place

    def lookup(self, name, location):  # noqa: ARG002
        return self._p


class _Fetcher:
    def fetch(self, url):  # noqa: ARG002
        raise AssertionError("must not fetch when there is no website")


def test_osm_supplies_the_second_source_for_a_business_with_no_website():
    """The whole point: without OSM this business has ONE source, so nothing can
    ever be corroborated and every fact stays UNVERIFIED."""
    place = DirectoryPlace(name="JS Lawn Care", address="7934 Milestone Ridge Dr, Frisco, TX",
                     phone="(972) 555-0148", website=None,
                     source_url="https://www.openstreetmap.org/node/1")
    collected = collect_sources(_Biz(), _Fetcher(), [_Dir(place)])

    assert [s.source_type for s in collected.sources] == [SourceType.GBP, SourceType.DIRECTORY]
    # the phone is now asserted by two INDEPENDENT sources -> corroboration is real
    phone_sources = [s.source_url for s in collected.sources
                     for c in s.claims if c.field == "phone"]
    assert len(phone_sources) == 2
    assert len(set(phone_sources)) == 2  # genuinely distinct sources


def test_no_osm_match_leaves_the_single_source_alone():
    collected = collect_sources(_Biz(), _Fetcher(), [NullDirectorySource()])
    assert [s.source_type for s in collected.sources] == [SourceType.GBP]


def test_osm_row_without_useful_tags_adds_no_source():
    """An OSM hit that carries neither address nor phone is not a source."""
    place = DirectoryPlace(name="X", address=None, phone=None, website=None,
                     source_url="https://www.openstreetmap.org/node/2")
    collected = collect_sources(_Biz(), _Fetcher(), [_Dir(place)])
    assert [s.source_type for s in collected.sources] == [SourceType.GBP]
