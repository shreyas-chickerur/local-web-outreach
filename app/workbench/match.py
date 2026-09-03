"""Deciding whether two records describe the same business.

A directory search returns its best guess, which is regularly a different
company with a similar name. Every lookup result passes through here before its
data is believed — two Frisco roofers once "matched" one unrelated listing, and
its phone number then looked like evidence our own data was wrong.
"""

from __future__ import annotations

import re

_STOPWORDS = {"the", "a", "an", "of", "and", "&", "llc", "inc", "co", "ltd",
              "corp", "company", "lp", "plc"}

# Below this, treat a lookup result as a different business.
NAME_MATCH_THRESHOLD = 0.6


def name_tokens(value: str | None) -> set[str]:
    words = re.sub(r"[^a-z0-9\s]", " ", (value or "").lower()).split()
    return {w for w in words if w and w not in _STOPWORDS}


def name_similarity(a: str, b: str) -> float:
    """Jaccard overlap of significant words. 1.0 is identical, 0.0 shares none."""
    ta, tb = name_tokens(a), name_tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def same_business(a: str, b: str, threshold: float = NAME_MATCH_THRESHOLD) -> bool:
    return name_similarity(a, b) >= threshold
