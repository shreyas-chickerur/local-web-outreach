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

from dataclasses import dataclass, field

from app.adapters.directory import DirectoryPlace, DirectorySource
from app.adapters.site_fetch import HttpSiteFetcher, SiteFetcher
from app.ai.research_runner import RawClaim
from app.core.enums import SourceType
from app.stages.collect import contact_page_urls
from app.stages.entity_resolution import _name_similarity
from app.stages.extract_site import (
    ExtractedSite,
    extract_from_html,
    menu_page_urls,
    merge,
)
from app.stages.research import ResolvedClaim, corroborate
from app.workbench.resolve import (
    ResolvedInput,
    name_from_domain,
    name_from_title,
    resolve_input,
)

# Below this, a directory hit is a different company and must not be merged.
NAME_MATCH_THRESHOLD = 0.6


@dataclass
class Brief:
    name: str
    location: str | None
    website_url: str | None
    notes: str | None
    facts: list[ResolvedClaim] = field(default_factory=list)
    published: ExtractedSite | None = None      # what their own site says
    assumptions: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    site_reachable: bool | None = None
    sources_consulted: list[str] = field(default_factory=list)

    @property
    def confident_facts(self) -> list[ResolvedClaim]:
        return [f for f in self.facts if f.status.value in
                ("verified", "operator_verified")]


def _claims_from_place(place: DirectoryPlace, source_type: SourceType) -> list[RawClaim]:
    claims: list[RawClaim] = []
    if place.address:
        claims.append(RawClaim(field="address", value=place.address,
                               source_url=place.source_url, source_type=source_type))
    if place.phone:
        claims.append(RawClaim(field="phone", value=place.phone,
                               source_url=place.source_url, source_type=source_type))
    if place.rating:
        claims.append(RawClaim(field="rating", value=str(place.rating),
                               source_url=place.source_url, source_type=source_type))
    return claims


def _read_their_site(url: str, fetcher: SiteFetcher) -> tuple[ExtractedSite | None, bool]:
    """Fetch their homepage plus the pages that actually carry content."""
    result = fetcher.fetch(url)
    if not result.ok or not result.html:
        return None, False
    base = result.final_url or url
    extracted = extract_from_html(result.html, base)
    for page in menu_page_urls(result.html, base) + contact_page_urls(result.html, base):
        sub = fetcher.fetch(page)
        if sub.ok and sub.html:
            extracted = merge(extracted, extract_from_html(sub.html, page))
    return extracted, True


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
        published, reachable = _read_their_site(brief.website_url, fetcher)
        brief.site_reachable = reachable
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
    for directory in directories:
        place = directory.lookup(brief.name, brief.location or "")
        if place is None:
            continue
        source_name = getattr(directory, "name", "directory")
        if _name_similarity(brief.name, place.name) < NAME_MATCH_THRESHOLD:
            brief.assumptions.append(
                f"ignored a {source_name} result for {place.name!r} — different business")
            continue
        brief.sources_consulted.append(source_name)
        raw_claims.extend(_claims_from_place(place, SourceType.DIRECTORY))
        if brief.location is None and place.address:
            brief.location = place.address
        if brief.website_url is None and place.website:
            brief.website_url = place.website
            brief.assumptions.append(
                f"website found via {source_name}: {place.website}")

    # A website discovered by a directory still needs reading.
    if brief.website_url and brief.published is None:
        published, reachable = _read_their_site(brief.website_url, fetcher)
        brief.site_reachable = reachable
        brief.published = published
        if reachable:
            brief.sources_consulted.append("their website")

    if brief.website_url is None:
        brief.open_questions.append(
            "No website found — is that right, or do they have one we missed?")

    brief.facts = corroborate(raw_claims)

    known = {f.field for f in brief.confident_facts}
    for wanted, question in (
        ("address", "What is their street address?"),
        ("phone", "What number do customers actually call?"),
        ("hours", "What are their opening hours?"),
    ):
        if wanted not in known and not (
                wanted == "hours" and brief.published and brief.published.hours):
            brief.open_questions.append(question)

    return brief


def format_brief(brief: Brief) -> str:
    """Plain-text brief — the thing you read before walking in."""
    lines: list[str] = []
    lines.append(f"{brief.name}")
    if brief.location:
        lines.append(f"  {brief.location}")
    if brief.website_url:
        state = ("reachable" if brief.site_reachable
                 else "NOT LOADING" if brief.site_reachable is False else "")
        lines.append(f"  {brief.website_url}  {('(' + state + ')') if state else ''}")
    else:
        lines.append("  no website found")
    if brief.notes:
        lines.append(f"  your notes: {brief.notes}")

    lines.append("")
    lines.append("WHAT WE ESTABLISHED")
    if not brief.facts:
        lines.append("  (nothing corroborated — see open questions)")
    for fact in brief.facts:
        pct = f"{fact.confidence * 100:.0f}%"
        if fact.candidates:
            # A conflict is only useful if you can see who said what.
            lines.append(f"  [{fact.status.value:10}] {fact.field:9} {pct:>4}  "
                         f"sources disagree:")
            for cand in fact.candidates:
                who = cand.get("source_url", "")
                label = ("google" if "google" in who else
                         "yelp" if "yelp" in who else
                         "openstreetmap" if "openstreetmap" in who else
                         cand.get("source_type", "source"))
                lines.append(f"{'':16}{label:>14}: {cand.get('value')}")
        else:
            lines.append(f"  [{fact.status.value:10}] {fact.field:9} {pct:>4}  {fact.value}")
            for src in fact.sources:
                lines.append(
                    f"{'':30}<- {src.get('source_type')}: {src.get('source_url', '')[:58]}")

    pub = brief.published
    if pub:
        lines.append("")
        lines.append("WHAT THEIR SITE PUBLISHES")
        if pub.description:
            lines.append(f"  tagline:  {pub.description[:88]}")
        if pub.services:
            lines.append(f"  services: {', '.join(pub.services[:6])}")
        if pub.menu_items:
            lines.append(f"  pricing:  {len(pub.menu_items)} priced items")
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
