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
    r"best in|number one|#1|family[- ]owned|family[- ]run|trusted by|"
    r"\d+ (?:happy )?(?:customers|clients)|five[- ]star|5[- ]star)\b",
    re.IGNORECASE)


def reads_as_claim(text: str) -> bool:
    """Does this sentence assert something only their own sources can settle?

    Used on model-written alt text, which is the one place text about a
    photograph is allowed onto the page. Describing what is visible is
    checkable by looking; "the award-winning signature dish" is not.
    """
    return bool(CLAIM_RE.search(text or ""))
