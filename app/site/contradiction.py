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

# A number, optionally comma-grouped, followed by up to two review/
# rating-context words, then "review(s)" — "90,000 Google reviews",
# "15,000 five-star reviews", "6,203 reviews". Widened in Phase 2b from
# a fixed "optionally a star rating" slot: that version required the
# number to sit immediately beside "review(s)" (only "5-star" tolerated
# in between), so "90,000 Google reviews" — a real shape a rendered page
# can carry — was invisible to this expression entirely, the one place
# gap 2's own unbacked number WOULD have been caught if this pattern had
# reached it.
#
# Deliberately NOT "any word, up to three of them" (the round's own
# first phrasing): tried that first, and it turned
# tests/test_no_contradicted_fact_ships.py red on the real corpus —
# barbecue-rich renders a service literally titled "Turkey Sandwich
# review by Sabrina" (someone's name, not a review count), and "03
# Turkey Sandwich review" (the "03" a sibling carousel index the
# standing test's own simpler tag-stripping concatenates onto it)
# matched as a false "review count" purely because two arbitrary words
# sat between a number and the word "review". A closed, small allowlist
# of the words that actually appear in this shape avoids that collision
# entirely while still catching the real one.
_REVIEW_WORD = r"google|yelp|facebook|verified|genuine|happy|satisfied|five[- ]star|5[- ]star"
# Only plain spaces/tabs between the parts, never a newline — this
# operates on one sentence at a time, but the same expression is reused
# by the standing test over rendered HTML, where an unrelated heading
# and the next section's can sit a newline apart; requiring the words on
# one line keeps both readings of "contradiction" the same thing.
# Public: Phase 2 Step 3 (app.site.seam_gates) imports both this and
# `contradicts` to build a real GATE over the rendered page, rather than
# copying either — and tests/test_no_contradicted_fact_ships.py, which
# used to carry its own second copy of both, now imports them too.
REVIEW_COUNT_RE = re.compile(
    rf"\b([\d,]{{2,}})\+?[ \t]*(?:(?:{_REVIEW_WORD})[ \t]+){{0,2}}reviews?\b",
    re.IGNORECASE)

# How far a stated count can drift from the corroborated one before it reads
# as a contradiction rather than rounding or a slightly stale scrape. Both a
# floor (small counts) and a percentage (large ones) — 6,203 said as "over
# 6,000" is a business rounding down, not a defect; 6,203 said as "20,000"
# is roughly 3x over and is.
_ABSOLUTE_FLOOR = 10
_RELATIVE_TOLERANCE = 0.15


def contradicts(claimed: int, actual: int) -> bool:
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
        match = REVIEW_COUNT_RE.search(sentence)
        if match:
            claimed = int(match.group(1).replace(",", ""))
            if contradicts(claimed, reviews):
                continue
        kept.append(sentence)
    return " ".join(kept)
