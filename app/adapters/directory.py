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


class DirectorySource(Protocol):
    """Anything that can look a business up by name + location."""

    name: str

    def lookup(self, name: str, location: str) -> DirectoryPlace | None: ...


class NullDirectorySource:
    """Yields no match — used to keep tests off the network."""

    name = "null"

    def lookup(self, name: str, location: str) -> DirectoryPlace | None:  # noqa: ARG002
        return None
