"""Phase 2, Step 3: the existing content gates, ported onto `visible.py`.

Three gates, unchanged in PURPOSE from what they replace, changed in
WHAT THEY READ — a rendered page's visible text runs
(`app.site.visible.visible_text_runs`), never source markup — and, for
`unsupported_sentences`, changed in HOW they decide a claim is backed:
sentence-level, not bag-of-words. See `.reviews/phase-2-seam.md` for the
gap each change closes and the planted-fabrication corpus
(`tests/fixtures/seam/`) that pins it.

`gate()` is the ported `pipeline._gate()`: the same two checks, sentence-
aware now, plus a third that never existed as a gate at all — the
review-count contradiction, imported from `app.site.contradiction`
rather than reimplemented (that module's own `REVIEW_COUNT_RE` and
`contradicts` are exactly what `contradiction.reconcile()` already
uses on OUR OWN pre-render text; a rendered-page gate needs the same
expression and tolerance, not a second copy that could drift from it).
"""

from __future__ import annotations

import re

from app.core.claims import CLAIM_RE
from app.site import contradiction, provenance
from app.site.visible import VisibleRun

# The closed rule Step 3 asks for, in place of provenance.py's old five
# CSS classes: what counts as template chrome, by TAG and SHAPE, not by
# a class list a foreign page will never share.
#
# - nav/button/a/label/form: never a sentence a business wrote for this
#   page to read as prose — navigation, a control, a form field.
# - a heading of three words or fewer: a section title ("Our Services"),
#   not an assertion.
# - four words or fewer with no sentence-ending punctuation: a single
#   field value — a price, a phone number, a bare stat ("15,000+",
#   "$99", "6203") — never "selected sentences" (BRIEF §5's own phrase
#   for what this file is scoped to, carried over from the five-class
#   version this replaces).
_CHROME_TAGS = frozenset({"nav", "button", "a", "label", "form"})
_HEADING_TAGS = frozenset({"h1", "h2", "h3", "h4", "h5", "h6"})
_TERMINAL_PUNCTUATION_RE = re.compile(r"[.!?]")


def is_template_chrome(run: VisibleRun) -> bool:
    """The closed rule. A function, not a table, so it is testable on
    its own and every caller applies exactly the same one."""
    if run.tag in _CHROME_TAGS:
        return True
    words = run.text.split()
    if run.tag in _HEADING_TAGS and len(words) <= 3:
        return True
    return len(words) <= 4 and not _TERMINAL_PUNCTUATION_RE.search(run.text)


def _sentences_of(run: VisibleRun) -> list[str]:
    return [s.strip() for s in provenance.SENTENCE_RE.split(run.text) if s.strip()]


def unsupported_sentences(runs: list[VisibleRun], material) -> list[str]:
    """Port of `render.unsupported()`: a CLAIM_RE match only counts if
    the SENTENCE it appears in is itself verbatim-or-prefix-cut source —
    not merely a claim PHRASE appearing anywhere in the material, which
    lets an unrelated word (a customer review's incidental "certified
    technicians") launder an unrelated, uncorroborated sentence built by
    whoever wrote the page. See tests/fixtures/seam/*-foreign.manifest.json
    class 2 for the exact planted case this closes.
    """
    own = provenance.own_words(material)
    found: list[str] = []
    seen: set[str] = set()
    for run in runs:
        for sentence in _sentences_of(run):
            bare = sentence.rstrip("…").strip().lower()
            if bare and bare in own:
                continue
            for match in CLAIM_RE.finditer(sentence):
                claim = match.group(0)
                if claim.lower() not in seen:
                    seen.add(claim.lower())
                    found.append(claim)
    return found


def unexplained_prose(runs: list[VisibleRun], material) -> list[str]:
    """Port of `provenance.unexplained_sentences()`: every visible
    sentence that is not template chrome (`is_template_chrome`, a closed
    tag/shape rule, not five CSS classes), checked the same
    verbatim-or-prefix-cut way as before.
    """
    own = provenance.own_words(material)
    found: list[str] = []
    seen: set[str] = set()
    for run in runs:
        if is_template_chrome(run):
            continue
        for sentence in _sentences_of(run):
            if sentence in provenance.GENERIC_COPY:
                continue
            bare = sentence.rstrip("…").strip().lower()
            if bare and bare in own:
                continue
            if sentence not in seen:
                seen.add(sentence)
                found.append(sentence)
    return found


def contradicted_review_counts(runs: list[VisibleRun], material) -> list[str]:
    """The gate that did not exist before this round: a sentence stating
    a review count that contradicts `material.reviews`, read straight
    off the rendered page. Same expression (`contradiction.REVIEW_COUNT_RE`)
    and same tolerance (`contradiction.contradicts`) `contradiction.
    reconcile()` already applies to free text before render — imported,
    not copied, so the two readings of "contradiction" cannot drift
    apart (the standing test used to carry its own copy of both; that
    is folded into this same import now too).
    """
    if material.reviews is None:
        return []
    found: list[str] = []
    seen: set[str] = set()
    for run in runs:
        for sentence in _sentences_of(run):
            match = contradiction.REVIEW_COUNT_RE.search(sentence)
            if not match:
                continue
            claimed = int(match.group(1).replace(",", ""))
            if contradiction.contradicts(claimed, material.reviews) and sentence not in seen:
                seen.add(sentence)
                found.append(sentence)
    return found


def gate(runs: list[VisibleRun], material) -> list[str]:
    """The ported `pipeline._gate()`: all three, concatenated, exactly
    the shape the original two-function version already had."""
    return (unsupported_sentences(runs, material)
            + unexplained_prose(runs, material)
            + contradicted_review_counts(runs, material))
