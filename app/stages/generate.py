"""Stage 4: GENERATE.

Build a structured, industry-aware **site content model** for a business,
grounded entirely in its VERIFIED research claims. Every fact rendered on the
site carries the ``claim_id`` that backs it; unverified/conflicting fields are
omitted (surfaced as "needs confirmation"), and social-proof sections
(reviews/testimonials) are never fabricated. The result is persisted as a
private DRAFT ``Website`` (tokenized preview, noindex) and the business advances
to SITE_DRAFTED via the spine.

The content model is deterministic and fully grounded, so no LLM call is
required for correctness — a later copy-polish step (Claude) is an optional
enhancement that must preserve every ``claim_id`` and pass the same validator.
"""

from __future__ import annotations

import secrets

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import config
from app.core.approvals import hash_content
from app.core.enums import Actor, BusinessStatus, ClaimStatus, WebsiteState
from app.core.errors import SiteIntegrityError
from app.core.state_machine import advance
from app.models.research_claim import ResearchClaim
from app.models.website import Website
from app.stages.research import REQUIRED_FIELDS

# Sections whose presence would imply fabricated social proof — never generated,
# and rejected by the validator if they somehow appear.
FORBIDDEN_SECTIONS = frozenset({"reviews", "testimonials", "awards"})

# Sections built from the business's own published content. They carry no
# claim_ids (nothing to corroborate — the business said it about itself) and so
# must declare provenance instead.
SELF_ATTESTED_SECTIONS = frozenset({"offerings", "opening_hours", "story", "gallery",
                                    "bill_of_fare"})

# Which verified fields each section renders as facts.
SECTION_FIELDS: dict[str, list[str]] = {
    "menu": ["services"],
    "services": ["services"],
    "hours": ["hours"],
    "location": ["address"],
    "service_area": ["address"],
    "contact": ["address", "phone"],
    "about": ["services"],
    "standing": ["rating"],
}

_HEADINGS = {
    "menu": "What we serve", "services": "What we do", "hours": "Hours",
    "location": "Find us", "service_area": "Areas we serve", "contact": "Contact",
    "about": "About us", "standing": "Rated by customers",
}


def industry_template(category: str | None) -> tuple[str, list[str]]:
    """Pick an industry template + ordered section list for a category."""
    c = (category or "").lower()
    if c in {"restaurant", "cafe", "diner", "bakery", "bar", "food"}:
        return "restaurant", ["hero", "menu", "standing", "hours", "location", "contact", "cta"]
    if c in {"lawn", "landscaping", "handyman", "plumbing", "cleaning", "pool", "hvac",
             "roofing", "electrician", "service"}:
        return "service", ["hero", "services", "standing", "service_area", "contact", "cta"]
    return "generic", ["hero", "about", "standing", "contact", "cta"]


def _self_attested_sections(extracted) -> list[dict]:  # noqa: ANN001
    """Sections built from the business's OWN site.

    This is their published content, carried across — not fabricated, and not a
    third-party claim needing corroboration. Every entry is marked
    ``provenance: self_attested`` so the operator can tell it apart from a
    corroborated fact at a glance.
    """
    if extracted is None:
        return []
    out: list[dict] = []
    if extracted.menu_items or extracted.menu_media:
        out.append({"type": "bill_of_fare", "heading": "Menu",
                    "provenance": "self_attested",
                    "items": list(extracted.menu_items),
                    "media": list(extracted.menu_media)})
    if extracted.services:
        out.append({"type": "offerings", "heading": "What we offer",
                    "provenance": "self_attested",
                    "items": list(extracted.services)})
    if extracted.hours:
        out.append({"type": "opening_hours", "heading": "Hours",
                    "provenance": "self_attested",
                    "items": list(extracted.hours)})
    if extracted.about:
        out.append({"type": "story", "heading": "About us",
                    "provenance": "self_attested", "body": extracted.about})
    if extracted.images:
        out.append({"type": "gallery", "heading": "Gallery",
                    "provenance": "self_attested",
                    "images": list(extracted.images[:6])})
    return out


def _internalised_actions(extracted) -> list[dict]:  # noqa: ANN001
    """Rewrite actions so the proposal never sends a visitor back to the old site.

    A "Menu" button pointing at their current website makes the new page a
    brochure for the old one. Where we carry the content ourselves the action
    becomes an in-page anchor; a link back to their own host is dropped
    entirely. Only genuine third-party flows (OpenTable, DoorDash) and
    tel:/mailto: survive as outbound links, because those ARE the real booking
    path and no new site replaces them.
    """
    if extracted is None:
        return []
    carries_menu = bool(extracted.menu_items or extracted.menu_media)
    host = (extracted.site_host or "").lower()
    out: list[dict] = []
    for action in extracted.actions:
        url = str(action.get("url", ""))
        kind = str(action.get("kind", ""))
        if kind == "Menu":
            if carries_menu:
                out.append({**action, "url": "#menu", "label": "See the menu"})
            continue                       # no menu content -> no dead button
        if url.startswith(("tel:", "mailto:")):
            out.append(action)
            continue
        if host and host in url:           # their old site — not a destination
            continue
        out.append(action)
    return out


