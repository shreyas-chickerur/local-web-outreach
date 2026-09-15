"""Phase 2/2b: the existing content gates, ported onto `visible.py`.

Four gates, unchanged in PURPOSE from what they replace, changed in
WHAT THEY READ — a rendered page's visible text runs
(`app.site.visible.visible_text_runs`), never source markup — and in
HOW they decide something is backed: sentence-level, not bag-of-words,
and never exempted from a check just because a run is short. See
`.reviews/phase-2-seam.md` and `.reviews/phase-2b-seam.md` for the gaps
each change closes and the planted-fabrication corpus
(`tests/fixtures/seam/`) that pins them.

Phase 2b's own finding: Phase 2's `is_template_chrome()` did two jobs
at once — deciding what to exempt from PROVENANCE (a full sentence
check) and deciding what to exempt from the CLAIMS check (`CLAIM_RE`)
— and a short run (a badge, a stat tile, a `<button>`) got both for
free, regardless of whether anything corroborated it. `gate()` is the
ported `pipeline._gate()`: `unsupported_sentences()` and
`unexplained_prose()` (the original two, sentence-aware and now
correctly separated), `unbacked_numbers()` (new — no gate before this
round ever checked a number at all), and `contradicted_review_counts()`
(new in Phase 2 — imported from `app.site.contradiction` rather than
reimplemented, so the pre-render transform and this rendered-page gate
cannot drift apart).
"""

from __future__ import annotations

import re

from app.core.claims import CLAIM_RE
from app.site import contractorfacts, contradiction, provenance
from app.site.visible import VisibleRun

# Chrome for PROVENANCE (unexplained_prose) only — Phase 2b narrows this
# from Phase 2's version, which also exempted any heading of <=3 words
# and any run of <=4 words with no terminal punctuation. Both of those
# turned out to double as an exemption from the CLAIMS check too (see
# unsupported_sentences below, which no longer calls this at all) and
# a stat tile / badge / short button is exactly the shape a planted
# short-form claim (Phase 2b class 7) takes. Left standing because it is
# still correct for what it actually says: navigation, a form, and a
# label are never a sentence a business wrote for this page to read as
# prose, and a genuinely short link/button text ("Home", "Read more")
# is a control label, not an assertion — a LONGER one is prose, and Step
# 2's own worked example (threadbare's <button>, nine words) is exactly
# why the length limit stays at three, not "everything in <button>".
_CHROME_TAGS = frozenset({"nav", "label", "form"})
_SHORT_CHROME_TAGS = frozenset({"a", "button"})
_SHORT_CHROME_WORD_LIMIT = 3

# Phase 2's `_BOILERPLATE_WORDS` / `_is_all_facts_and_boilerplate()` is
# gone outright, not narrowed — the mechanism itself (exempt a run whose
# words are all "safe" connectives) is what let gap 2 through, since it
# scanned only `[a-z]+` and could never see a number at all. Numbers are
# now `unbacked_numbers()`'s job, unconditionally; text is chrome only by
# the tag rule above. Audited on the way out, per Step 2's own
# instruction, one line per entry:
#
# DELETED, and were the actual masking risk (directly enabled gap 2 —
# each one is a word that sits right next to the number in "N average
# rating from M [word] reviews", making the whole phrase read as "safe"
# connective text with the fabricated number invisible inside it):
#   average, rating, stars, star, from, across, google, reviews, review
#
# DELETED, but were not themselves adjacent to a claim or a number (no
# masking incident traces to these — removed anyway because the whole
# mechanism is gone, not because any one of them was independently
# risky):
#   follow, along, get, directions, direction, call, book, order,
#   estimate, free, written, clear, table, to, a, an, the, and, for, on,
#   off, offer, what, we, cook, serve, am, pm, mon, tue, wed, thu, fri,
#   sat, sun, monday, tuesday, wednesday, thursday, friday, saturday,
#   sunday, address, phone, email, dishes, menu, instagram, facebook,
#   tiktok, linkedin, yelp, twitter, x
#
# "dishes"/"menu" (the "N dishes on the menu" stat) deserve their own
# note: masking WAS possible here too, in principle, the same shape as
# the review-count case — but `_corroborated_numbers()` below adds
# `len(material.menu_items)` explicitly, so `unbacked_numbers()` now
# checks that count on its own regardless of what surrounds it.


