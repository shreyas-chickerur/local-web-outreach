"""Turning what you typed into decisions the generator can act on.

Free text is the interface — "warm and rustic, put the menu first, they do a
lot of catering" — so this reads intent out of it rather than asking you to
fill in a form. What it cannot read, it leaves at a sensible default and
reports, so the panel can show you which parts of your sentence actually landed
instead of silently ignoring half of it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Section keys the generator knows how to build, in their default order.
SECTIONS = ("hero", "services", "menu", "gallery", "about", "hours", "contact")

_MOODS = {
    "warm": ("warm", ("rustic", "cozy", "homely", "welcoming", "warm", "farmhouse",
                      "comfort", "family")),
    "fresh": ("fresh", ("fresh", "clean", "bright", "airy", "light", "modern",
                        "minimal", "simple")),
    "bold": ("bold", ("bold", "loud", "punchy", "vibrant", "energetic", "fun",
                      "playful", "young")),
    "refined": ("refined", ("elegant", "refined", "upscale", "premium", "luxury",
                            "fine", "classy", "sophisticated")),
    "industrial": ("industrial", ("industrial", "urban", "raw", "concrete",
                                  "workshop", "garage", "tough", "rugged")),
    "night": ("night", ("dark", "moody", "night", "bar", "lounge", "izakaya",
                        "speakeasy")),
}

_SECTION_WORDS = {
    "menu": ("menu", "dishes", "food", "prices", "pricing"),
    "gallery": ("photo", "photos", "gallery", "images", "pictures"),
    "services": ("services", "what they do", "offerings", "catering", "work"),
    "hours": ("hours", "opening", "times", "schedule"),
    "contact": ("contact", "phone", "call", "directions", "map", "address"),
    "about": ("about", "story", "history"),
}

_CTA_WORDS = {
    "call": ("call", "phone", "ring"),
    "book": ("book", "booking", "reserve", "reservation", "table", "appointment"),
    "order": ("order", "delivery", "takeout", "take-out", "pickup"),
    "quote": ("quote", "estimate", "enquiry", "inquiry", "consultation"),
    "visit": ("visit", "directions", "come in", "walk in"),
}


@dataclass
class SiteSpec:
    """What to build. Every field has a defensible default."""

    text: str = ""
    mood: str = "fresh"
    lead_with: str | None = None        # a section hoisted to the top
    emphasis: list[str] = field(default_factory=list)
    cta: str | None = None
    one_page: bool = True
    understood: list[str] = field(default_factory=list)
    ignored: list[str] = field(default_factory=list)
    # Asked for, but impossible with what this business publishes. Silently
    # dropping the instruction would leave you thinking it had been applied.
    unmet: list[str] = field(default_factory=list)


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z][a-z'-]+", text.lower())


def parse_spec(text: str, *, default_cta: str | None = None) -> SiteSpec:
    spec = SiteSpec(text=text.strip())
    words = set(_words(text))
    if not words:
        spec.cta = default_cta
        return spec

    for name, triggers in _MOODS.values():
        if words & set(triggers):
            spec.mood = name
            spec.understood.append(f"styled {name}")
            break

    # "menu first", "lead with the gallery", "put photos up top"
    lead = re.search(r"(?:lead with|start with|open with|put)\s+(?:the\s+)?(\w+)"
                     r"|(\w+)\s+(?:first|up top|at the top)", text, re.IGNORECASE)
    if lead:
        named = (lead.group(1) or lead.group(2) or "").lower()
        for section, triggers in _SECTION_WORDS.items():
            if named in triggers:
                spec.lead_with = section
                spec.understood.append(f"led with the {section}")
                break

    for section, triggers in _SECTION_WORDS.items():
        if words & set(triggers) and section != spec.lead_with:
            spec.emphasis.append(section)

    for cta, triggers in _CTA_WORDS.items():
        if words & set(triggers):
            spec.cta = cta
            spec.understood.append(f"a “{cta}” call to action")
            break
    spec.cta = spec.cta or default_cta

    if words & {"multi-page", "pages", "subpages"}:
        spec.one_page = False
        spec.understood.append("more than one page")

    # Say what did not land, so a sentence is never half-ignored in silence.
    known = set()
    for _, triggers in _MOODS.values():
        known |= set(triggers)
    for triggers in _SECTION_WORDS.values():
        known |= set(triggers)
    for triggers in _CTA_WORDS.values():
        known |= set(triggers)
    content = {w for w in words if len(w) > 3} - known - _FILLER
    spec.ignored = sorted(content)[:6]
    return spec


_FILLER = {
    "with", "that", "this", "make", "made", "look", "looks", "site", "website",
    "them", "they", "their", "please", "want", "need", "like", "some", "more",
    "less", "very", "really", "should", "would", "could", "have", "has", "and",
    "the", "for", "but", "not", "you", "your", "our", "keep", "give", "show",
    "lot", "lots", "much", "into", "from", "also", "just", "then", "first",
    "button", "vibe", "emphasise", "emphasize", "emphasis", "focus", "big",
    "small", "put", "lead", "top", "list", "page", "style", "styled", "feel",
}
