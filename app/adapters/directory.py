"""Third-party directory lookups — the independent sources that make
corroboration possible.

A fact needs **two independent** sources to become VERIFIED. For a business with
no website, the Google Places record is the only one we start with, so every
fact would stay UNVERIFIED forever. Each directory here is an independent
publisher of the same facts.

Coverage differs sharply by segment, which is why there is more than one:

* **OpenStreetMap** (`osm.py`) — free, no key. Good for storefronts (restaurants,
  shops); **poor for service-area businesses** like lawn care, and rarely carries
  phone numbers.
* **Yelp** (`yelp.py`) — free API key. Strong coverage of exactly the local
  service businesses OSM misses, and reliably carries phone + address.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class DirectoryPlace:
    """One matched directory record. Fields are None when not published."""

    name: str
    address: str | None
    phone: str | None
    website: str | None
    source_url: str
    rating: float | None = None
    review_count: int | None = None
    categories: tuple[str, ...] = ()
    # Opening hours, when the source publishes them. A second source for hours
    # is what turns "ask them their hours" into a fact you already have.
    hours: tuple[str, ...] = ()
    # How many results in the same search carried this business's name. A
    # chain announces itself here long before its website does - and when the
    # site blocks us, this is the only signal left.
    same_name_nearby: int = 1
    # OPERATIONAL | CLOSED_TEMPORARILY | CLOSED_PERMANENTLY. Pitching a closed
    # business wastes a visit, and Google knows before the street does.
    business_status: str | None = None
    summary: str | None = None          # Google's one-line editorial description
    latitude: float | None = None
    longitude: float | None = None
    reviews: tuple[dict, ...] = ()
    photo_refs: tuple[str, ...] = ()
    price_level: str | None = None


class DirectorySource(Protocol):
    """Anything that can look a business up by name + location."""

    name: str

    def lookup(self, name: str, location: str) -> DirectoryPlace | None: ...


class NullDirectorySource:
    """Yields no match — used to keep tests off the network."""

    name = "null"

    def lookup(self, name: str, location: str) -> DirectoryPlace | None:  # noqa: ARG002
        return None
