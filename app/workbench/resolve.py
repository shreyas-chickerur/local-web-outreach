"""Turn whatever the user typed into a company we can research.

The input is deliberately loose — a URL, a company name, a name with a city, or
a name plus free-text notes. Everything downstream needs the same three things:
a name, a location if we can get one, and a website URL if one exists.

Resolution order matters. If a URL was given, that IS the business and no
directory lookup can contradict it; searching by name would only introduce the
chance of matching the wrong company. Only when there is no URL do we search.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urlparse

_URL_RE = re.compile(r"^(https?://|www\.)", re.IGNORECASE)
_DOMAINISH_RE = re.compile(r"^[a-z0-9-]+(\.[a-z0-9-]+)+(/.*)?$", re.IGNORECASE)

# A dot between two words is not enough to make something a web address.
# "S.Handyman" was read as https://S.Handyman, the name became "S", and the
# generated page was a single letter on an empty ground.
#
# The asymmetry decides the default: read a URL as a name and the directory
# lookup finds the website anyway, so nothing is lost. Read a name as a URL and
# the name is gone, and everything downstream is built for a business called
# "S". So anything ambiguous is a name.
_REAL_TLDS = frozenset("""
com net org edu gov mil int co io us uk ca au de fr es it nl se no fi dk pl
br mx jp cn in ru za nz ie ch at be pt gr cz ro hu biz info name pro mobi
xyz online site website store shop app dev tech digital media agency studio
design works group team company solutions services expert
live life today world tv me cc ly sh gg
example test invalid localhost local
""".split())
# The last row is RFC 2606's reserved names plus the ones used on internal
# networks: real top-level domains that never resolve publicly.
#
# Deliberately absent: .roofing, .plumbing, .law, .legal, .dental, .salon,
# .spa, .restaurant, .kitchen, .cafe, .pizza, .menu, .contractors,
# .construction, .fitness, .realty, .homes, .house, .estate, .bar. They all
# exist, and including them broke the asymmetry precisely along the businesses
# this tool sells to: "Smith.Roofing" became https://smith.roofing and the name
# was gone. A local contractor writes their address as smithroofing.com, not
# smith.roofing. Anyone who really does own one can type the scheme or the
# www., which still settles it.
# "Craftway Kitchen, Frisco, TX" and "Craftway Kitchen in Frisco, TX".
# The separator must be explicit — a bare space cannot introduce the city, or
# "Ryno Lawn Care in Frisco, TX" loses "Lawn Care" to the city group. A city is
# at most three words, which is what keeps the match tight.
_CITY = r"[A-Za-z.'-]+(?:\s+[A-Za-z.'-]+){0,2}"
_LOCATION_TAIL_RES = (
    re.compile(rf"\s+in\s+({_CITY},\s*[A-Z]{{2}})\s*$"),
    re.compile(rf",\s*({_CITY},\s*[A-Z]{{2}})\s*$"),
)


@dataclass
class ResolvedInput:
    """What the user meant, normalized."""

    name: str | None = None
    location: str | None = None
    website_url: str | None = None
    notes: str | None = None
    # True when the user typed a URL. The name is then a guess from the domain
    # and should be replaced by anything better we find.
    input_was_url: bool = False
    # Set when we had to guess; the brief shows this so the user can correct it.
    assumptions: list[str] = field(default_factory=list)


def looks_like_url(text: str) -> bool:
    """Is this a web address, or a company name with a full stop in it?

    An explicit scheme or a `www.` settles it. Otherwise the last label has to
    be a real top-level domain — see `_REAL_TLDS` for why the doubtful cases
    resolve to "name".
    """
    candidate = (text or "").strip()
    if not candidate or " " in candidate:
        return False
    if _URL_RE.match(candidate):
        return True
    if candidate.lower().startswith("www."):
        return True
    if not _DOMAINISH_RE.match(candidate):
        return False
    host = candidate.split("/", 1)[0]
    return host.rsplit(".", 1)[-1].lower() in _REAL_TLDS


def normalize_url(text: str) -> str:
    candidate = (text or "").strip()
    if not candidate.lower().startswith(("http://", "https://")):
        candidate = "https://" + candidate.lstrip("/")
    return candidate


def name_from_domain(url: str) -> str:
    """A readable company name guessed from a domain, as a starting point."""
    host = (urlparse(url).netloc or "").lower()
    host = host.removeprefix("www.")
    stem = host.split(".")[0] if host else ""
    # craftwaykitchen -> "Craftwaykitchen"; craftway-kitchen -> "Craftway Kitchen"
    words = [w for w in re.split(r"[-_]+", stem) if w]
    return " ".join(w.capitalize() for w in words) if words else stem


def split_location(text: str) -> tuple[str, str | None]:
    """Pull a trailing 'City, ST' off a company name if one is there."""
    for pattern in _LOCATION_TAIL_RES:
        match = pattern.search(text or "")
        if match:
            return text[: match.start()].strip(" ,"), match.group(1).strip()
    return (text or "").strip(), None


def resolve_input(raw: str, *, location: str | None = None,
                  notes: str | None = None) -> ResolvedInput:
    """Normalize a free-form lead input into name / location / website."""
    text = (raw or "").strip()
    if not text:
        raise ValueError("give a company name or a website URL")

    if looks_like_url(text):
        url = normalize_url(text)
        guessed = name_from_domain(url)
        resolved = ResolvedInput(name=None, location=location, website_url=url,
                                 notes=notes, input_was_url=True)
        if guessed:
            resolved.name = guessed
            resolved.assumptions.append(
                f"name guessed from the domain as {guessed!r} — correct it if wrong")
        return resolved

    name, tail_location = split_location(text)
    return ResolvedInput(name=name, location=location or tail_location,
                         website_url=None, notes=notes)


# Page titles are written for search engines, not for us: "Home | The Heritage
# Table | Downtown Frisco Restaurants". The business name is rarely the first
# segment and never the boilerplate one.
_GENERIC_TITLE_PARTS = {
    "home", "welcome", "index", "menu", "about", "about us", "contact",
    "contact us", "official site", "official website", "homepage", "main",
}


def name_from_title(title: str, *, domain_hint: str = "") -> str | None:
    """The business name inside a page title, or None if it isn't in there."""
    parts = [p.strip() for p in re.split(r"[|\u2013\u2014\u00b7>]+", title or "")]
    candidates = [
        p for p in parts
        if p and p.lower() not in _GENERIC_TITLE_PARTS and 2 < len(p) <= 60
    ]
    if not candidates:
        return None
    if domain_hint:
        # The segment whose letters best match the domain is almost always the name.
        squashed = re.sub(r"[^a-z]", "", domain_hint.lower())

        def overlap(part: str) -> int:
            letters = re.sub(r"[^a-z]", "", part.lower())
            return len(letters) if letters and letters in squashed else 0

        best = max(candidates, key=overlap)
        if overlap(best):
            return best
    # Otherwise prefer the shortest plausible segment: taglines are long.
    return min(candidates, key=len)


def town_of(text: str) -> str:
    """The city out of 'Frisco, TX' or '2770 Main St, Frisco, TX 75033'."""
    parts = [p.strip().lower() for p in (text or "").split(",") if p.strip()]
    # The city is the part before the state; with no state, the first part.
    for i, part in enumerate(parts):
        if re.fullmatch(r"[a-z]{2}(\s+\d{5}(-\d{4})?)?", part) and i:
            return parts[i - 1]
    return parts[0] if parts else ""
