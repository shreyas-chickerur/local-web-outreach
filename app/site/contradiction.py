"""BRIEF §4: a business's own marketing copy does not outrank a value this
system independently corroborates. When the two disagree, the copy sentence
is dropped — never rewritten, since this system never authors prose.

`hvac`'s own "about" text claims "over 20,000 5 star reviews" while its
corroborated Google review count (`Material.reviews`) is 6,203, printed
elsewhere on the same page. Both are real: the copy is verbatim from the
business's own published text, and the count comes from structured rating
data, so `render.unsupported()` — which checks provenance, whether they said
it, not consistency, whether their own numbers agree with each other — was
right to let it through. Nothing before this checked their own words against
each other. See `.reviews/slice-c-credential-claims.md` for the shape of the
first fix in this family (an unverified claim); this is the second shape
(two verified claims that contradict).

Scoped to review counts because that is the one quantity this project has a
corroborated structured counterpart for (`Material.reviews`, from rating
data). "Years in business", "customers served" and "jobs completed" show up
in this corpus too but nothing here tracks a founding date, a customer
count, or a jobs-completed count to check them against — there is nothing to
reconcile, so nothing is touched.
"""

from __future__ import annotations

import re

# A number, optionally comma-grouped, immediately followed by "review(s)",
# optionally preceded by a star rating ("5-star reviews"). The one quantity
# with a corroborated structured counterpart (`Material.reviews`). Only
# plain spaces/tabs between the parts, never a newline — this operates on
# one sentence at a time, but the same expression is reused by the standing
# test over rendered HTML, where an unrelated heading and the next
# section's can sit a newline apart; requiring the words on one line keeps
# both readings of "contradiction" the same thing.
_REVIEW_COUNT_RE = re.compile(
    r"\b([\d,]{2,})\+?[ \t]*(?:5[- ]star[ \t]+)?reviews?\b", re.IGNORECASE)

# How far a stated count can drift from the corroborated one before it reads
# as a contradiction rather than rounding or a slightly stale scrape. Both a
# floor (small counts) and a percentage (large ones) — 6,203 said as "over
# 6,000" is a business rounding down, not a defect; 6,203 said as "20,000"
# is roughly 3x over and is.
_ABSOLUTE_FLOOR = 10
_RELATIVE_TOLERANCE = 0.15


def _contradicts(claimed: int, actual: int) -> bool:
    return abs(claimed - actual) > max(_ABSOLUTE_FLOOR,
                                       round(actual * _RELATIVE_TOLERANCE))


def reconcile(text: str | None, reviews: int | None) -> str | None:
    """Drop any sentence in `text` that states a review count contradicting
    the corroborated `reviews` value. Every other sentence is untouched —
    the fix is a sentence dropped, never a sentence rewritten."""
    if not text or reviews is None:
        return text
    sentences = re.split(r"(?<=[.!?])\s+", text)
    kept = []
    for sentence in sentences:
        match = _REVIEW_COUNT_RE.search(sentence)
        if match:
            claimed = int(match.group(1).replace(",", ""))
            if _contradicts(claimed, reviews):
                continue
        kept.append(sentence)
    return " ".join(kept)