def is_template_chrome(run: VisibleRun) -> bool:
    """The closed rule for PROVENANCE only. Never consulted by
    unsupported_sentences() or unbacked_numbers() — a claim or a number
    is backed by evidence, never by which tag it happens to sit in."""
    if run.tag in _CHROME_TAGS:
        return True
    if run.tag in _SHORT_CHROME_TAGS:
        return len(run.text.split()) <= _SHORT_CHROME_WORD_LIMIT
    return False


def _sentences_of(run: VisibleRun) -> list[str]:
    return [s.strip() for s in provenance.SENTENCE_RE.split(run.text) if s.strip()]


# The old, regex-over-source gates never faced this: `_PROSE_RE` captures
# only the text BETWEEN the literal `&ldquo;`/`&rdquo;` markers, so a
# quote's own decorative wrapper characters were never part of the
# extracted sentence to begin with. Reading the RENDERED DOM, those
# entities are already decoded into real curly-quote characters sitting
# directly in the text (`“I recently had…”`), and a trailing ellipsis a
# truncated quote ends with can itself be followed by a closing quote
# mark (`…”`) rather than being the very last character.
_WRAPPING_PUNCTUATION = "\"'“”‘’…"


def _bare(sentence: str) -> str:
    return sentence.strip(_WRAPPING_PUNCTUATION).strip().lower()


def _own(material) -> str:
    """Everything a rendered sentence could legitimately trace back to:
    `provenance.own_words()`'s free-text fields, plus every corroborated
    structured field and scraped heading/entry `_corroborated_facts`
    covers. One shared corpus for every check in this module, so a
    heading found verbatim by one function is not somehow re-flagged by
    another that forgot to widen the same way."""
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


def _material_contractor_facts(material) -> frozenset[str]:
    """Which `contractorfacts` keys the business's OWN words (about +
    every block's text) actually corroborate — the same source
    `app.site.contractorfacts.found()` is already trusted against
    elsewhere in this codebase (the `credentials` section builder),
    reused here rather than a second read of the same fields."""
    text = " ".join([material.about or ""]
                    + [str(b.get("text", "")) for b in material.blocks])
    return frozenset(contractorfacts.found(text))


def unsupported_sentences(runs: list[VisibleRun], material) -> list[str]:
    """Port of `render.unsupported()`: a CLAIM_RE match only counts if
    the SENTENCE it appears in is itself verbatim-or-prefix-cut source,
    OR the claim is a credential `contractorfacts.found()` also finds
    in the business's own material (`_material_contractor_facts`) — not
    merely a claim PHRASE appearing anywhere in the material, which
    lets an unrelated word (a customer review's incidental "certified
    technicians") launder an unrelated, uncorroborated sentence built by
    whoever wrote the page.

    Runs UNCONDITIONALLY — no chrome exemption. Phase 2b's own finding:
    exempting short runs and everything in <button> here (Phase 2's
    version) reopened the credential invariant outright — a page with
    NO corroborating material at all (`tests/fixtures/seam/
    threadbare-foreign.html`) still came back clean, because every
    credential badge was short enough, or inside a <button>, to skip
    this check entirely regardless of whether anything backed it.
    """
    own = _own(material)
    material_facts = _material_contractor_facts(material)
    found: list[str] = []
    seen: set[str] = set()
    for run in runs:
        for sentence in _sentences_of(run):
            bare = _bare(sentence)
            if bare and bare in own:
                continue
            if set(contractorfacts.found(sentence)) & material_facts:
                # "Licensed & insured" built by contractorfacts.py's own
                # credentials section passes because the corroborating
                # FACT is present in their own material (checked here,
                # explicitly) — never because the run happened to be
                # short or sat inside a <button>.
                continue
            for match in CLAIM_RE.finditer(sentence):
                claim = match.group(0)
                if claim.lower() not in seen:
                    seen.add(claim.lower())
                    found.append(claim)
    return found


