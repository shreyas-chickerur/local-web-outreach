"""Slice 1: turn a company name or URL into a brief you can walk in with.

A brief is everything we could establish about a business, each item carrying
how confident we are and where it came from. It is not a report the machine
believes — it is evidence the reader judges, which is why confidence and sources
are on every line rather than in a footnote.

Two paths in:

* **A URL was given.** That IS the business. We read their site directly and use
  directories only to corroborate what it says. No search happens, because a
  search can only introduce the chance of matching the wrong company.
* **A name was given.** We look the name up, and the match becomes an assumption
  the brief states out loud rather than hides.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace

from app.adapters.directory import DirectoryPlace, DirectorySource
from app.adapters.site_fetch import HttpSiteFetcher, SiteFetcher
from app.workbench.corroborate import Fact, corroborate
from app.workbench.extract import (
    ExtractedSite,
    contact_page_urls,
    extract_from_html,
    menu_page_urls,
    merge,
)
from app.workbench.hours import canonical as canonical_hours
from app.workbench.hours import describe as describe_hours
from app.workbench.hours import from_canonical as hours_from_canonical
from app.workbench.match import same_business
from app.workbench.resolve import (
    ResolvedInput,
    name_from_domain,
    name_from_title,
    resolve_input,
    town_of,
)
from app.workbench.types import Confidence, RawClaim, SourceType
from app.workbench.weburl import UrlCheck, validate


@dataclass
class Brief:
    name: str
    location: str | None
    website_url: str | None
    notes: str | None
    facts: list[Fact] = field(default_factory=list)
    published: ExtractedSite | None = None      # what their own site says
    assumptions: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    site_reachable: bool | None = None
    # Being refused is not being broken. Home Depot answers our request with a
    # 403 from its bot protection while the page loads perfectly in a browser;
    # reporting that as "not loading" tells the reader something false about
    # the business.
    site_status: str | None = None      # ok | blocked | error | unreachable
    # What the published address actually does, and what to use instead.
    url_check: UrlCheck | None = None
    sources_consulted: list[str] = field(default_factory=list)
    # Why we think this is a multi-location brand. Empty for a single business.
    chain_signals: list[str] = field(default_factory=list)
    # One rating per platform. These are not competing claims about a single
    # number - Google's 4.8 and Yelp's 2.4 measure different review
    # populations, so both are true and corroborating them is meaningless.
    ratings: list[dict] = field(default_factory=list)
    # Customer reviews and Google's own photography. Not facts to corroborate —
    # material for the site we build them, which is short of good imagery and
    # short of anything credible that the business did not write itself.
    testimonials: list[dict] = field(default_factory=list)
    place_photos: list[str] = field(default_factory=list)
    trade: str | None = None            # "Restaurant", as the directory files it
    latitude: float | None = None
    longitude: float | None = None

    @property
    def looks_like_a_chain(self) -> bool:
        return bool(self.chain_signals)

    @property
    def confident_facts(self) -> list[Fact]:
        return [f for f in self.facts if f.is_fact]


def _same_town(location: str, address: str) -> bool:
    town = town_of(location)
    return not town or town in (address or "").lower()


_HOUSE_NUMBER_RE = re.compile(r"^\s*(\d+)\b")
_LOCATOR_HINTS = ("store-locator", "storelocator", "/locations", "/stores",
                  "/find-a", "/our-locations")


def chain_signals(facts: list[Fact], website_url: str | None,
                  published: ExtractedSite | None,
                  nearby: dict[str, int] | None = None) -> list[str]:
    """Evidence that this brand has several branches.

    Worth knowing before you walk in, in both directions: a national franchise
    cannot buy a website from you, while a three-location local group often has
    more budget than a single site. Either way the brief was reporting it as a
    three-way address disagreement, which reads like a data problem rather than
    what it is — the sources are not disagreeing about ONE address, they each
    picked a DIFFERENT branch.
    """
    signals: list[str] = []

    address = next((f for f in facts if f.field == "address"), None)
    if address is not None and address.candidates:
        numbers = set()
        for candidate in address.candidates:
            match = _HOUSE_NUMBER_RE.match(str(candidate.get("value", "")))
            if match:
                numbers.add(match.group(1))
        if len(numbers) > 1:
            signals.append(
                f"sources point at {len(numbers)} different street addresses — "
                f"each likely a separate branch")

    if website_url and any(h in website_url.lower() for h in _LOCATOR_HINTS):
        signals.append(f"the website is a store locator, not one location: {website_url}")

    if published is not None and published.has_locations_page:
        signals.append("their own site has a locations page")

    # The directories know how many branches exist whether or not the site lets
    # us read it. When a chain's bot protection refuses us — Home Depot answers
    # our reader with a 403 — this is the only signal left.
    for source, count in sorted((nearby or {}).items()):
        if count >= 3:
            signals.append(f"{source} returns {count} locations under this name "
                           f"in one search")

    return signals


def source_type_for(directory_name: str) -> SourceType:
    """Name a source precisely. 'directory' told the reader nothing; 'google'
    and 'yelp' let them judge which one to believe when the two disagree."""
    try:
        return SourceType(directory_name)
    except ValueError:
        return SourceType.OTHER


def _claims_from_place(place: DirectoryPlace, source_type: SourceType) -> list[RawClaim]:
    claims: list[RawClaim] = []
    if place.address:
        claims.append(RawClaim(field="address", value=place.address,
                               source_url=place.source_url, source_type=source_type))
    if place.phone:
        claims.append(RawClaim(field="phone", value=place.phone,
                               source_url=place.source_url, source_type=source_type))
    schedule = canonical_hours(list(place.hours))
    if schedule:
        claims.append(RawClaim(field="hours", value=schedule,
                               source_url=place.source_url, source_type=source_type))
    return claims


def site_state(status: int | None, ok: bool) -> str:
    """How to describe a fetch that did not work."""
    if ok:
        return "ok"
    if status in (401, 403, 405, 406, 429):
        return "blocked"        # refused us, not down
    if status is None:
        return "unreachable"    # nothing answered
    return "error"


def _read_their_site(url: str, fetcher: SiteFetcher
                     ) -> tuple[ExtractedSite | None, bool, str, UrlCheck]:
    """Fetch their homepage plus the pages that actually carry content."""
    check = validate(url, fetcher)
    result = check.result
    if result is None or not result.html:
        state = ("blocked" if check.blocked
                 else "insecure" if check.fault == "certificate" else "unreachable")
        return None, False, state, check
    url = check.working or url
    state = site_state(result.status, bool(result.ok and result.html))
    if check.fault == "certificate":
        state = "insecure"
    base = result.final_url or url
    extracted = extract_from_html(result.html, base)
    for page in menu_page_urls(result.html, base) + contact_page_urls(result.html, base):
        sub = fetcher.fetch(page)
        if sub.ok and sub.html:
            extracted = merge(extracted, extract_from_html(sub.html, page))
    return extracted, True, ("insecure" if check.fault == "certificate" else "ok"), check


def build_brief(
    raw: str,
    *,
    location: str | None = None,
    notes: str | None = None,
    directories: list[DirectorySource] | None = None,
    fetcher: SiteFetcher | None = None,
) -> Brief:
    """Research one company and return everything we could establish."""
    resolved: ResolvedInput = resolve_input(raw, location=location, notes=notes)
    fetcher = fetcher or HttpSiteFetcher()
    directories = directories or []

    brief = Brief(name=resolved.name or raw.strip(), location=resolved.location,
                  website_url=resolved.website_url, notes=notes,
                  assumptions=list(resolved.assumptions))

    raw_claims: list[RawClaim] = []

    # --- their own site first ------------------------------------------------
    # Reading the site before searching matters: a directory lookup keyed on a
    # name guessed from a domain ("Theheritagetable") matches nothing, while the
    # real name from their page title matches immediately.
    if brief.website_url:
        published, reachable, state, check = _read_their_site(brief.website_url, fetcher)
        brief.url_check = check
        brief.site_reachable = reachable
        brief.site_status = state
        brief.published = published
        if reachable and published:
            brief.sources_consulted.append("their website")
            if published.title and resolved.input_was_url:
                better = name_from_title(
                    published.title, domain_hint=name_from_domain(brief.website_url))
                if better and better.lower() != brief.name.lower():
                    brief.assumptions = [
                        a for a in brief.assumptions if "guessed from the domain" not in a]
                    brief.assumptions.append(
                        f"name read from their page title: {better!r}")
                    brief.name = better
            if published.menu_items:
                raw_claims.append(RawClaim(
                    field="services",
                    value=", ".join(i["name"] for i in published.menu_items[:4]),
                    source_url=brief.website_url,
                    source_type=SourceType.EXISTING_SITE))
    else:
        brief.site_reachable = None

    # --- directories, now that we know what the business is called ------------
    nearby: dict[str, int] = {}
    for directory in directories:
        place = directory.lookup(brief.name, brief.location or "")
        if place is None:
            continue
        source_name = getattr(directory, "name", "directory")
        if not same_business(brief.name, place.name):
            brief.assumptions.append(
                f"ignored a {source_name} result for {place.name!r} — different business")
            continue
        # Matching on name alone can pick up the same-named business one town
        # over. That may still be the right company — a lawn service in Plano
        # covers Frisco — but the reader has to be told, not left to notice.
        if brief.location and place.address and not _same_town(brief.location, place.address):
            brief.assumptions.append(
                f"{source_name} matched a listing in a different town: {place.address}")
        brief.sources_consulted.append(source_name)
        raw_claims.extend(_claims_from_place(place, source_type_for(source_name)))
        if place.same_name_nearby > 1:
            nearby[source_name] = place.same_name_nearby
        if place.reviews and not brief.testimonials:
            brief.testimonials = [dict(r) for r in place.reviews[:5]]
        if place.categories and brief.trade is None:
            brief.trade = place.categories[0] or None
        if place.photo_refs and not brief.place_photos:
            brief.place_photos = list(place.photo_refs)
        if brief.latitude is None and place.latitude is not None:
            brief.latitude, brief.longitude = place.latitude, place.longitude
        if place.rating is not None:
            brief.ratings.append({"source": source_name, "value": place.rating,
                                  "reviews": place.review_count,
                                  "source_url": place.source_url})
        if brief.location is None and place.address:
            brief.location = place.address
        if brief.website_url is None and place.website:
            brief.website_url = place.website
            brief.assumptions.append(
                f"website found via {source_name}: {place.website}")

    # What a business publishes about itself is an independent source. Without
    # this, a single directory listing could never reach two-source
    # confirmation, and everything stayed UNVERIFIED no matter how plainly the
    # number was printed on their own homepage.
    def _claims_from_site(site: ExtractedSite, url: str) -> list[RawClaim]:
        out: list[RawClaim] = []
        for name, value in (("phone", site.phone), ("address", site.address)):
            if value:
                out.append(RawClaim(field=name, value=value, source_url=url,
                                    source_type=SourceType.EXISTING_SITE))
        schedule = canonical_hours(site.hours)
        if schedule:
            out.append(RawClaim(field="hours", value=schedule, source_url=url,
                                source_type=SourceType.EXISTING_SITE))
        return out

    # A website discovered by a directory still needs reading.
    if brief.website_url and brief.published is None:
        published, reachable, state, check = _read_their_site(brief.website_url, fetcher)
        brief.url_check = check
        brief.site_reachable = reachable
        brief.site_status = state
        brief.published = published
        if reachable:
            brief.sources_consulted.append("their website")
    if brief.published is not None and brief.website_url:
        raw_claims.extend(_claims_from_site(brief.published, brief.website_url))

    if brief.website_url is None:
        brief.open_questions.append(
            "No website found — is that right, or do they have one we missed?")

    # A source that only knows the town ("Frisco, TX 75035") is not disagreeing
    # with one that has the street ("2770 Main St, Frisco, TX 75033") — it is
    # simply less specific. Scoring that as a conflict buried a good address and
    # then asked for the address we already had.
    street = [c for c in raw_claims
              if c.field == "address" and _HOUSE_NUMBER_RE.match(c.value.strip())]
    if street:
        vague = [c for c in raw_claims
                 if c.field == "address" and c not in street]
        for claim in vague:
            brief.assumptions.append(
                f"{claim.source_type.value} had only a town for this business, "
                f"so it neither confirms nor contradicts the street address: "
                f"{claim.value}")
        raw_claims = [c for c in raw_claims if c not in vague]

    brief.facts = corroborate(raw_claims)
    # "mon:0800-1700 tue:..." exists so two sources can be compared. Nobody
    # should have to read it, so put the human phrasing back afterwards.
    brief.facts = [
        replace(f, value=describe_hours(hours_from_canonical(f.value)))
        if f.field == "hours" and f.value else f
        for f in brief.facts]
    brief.chain_signals = chain_signals(brief.facts, brief.website_url,
                                        brief.published, nearby)

    # A town name is not a service. Only the brief knows which towns are in play.
    if brief.published is not None:
        towns = {town_of(brief.location or "")}
        towns |= {town_of(str(c.get("value", "")))
                  for f in brief.facts if f.field == "address"
                  for c in (f.candidates or [{"value": f.value}])}
        towns.discard("")
        services = [s for s in brief.published.services if s.strip().lower() not in towns]
        # On a site with a locations menu, a bare one-word entry is a branch
        # name, not an offering — "Plano" and "Southlake" are not services.
        if brief.published.has_locations_page:
            services = [s for s in services if " " in s.strip()]
        brief.published.services = services
        brief.published.products = [
            p for p in brief.published.products if p.strip().lower() not in towns]

    known = {f.field for f in brief.confident_facts}
    _NOUN = {"address": "their street address", "phone": "their phone number",
             "hours": "their opening hours"}
    for wanted, question in (
        ("address", "What is their street address?"),
        ("phone", "What number do customers actually call?"),
        ("hours", "What are their opening hours?"),
    ):
        if wanted in known or (
                wanted == "hours" and brief.published and brief.published.hours):
            continue
        # If exactly one source gave us a value, asking as though we have
        # nothing wastes the walk-in. Ask them to confirm what we found.
        single = next((f for f in brief.facts if f.field == wanted
                       and f.confidence is Confidence.UNVERIFIED), None)
        if single is not None:
            brief.open_questions.append(
                f"{_NOUN[wanted].capitalize()}: only "
                f"{single.sources[0]['source_type']} lists it — confirm "
                f"{single.value}?")
        else:
            brief.open_questions.append(question)

    return brief


def format_brief(brief: Brief) -> str:
    """Plain-text brief — the thing you read before walking in."""
    lines: list[str] = []
    lines.append(f"{brief.name}")
    # Prefer the address we established over the town the operator typed: the
    # same business looked up by name and by URL should print the same header.
    best_address = next(
        (f.value for f in brief.facts
         if f.field == "address" and f.confidence is not Confidence.CONFLICT), None)
    if best_address or brief.location:
        lines.append(f"  {best_address or brief.location}")
    if brief.website_url:
        state = {"ok": "reachable",
                 "insecure": "CERTIFICATE ERROR — visitors get a browser "
                             "security warning at this address",
                 "blocked": "BLOCKED OUR READER — the site itself is probably fine",
                 "error": "returning an error",
                 "unreachable": "NOT LOADING"}.get(brief.site_status or "", "")
        lines.append(f"  {brief.website_url}  {('(' + state + ')') if state else ''}")
    else:
        lines.append("  no website found")
    if brief.notes:
        lines.append(f"  your notes: {brief.notes}")

    if brief.looks_like_a_chain:
        lines.append("")
        lines.append("!! MULTIPLE LOCATIONS — a franchise is not a lead, but a "
                     "local group may be a better one")
        for signal in brief.chain_signals:
            lines.append(f"   {signal}")

    lines.append("")
    lines.append("WHAT WE ESTABLISHED")
    if not brief.facts:
        lines.append("  (nothing corroborated — see open questions)")
    for fact in brief.facts:
        pct = f"{fact.score * 100:.0f}%"
        if fact.candidates:
            # A conflict is only useful if you can see who said what.
            lines.append(f"  [{fact.confidence.value:10}] {fact.field:9} {pct:>4}  "
                         f"sources disagree:")
            for cand in fact.candidates:
                who = cand.get("source_url", "")
                label = ("google" if "google" in who else
                         "yelp" if "yelp" in who else
                         "openstreetmap" if "openstreetmap" in who else
                         cand.get("source_type", "source"))
                lines.append(f"{'':16}{label:>14}: {cand.get('value')}")
        else:
            lines.append(f"  [{fact.confidence.value:10}] {fact.field:9} {pct:>4}  {fact.value}")
            for src in fact.sources:
                lines.append(
                    f"{'':30}<- {src.get('source_type')}: {src.get('source_url', '')[:58]}")
            for other in fact.dissent:
                lines.append(
                    f"{'':30}!! {other.get('source_type')} disagrees: "
                    f"{other.get('value')}")

    check = brief.url_check
    if check is not None and (check.fault or check.blocked):
        lines.append("")
        lines.append("THE LINK ON THEIR LISTING")
        lines.append(f"  published: {check.published}")
        if check.working and check.working != check.published:
            lines.append(f"  works:     {check.working}")
        lines.append(f"  {check.note}")

    if brief.ratings:
        lines.append("")
        lines.append("RATINGS (per platform — these measure different crowds)")
        for entry in brief.ratings:
            count = entry.get("reviews")
            tail = f"  ({count} reviews)" if count else ""
            lines.append(f"  {entry['source']:<15}{entry['value']}{tail}")

    pub = brief.published
    has_published = pub is not None and any(
        (pub.description, pub.services, pub.products, pub.menu_items, pub.menu_media,
         pub.hours, pub.images, pub.socials))
    if pub and has_published:
        lines.append("")
        lines.append("WHAT THEIR SITE PUBLISHES")
        if pub.description:
            lines.append(f"  tagline:  {pub.description[:88]}")
        if pub.services:
            lines.append(f"  services: {', '.join(pub.services[:6])}")
        if pub.products:
            lines.append(f"  sells:    {', '.join(pub.products[:6])}")
        if pub.menu_items:
            n = len(pub.menu_items)
            lines.append(f"  pricing:  {n} priced item{'s' if n != 1 else ''}")
        if pub.menu_media:
            kinds = ", ".join(sorted({m["kind"] for m in pub.menu_media}))
            lines.append(f"  menu/price doc: {len(pub.menu_media)} ({kinds})")
        if pub.hours:
            lines.append(f"  hours:    {' | '.join(pub.hours[:3])}")
        if pub.images:
            lines.append(f"  photos:   {len(pub.images)}")
        if pub.socials:
            lines.append(f"  social:   {', '.join(s['name'] for s in pub.socials)}")

    if brief.assumptions:
        lines.append("")
        lines.append("ASSUMPTIONS (correct these if wrong)")
        for a in brief.assumptions:
            lines.append(f"  · {a}")

    if brief.open_questions:
        lines.append("")
        lines.append("ASK THEM")
        for q in brief.open_questions:
            lines.append(f"  ? {q}")

    if brief.sources_consulted:
        lines.append("")
        lines.append(f"sources consulted: {', '.join(dict.fromkeys(brief.sources_consulted))}")
    return "\n".join(lines)