def generate_content(business, verified: dict[str, ResearchClaim], extracted=None) -> dict:  # noqa: ANN001
    """Build the grounded content model from a business's verified claims, plus
    their own site's self-attested content."""
    template_name, section_types = industry_template(business.category)
    sections: list[dict] = []
    rendered_fields: set[str] = set()

    for stype in section_types:
        if stype == "hero":
            # Lead with what they actually are ("South Indian Restaurant"), not
            # just the city — but only when a VERIFIED claim says so.
            services = verified.get("services")
            subheading = (f"{services.value} in {business.location}"
                          if services is not None else business.location)
            sections.append(
                {"type": "hero", "heading": business.name, "subheading": subheading}
            )
        elif stype == "cta":
            sections.append(
                {"type": "cta", "heading": "Get in touch",
                 "body": f"Reach out to {business.name}."}
            )
        else:
            facts = []
            for field in SECTION_FIELDS.get(stype, []):
                claim = verified.get(field)
                # A field belongs to whichever section renders it first; showing
                # the address under both "Find us" and "Contact" is just noise.
                if claim is not None and field not in rendered_fields:
                    rendered_fields.add(field)
                    facts.append({
                        "label": field.replace("_", " ").title(),
                        "field": field,
                        "value": claim.value,
                        "claim_id": str(claim.id),
                    })
            if facts:  # omit sections with no verified facts — never fabricate
                sections.append({"type": stype, "heading": _HEADINGS[stype], "facts": facts})

    # Their own content goes after the hero, before the contact/CTA blocks.
    self_attested = _self_attested_sections(extracted)
    if self_attested:
        tail = [s for s in sections if s.get("type") in {"cta"}]
        head = [s for s in sections if s.get("type") not in {"cta"}]
        sections = head[:1] + self_attested + head[1:] + tail

    needs_confirmation = [f for f in REQUIRED_FIELDS if f not in verified]
    hero_image = (extracted.images[0] if extracted and extracted.images else None)
    return {
        "business_name": business.name,
        "industry": template_name,
        "noindex": True,  # private proposal until purchased
        "sections": sections,
        "needs_confirmation": needs_confirmation,
        "hero_image": hero_image,
        # The actions their customers came to perform. Dropping these would make
        # the new site a downgrade however good it looks.
        "actions": _internalised_actions(extracted),
        "socials": list(extracted.socials) if extracted else [],
        "tagline": (extracted.description if extracted else None),
    }


def validate_site_content(content: dict, verified_claim_ids: set[str]) -> dict:
    """Hard guard: every rendered fact traces to a VERIFIED claim; no fabricated
    social proof. Enforces invariant #1 on the site itself."""
    for section in content.get("sections", []):
        if section.get("type") in FORBIDDEN_SECTIONS:
            raise SiteIntegrityError(
                f"forbidden section '{section['type']}' — no fabricated social proof"
            )
        # Content carried from their own site must declare where it came from,
        # so it can never be mistaken for a corroborated third-party fact.
        if section.get("type") in SELF_ATTESTED_SECTIONS and \
                section.get("provenance") != "self_attested":
            raise SiteIntegrityError(
                f"section '{section.get('type')}' carries content with no provenance"
            )
        for fact in section.get("facts", []):
            cid = fact.get("claim_id")
            if not cid or cid not in verified_claim_ids:
                raise SiteIntegrityError(
                    f"fact '{fact.get('field')}' is not backed by a VERIFIED claim"
                )
    return content


def generate_website(session: Session, business, *, model_version: str | None = None,
                     extracted=None) -> Website:  # noqa: ANN001
    """Generate + persist a private DRAFT website; advance RESEARCHED -> SITE_DRAFTED."""
    claims = session.execute(
        select(ResearchClaim).where(
            ResearchClaim.business_id == business.id,
            ResearchClaim.status == ClaimStatus.VERIFIED,
        )
    ).scalars().all()

    # Highest-confidence verified claim per field.
    verified: dict[str, ResearchClaim] = {}
    for claim in claims:
        if claim.field not in verified or claim.confidence > verified[claim.field].confidence:
            verified[claim.field] = claim

    content = generate_content(business, verified, extracted)
    validate_site_content(content, {str(c.id) for c in claims})

    token = secrets.token_urlsafe(16)
    next_version = session.execute(
        select(func.count()).select_from(Website).where(Website.business_id == business.id)
    ).scalar_one() + 1

    site = Website(
        business_id=business.id,
        version=next_version,
        content_json=content,
        preview_token=token,
        preview_url=f"{config.preview_base_url()}/preview/{token}",
        state=WebsiteState.DRAFT,
        content_hash=hash_content(content),
    )
    session.add(site)
    session.flush()

    fact_count = sum(len(s.get("facts", [])) for s in content["sections"])
    advance(
        session, business, BusinessStatus.SITE_DRAFTED,
        actor=Actor.SYSTEM.value,
        reason=f"site draft v{next_version}: {len(content['sections'])} sections, "
               f"{fact_count} verified facts, {len(content['needs_confirmation'])} to confirm",
    )
    return site
