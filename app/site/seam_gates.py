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


# Boilerplate connective words a rendered stat tile, footer, or CTA is
# built from regardless of which business it names — "4.6 average
# rating", "Get a free estimate", "Follow along", "Mon - Fri: 8:00am to
# 6:00pm". None of these ASSERT anything about the business on their
# own; every fact-bearing word beside them (the number, the address,
# the platform name) already has to clear `_corroborated_facts`
# separately. A closed list, not a heuristic guess: every entry here
# was found by running this gate against the real 19-fixture corpus
# and reading what was left over once every genuine corroborated field
# value was already accounted for.
_BOILERPLATE_WORDS = frozenset({
    "average", "rating", "stars", "star", "from", "across", "google",
    "reviews", "review", "follow", "along", "get", "directions",
    "direction", "call", "book", "order", "estimate", "free", "written",
    "clear", "table", "to", "a", "an", "the", "and", "for", "on", "off",
    "offer", "what", "we", "cook", "serve", "am", "pm",
    "mon", "tue", "wed", "thu", "fri", "sat", "sun", "monday", "tuesday",
    "wednesday", "thursday", "friday", "saturday", "sunday",
    "address", "phone", "email", "dishes", "menu",
    "instagram", "facebook", "tiktok", "linkedin", "yelp", "twitter", "x",
})
_WORD_RE = re.compile(r"[a-z]+")


def _is_all_facts_and_boilerplate(text: str, material) -> bool:
    """True if nothing in `text` is left unaccounted for once every
    digit/punctuation, every corroborated field value, and every known
    boilerplate connective word is set aside — a stat tile or a footer
    line built entirely out of real facts and glue, however they got
    merged into one run, is not "unexplained": there is no free-form
    assertion left inside it to explain."""
    facts = _corroborated_facts(material)
    remainder = text.lower()
    for value in sorted((v for v in re.split(r"\s{2,}|(?<=\S)(?=\d)", facts) if v),
                        key=len, reverse=True):
        remainder = remainder.replace(value, " ")
    for word in _WORD_RE.findall(remainder):
        if word not in _BOILERPLATE_WORDS and word not in facts:
            return False
    return True


def is_template_chrome(run: VisibleRun, material=None) -> bool:
    """The closed rule. A function, not a table, so it is testable on
    its own and every caller applies exactly the same one.

    `material`, when given, additionally excludes a run built entirely
    out of corroborated field values and boilerplate connectives (a
    merged stat tile, an address/hours footer) regardless of its own
    length or punctuation — see `_is_all_facts_and_boilerplate`.
    """
    if run.tag in _CHROME_TAGS:
        return True
    words = run.text.split()
    if run.tag in _HEADING_TAGS and len(words) <= 3:
        return True
    if len(words) <= 4 and not _TERMINAL_PUNCTUATION_RE.search(run.text):
        return True
    return material is not None and _is_all_facts_and_boilerplate(run.text, material)


def _sentences_of(run: VisibleRun) -> list[str]:
    return [s.strip() for s in provenance.SENTENCE_RE.split(run.text) if s.strip()]


# The old, regex-over-source gates never faced this: `_PROSE_RE` captures
# only the text BETWEEN the literal `&ldquo;`/`&rdquo;` markers, so a
# quote's own decorative wrapper characters were never part of the
# extracted sentence to begin with. Reading the RENDERED DOM, those
# entities are already decoded into real curly-quote characters sitting
# directly in the text (`“I recently had…”`), and a trailing ellipsis a
# truncated quote ends with can itself be followed by a closing quote
# mark (`…”`) rather than being the very last character — found running
# this against the real 19-fixture corpus: every quoted testimonial on
# every fixture came back as a "new" false-positive finding purely
# because of this, not because the quote itself was unsupported.
_WRAPPING_PUNCTUATION = "\"'“”‘’…"


def _bare(sentence: str) -> str:
    return sentence.strip(_WRAPPING_PUNCTUATION).strip().lower()


