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


def generate_content(business, verified: dict[str, ResearchClaim]) -> dict:  # noqa: ANN001
    """Build the grounded content model from a business's verified claims."""
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

    needs_confirmation = [f for f in REQUIRED_FIELDS if f not in verified]
    return {
        "business_name": business.name,
        "industry": template_name,
        "noindex": True,  # private proposal until purchased
        "sections": sections,
        "needs_confirmation": needs_confirmation,
    }


def validate_site_content(content: dict, verified_claim_ids: set[str]) -> dict:
    """Hard guard: every rendered fact traces to a VERIFIED claim; no fabricated
    social proof. Enforces invariant #1 on the site itself."""
    for section in content.get("sections", []):
        if section.get("type") in FORBIDDEN_SECTIONS:
            raise SiteIntegrityError(
                f"forbidden section '{section['type']}' — no fabricated social proof"
            )
        for fact in section.get("facts", []):
            cid = fact.get("claim_id")
            if not cid or cid not in verified_claim_ids:
                raise SiteIntegrityError(
                    f"fact '{fact.get('field')}' is not backed by a VERIFIED claim"
                )
    return content


def generate_website(session: Session, business, *, model_version: str | None = None) -> Website:  # noqa: ANN001
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

    content = generate_content(business, verified)
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
        preview_url=f"https://preview-{token}.lwo.example/",
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
