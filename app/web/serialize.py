"""Turn a Brief into JSON for the browser.

The UI renders exactly what the printed brief shows and nothing more: if a
value did not survive corroboration, it must not reach the screen looking like
a fact. Keeping this conversion in one place is what makes that checkable.
"""

from __future__ import annotations

from app.workbench.brief import Brief
from app.workbench.corroborate import Fact
from app.workbench.extract import ExtractedSite

_LABELS = {
    "address": "Address",
    "phone": "Phone",
    "services": "Services",
}


def fact_to_dict(fact: Fact) -> dict:
    return {
        "field": fact.field,
        "label": _LABELS.get(fact.field, fact.field.replace("_", " ").title()),
        "value": fact.value,
        "confidence": fact.confidence.value,
        "score": round(fact.score * 100),
        "corroborations": fact.corroborations,
        "sources": fact.sources,
        "candidates": fact.candidates,
        "dissent": fact.dissent,
    }


def published_to_dict(site: ExtractedSite) -> dict:
    return {
        "tagline": site.description,
        "about": site.about,
        "services": site.services[:8],
        "products": site.products[:8],
        "hours": site.hours[:7],
        "menu_items": site.menu_items[:12],
        "menu_media": site.menu_media[:4],
        "photos": site.images[:8],
        "socials": site.socials,
        "emails": site.emails,
        "has_locations_page": site.has_locations_page,
    }


def brief_to_dict(brief: Brief) -> dict:
    published = brief.published
    # An extraction with nothing in it is not worth a panel on the page.
    show_published = published is not None and not published.is_empty()
    return {
        "name": brief.name,
        # Mirrors the printed header: the address we established beats the town
        # that was typed in, so the same business reads the same either way.
        "location": next(
            (f.value for f in brief.facts
             if f.field == "address" and f.confidence.value != "conflict"),
            brief.location),
        "website_url": brief.website_url,
        "site_reachable": brief.site_reachable,
        "site_status": brief.site_status,
        "url_check": ({
            "published": brief.url_check.published,
            "working": brief.url_check.working,
            "fault": brief.url_check.fault,
            "blocked": brief.url_check.blocked,
            "note": brief.url_check.note,
        } if brief.url_check is not None
            and (brief.url_check.fault or brief.url_check.blocked) else None),
        "notes": brief.notes,
        "facts": [fact_to_dict(f) for f in brief.facts],
        "published": (published_to_dict(published)
                      if show_published and published is not None else None),
        "assumptions": brief.assumptions,
        "open_questions": brief.open_questions,
        "sources_consulted": brief.sources_consulted,
        "chain_signals": brief.chain_signals,
        "ratings": brief.ratings,
    }