def unexplained_prose(runs: list[VisibleRun], material) -> list[str]:
    """Port of `provenance.unexplained_sentences()`: every visible
    sentence that is not template chrome (`is_template_chrome` — now
    only nav/label/form and a short `<a>`/`<button>`, Phase 2b's own
    tightened rule), checked the same verbatim-or-prefix-cut way as
    before.
    """
    own = _own(material)
    found: list[str] = []
    seen: set[str] = set()
    for run in runs:
        if is_template_chrome(run):
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


# Matches an integer, a comma-grouped integer, a decimal, an "N+" count,
# or a percent — the shapes Phase 2b's own instruction names (integers,
# comma groups, decimals, N+, percents, years; a year is just a 4-digit
# integer, no separate pattern needed). "24/7" is excluded before this
# ever runs (see unbacked_numbers) — it is an idiom for round-the-clock
# availability (contractorfacts.py's own "emergency" pattern reads it
# the same way), not a quantity claim, and its two halves are not
# independently a fact to corroborate.
_NUMBER_RE = re.compile(r"\b\d[\d,]*(?:\.\d+)?%?\+?")
_TWENTY_FOUR_SEVEN_RE = re.compile(r"\b24\s*/\s*7\b")


def _normalize_number(token: str) -> str:
    return token.rstrip("%").rstrip("+").replace(",", "")


def _corroborated_numbers(material) -> frozenset[str]:
    """Every number that IS, itself, a corroborated field value — not a
    scan of free text (a number inside a verbatim-matched sentence is
    the OTHER half of the round's own rule, handled separately in
    unbacked_numbers by skipping verbatim-matched sentences entirely,
    the same way every other check in this module does)."""
    nums: set[str] = set()
    if material.rating is not None:
        nums.add(_normalize_number(str(material.rating)))
    if material.reviews is not None:
        nums.add(_normalize_number(str(material.reviews)))
    if material.phone:
        nums.add(re.sub(r"\D", "", material.phone))
    for h in material.hours:
        nums.update(_normalize_number(n) for n in _NUMBER_RE.findall(h))
    for item in material.menu_items:
        nums.update(_normalize_number(n)
                   for n in _NUMBER_RE.findall(str(item.get("price", ""))))
    # A count OUR OWN RENDERER computes and may print ("24 dishes on the
    # menu") -- a real, deterministic fact about the page, not a claim
    # about the business, but still a number a run can state.
    nums.add(str(len(material.menu_items)))
    nums.add(str(len(material.services)))
    return frozenset(n for n in nums if n)


def unbacked_numbers(runs: list[VisibleRun], material) -> list[str]:
    """Every number (integer, comma group, decimal, N+, percent, year)
    in any visible run that neither equals a corroborated field value
    nor sits inside a sentence already verbatim-or-prefix-cut from their
    own material. Runs UNCONDITIONALLY, same as unsupported_sentences —
    no chrome exemption, no length exemption. This is the gate that did
    not exist before Phase 2b: Phase 2's `_is_all_facts_and_boilerplate`
    scanned only `[a-z]+` runs, so "90,000" in "4.9 average rating from
    90,000 Google reviews" was invisible to every check that ran, gate
    or contradiction alike.
    """
    own = _own(material)
    corroborated = _corroborated_numbers(material)
    found: list[str] = []
    seen: set[str] = set()
    for run in runs:
        for sentence in _sentences_of(run):
            bare = _bare(sentence)
            if bare and bare in own:
                continue
            cleaned = _TWENTY_FOUR_SEVEN_RE.sub(" ", sentence)
            for token in _NUMBER_RE.findall(cleaned):
                normalized = _normalize_number(token)
                if not normalized or normalized in corroborated:
                    continue
                if token not in seen:
                    seen.add(token)
                    found.append(token)
    return found


def contradicted_review_counts(runs: list[VisibleRun], material) -> list[str]:
    """A sentence stating a review count that contradicts
    `material.reviews`, read straight off the rendered page. Same
    expression (`contradiction.REVIEW_COUNT_RE`) and same tolerance
    (`contradiction.contradicts`) `contradiction.reconcile()` already
    applies to free text before render — imported, not copied, so the
    two readings of "contradiction" cannot drift apart.
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
    """The ported `pipeline._gate()`: all four, concatenated."""
    return (unsupported_sentences(runs, material)
            + unexplained_prose(runs, material)
            + unbacked_numbers(runs, material)
            + contradicted_review_counts(runs, material))
