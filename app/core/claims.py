"""What counts as a claim about a business.

Lives here, below both the adapters and the generator, because two places need
the same answer and a second copy of this expression would drift within a week.

The rule it enforces is the one the whole product rests on: the page is shown
to the owner, so one sentence they know to be false ends the meeting. Generic
copy is fine. "Family owned since 1994" is not, unless they said it first.
"""

from __future__ import annotations

import re

CLAIM_RE = re.compile(
    r"\b(since \d{4}|est\.? ?\d{4}|\d+\+? years|award[- ]winning|voted|"
    r"best in|number one|top[- ]rated|family[- ]owned|family[- ]run|"
    r"trusted by|"
    r"\d+ (?:happy )?(?:customers|clients)|five[- ]star|5[- ]star|"
    # Credential and licensure language — added after `signature.py`'s
    # `stamp` device shipped "Licensed & insured" / "Registered practice" /
    # "Admitted to the bar" unconditionally on trade_kind alone, on six
    # fixtures whose own material corroborated none of it. This is a
    # pattern over the LANGUAGE of a credential claim, not the three exact
    # strings that device happened to print — the next device or section
    # that asserts one has to clear the same bar.
    r"licen[sc]ed|bonded|insured|certified|accredited|"
    r"board[- ]certified|admitted to the bar|state bar|"
    r"registered (?:practice|nurse|hygienist|dietitian|agent))\b"
    # "#1" as its own alternative, outside the shared \b(...)\b group:
    # "#" is a non-word character, so \b immediately before it can only
    # ever hold when "#" is glued directly onto a preceding word
    # character ("Ranked#1") — the one shape that never occurs in real
    # copy. Every real planting in this corpus (and every natural
    # sentence: "voted #1", "the #1", "#1 in Texas") has a space or
    # start-of-string before "#", which is non-word on both sides of
    # that position, so \b never matched there at all. A negative
    # lookbehind for a word character, not \b, is the right boundary
    # here; the trailing \b after "1" still keeps "#100" from matching
    # as a bare "#1".
    r"|(?<!\w)#1\b",
    re.IGNORECASE)


def reads_as_claim(text: str) -> bool:
    """Does this sentence assert something only their own sources can settle?

    Used on model-written alt text, which is the one place text about a
    photograph is allowed onto the page. Describing what is visible is
    checkable by looking; "the award-winning signature dish" is not.
    """
    return bool(CLAIM_RE.search(text or ""))
