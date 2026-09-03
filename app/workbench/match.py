"""Deciding whether two records describe the same business.

A directory search returns its best guess, which is regularly a different
company with a similar name. Every lookup result passes through here before its
data is believed — two Frisco roofers once "matched" one unrelated listing, and
its phone number then looked like evidence our own data was wrong.

Being too strict costs just as much. Refusing "J's Lawn Care" as different from
"JS Lawn Care Service", or "Starbucks Coffee Company" as different from
"Starbucks", throws away correct data and leaves the brief empty. So two rules
run: word overlap, and — for a name that is simply a shorter form of the other —
containment, guarded so that a generic fragment like "Lawn Care" cannot match
every lawn company in the county.
"""

from __future__ import annotations

import re

_STOPWORDS = {"the", "a", "an", "of", "and", "llc", "inc", "co", "ltd",
              "corp", "company", "lp", "plc"}

# Words that describe a trade rather than identify a business. A name made only
# of these is not distinctive enough to match on containment alone.
_GENERIC = {
    "lawn", "care", "service", "services", "landscaping", "roofing", "plumbing",
    "kitchen", "restaurant", "cafe", "coffee", "grill", "bar", "bakery", "salon",
    "dental", "auto", "repair", "cleaning", "construction", "group", "solutions",
    "shop", "store", "studio", "center", "centre", "clinic", "spa", "pizza",
    "food", "catering", "design", "supply", "electric", "hvac", "pest",
}

MATCH_THRESHOLD = 0.6
# Kept for callers that imported the old name.
NAME_MATCH_THRESHOLD = MATCH_THRESHOLD


def name_tokens(value: str | None) -> set[str]:
    """Significant words. Apostrophes are removed rather than split on, so
    "J's" and "JS" are the same token — otherwise a possessive silently makes
    two spellings of one business look unrelated."""
    cleaned = re.sub(r"[’']", "", (value or "").lower())
    words = re.sub(r"[^a-z0-9\s]", " ", cleaned).split()
    return {w for w in words if w and w not in _STOPWORDS}


def name_similarity(a: str, b: str) -> float:
    """Jaccard overlap of significant words. 1.0 identical, 0.0 nothing shared."""
    ta, tb = name_tokens(a), name_tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _is_shorter_form(a: str, b: str) -> bool:
    """True when one name is simply the other plus extra words.
    "Starbucks" inside "Starbucks Coffee Company"."""
    ta, tb = name_tokens(a), name_tokens(b)
    if not ta or not tb:
        return False
    shorter, longer = (ta, tb) if len(ta) <= len(tb) else (tb, ta)
    return shorter <= longer


def _shares_something_distinctive(a: str, b: str) -> bool:
    """The overlap must contain a word that identifies a business, not just one
    that describes a trade. "Ryno Lawn Care" and "Lawn Care" share two of three
    words, but both are generic — that is not evidence of the same company."""
    return bool((name_tokens(a) & name_tokens(b)) - _GENERIC)


def same_business(a: str, b: str, threshold: float = MATCH_THRESHOLD) -> bool:
    if not _shares_something_distinctive(a, b):
        return False
    return name_similarity(a, b) >= threshold or _is_shorter_form(a, b)
