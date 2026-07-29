"""Real, hand-verified Frisco, TX research data for the no-key research demo and
the capability-A eval.

These are actual sources gathered during the M0 research pass. Depot Cafe has
strong multi-source corroboration (address + phone from independent directories)
plus single-source and missing fields; JS Lawn Care is a thin-data service
business whose sources include a look-alike ("J.S.M. Lawn Care") that entity
resolution must refuse to merge.
"""

from __future__ import annotations

from app.ai.research_runner import RawClaim, SourceRecord
from app.core.enums import SourceType

_DEPOT = "The Depot Cafe"
_DEPOT_ADDR = "6733 W Main St, Frisco, TX 75034"
_DEPOT_PHONE = "(972) 377-0707"
_YELP = "https://www.yelp.com/biz/the-depot-cafe-frisco"
_YAHOO = "https://local.yahoo.com/info-18617284-the-depot-cafe"
_SITE = "https://depotcafefrisco.com/"


def _c(field: str, value: str, url: str, stype: SourceType) -> RawClaim:
    return RawClaim(field=field, value=value, source_url=url, source_type=stype)


DEPOT_CAFE_SOURCES = [
    SourceRecord(
        source_type=SourceType.YELP, source_url=_YELP,
        entity_name=_DEPOT, entity_address=_DEPOT_ADDR, entity_phone=_DEPOT_PHONE,
        claims=[
            _c("address", _DEPOT_ADDR, _YELP, SourceType.YELP),
            _c("phone", _DEPOT_PHONE, _YELP, SourceType.YELP),
            _c("rating", "4.3", _YELP, SourceType.YELP),
        ],
    ),
    SourceRecord(
        source_type=SourceType.DIRECTORY, source_url=_YAHOO,
        entity_name=_DEPOT, entity_address=_DEPOT_ADDR, entity_phone=_DEPOT_PHONE,
        claims=[
            _c("address", _DEPOT_ADDR, _YAHOO, SourceType.DIRECTORY),
            _c("phone", _DEPOT_PHONE, _YAHOO, SourceType.DIRECTORY),
        ],
    ),
    SourceRecord(
        source_type=SourceType.EXISTING_SITE, source_url=_SITE,
        entity_name=_DEPOT, entity_address=_DEPOT_ADDR, entity_phone=_DEPOT_PHONE,
        claims=[
            _c("services", "fried catfish, burgers, chicken fried steak", _SITE,
               SourceType.EXISTING_SITE),
            _c("year_opened", "1999", _SITE, SourceType.EXISTING_SITE),
        ],
    ),
]

_JS = "JS Lawn Care Service"
_JS_ADDR = "7934 Milestone Ridge Dr, Frisco, TX 75035"
_JS_DIR = "https://www.chamberofcommerce.com/js-lawn-care-service-frisco"
_JSM = "https://www.yelp.com/biz/j-s-m-lawn-care-frisco"

JS_LAWN_SOURCES = [
    SourceRecord(
        source_type=SourceType.DIRECTORY, source_url=_JS_DIR,
        entity_name=_JS, entity_address=_JS_ADDR,
        claims=[
            _c("address", _JS_ADDR, _JS_DIR, SourceType.DIRECTORY),
            _c("services", "mowing, trimming, edging, tree trimming, flower beds", _JS_DIR,
               SourceType.DIRECTORY),
        ],
    ),
    # Look-alike — a DIFFERENT business. Entity resolution must reject this.
    SourceRecord(
        source_type=SourceType.YELP, source_url=_JSM,
        entity_name="J.S.M. Lawn Care", entity_phone="(469) 555-0148",
        claims=[_c("phone", "(469) 555-0148", _JSM, SourceType.YELP)],
    ),
]


def demo_businesses() -> list[dict]:
    """Business kwargs + sources for the research demo."""
    return [
        {
            "name": _DEPOT, "location": "Frisco, TX", "category": "restaurant",
            "address": _DEPOT_ADDR, "phone": _DEPOT_PHONE, "place_id": "demo-depot",
            "sources": DEPOT_CAFE_SOURCES,
        },
        {
            "name": _JS, "location": "Frisco, TX", "category": "lawn",
            "address": _JS_ADDR, "phone": None, "place_id": "demo-jslawn",
            "sources": JS_LAWN_SOURCES,
        },
    ]


# Known-true facts for the capability-A eval (used to score the dossier).
GOLDEN_TRUTH = {
    "demo-depot": {
        "verified_must_include": {
            "address": "6733 w main st",   # normalized substring
            "phone": "9723770707",         # digits
        },
        "must_not_be_verified": ["owner_name"],  # unknown — must not be fabricated
    },
    "demo-jslawn": {
        "verified_must_include": {},
        "must_not_be_verified": ["phone", "owner_name"],  # thin data / gaps
    },
}