def _own(material) -> str:
    """Everything a rendered sentence could legitimately trace back to:
    `provenance.own_words()`'s free-text fields, plus every corroborated
    structured field and scraped heading/entry `_corroborated_facts`
    covers. One shared corpus for every check in this module, so a
    heading found verbatim by one function is not somehow re-flagged
    by another that forgot to widen the same way."""
    return provenance.own_words(material) + " " + _corroborated_facts(material)


def _corroborated_facts(material) -> str:
    """Field VALUES that are corroborated by construction — they came
    straight off a structured source (a directory listing, a scrape of
    the business's own hours/contact block), never typed by a model —
    so a rendered stat tile or footer line built out of them can never
    be "unexplained": there is nothing to explain, it is the field.

    `provenance.own_words()` only ever covered the free-TEXT fields
    (about, blocks, quotes...) because the old, regex-over-five-classes
    gate never read a stat tile, an address line, or a review's own
    star rating in the first place — reading the real rendered page
    now does, so this is genuinely new surface, not a widened version
    of an old gap.
    """
    parts = [
        material.name or "", material.address or "", material.phone or "",
        material.email or "", str(material.rating or ""),
        str(material.reviews or ""), material.trade or "",
        " ".join(material.hours),
        " ".join(str(s.get("platform", "")) for s in material.socials),
        " ".join(str(q.get("author", "")) for q in material.quotes),
        " ".join(f"{i.get('name', '')} {i.get('price', '')}"
                 for i in material.menu_items),
        # A block's HEADING and KICKER are their own real, scraped words
        # too — `render.unsupported`'s own_words never needed them
        # because the old gate never read a heading as prose (headings
        # were never one of its five prose classes); this gate does, so
        # this is genuinely new surface to cover, not a widened old gap.
        " ".join(str(b.get("heading", "")) for b in material.blocks),
        " ".join(str(b.get("kicker", "")) for b in material.blocks
                 if b.get("kicker")),
        # A "partners" block's entries print as "name — note" but store
        # as {name, note} pairs, not in the block's own `text` field —
        # found running this against restaurant-rich's real partner list.
        " ".join(f"{e.get('name', '')} {e.get('note', '')}"
                 for b in material.blocks for e in (b.get("entries") or [])),
    ]
    return re.sub(r"\s+", " ", " ".join(parts)).strip().lower()


def unsupported_sentences(runs: list[VisibleRun], material) -> list[str]:
    """Port of `render.unsupported()`: a CLAIM_RE match only counts if
    the SENTENCE it appears in is itself verbatim-or-prefix-cut source —
    not merely a claim PHRASE appearing anywhere in the material, which
    lets an unrelated word (a customer review's incidental "certified
    technicians") launder an unrelated, uncorroborated sentence built by
    whoever wrote the page. See tests/fixtures/seam/*-foreign.manifest.json
    class 2 for the exact planted case this closes.
    """
    own = _own(material)
    found: list[str] = []
    seen: set[str] = set()
    for run in runs:
        if is_template_chrome(run, material):
            # A badge assembled from already-corroborated words ("Licensed
            # & insured", built by app.site.contractorfacts's own match
            # against their material) is UI chrome, not a sentence to
            # re-check word-by-word against CLAIM_RE — the same reasoning
            # `is_template_chrome` already applies for unexplained_prose,
            # applied consistently here too. Found running this against
            # the real corpus: the combined heading "Licensed & insured"
            # is not itself a literal substring of their material even
            # though both words individually are, which is exactly the
            # bag-of-words gap this gate exists to close elsewhere — the
            # fix is not to re-open it for an already-corroborated device.
            continue
        for sentence in _sentences_of(run):
            bare = _bare(sentence)
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
    own = _own(material)
    found: list[str] = []
    seen: set[str] = set()
    for run in runs:
        if is_template_chrome(run, material):
            continue
        for sentence in _sentences_of(run):
            if sentence in provenance.GENERIC_COPY:
                continue
            bare = _bare(sentence)
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
