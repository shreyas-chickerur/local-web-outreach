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


# The `credentials` SECTION's own printed label ("Manufacturer
# certified", "Free estimate", "Service area"...) does not always match
# the very pattern that detected the fact in the business's own words —
# `contractorfacts.py`'s patterns are tuned to a business's real
# phrasing ("certified installer", "financing"), not to the device's own
# fixed label text. Found running Step 2's fix against the real corpus:
# "Manufacturer certified" (the label) matches none of the
# manufacturer_badge patterns, so contractorfacts.found() on the
# RENDERED label came back empty even on fixtures where the fact is
# genuinely, separately corroborated. A label that IS one of these exact
# strings is checked by KEY instead of by re-matching its own pattern.
_LABEL_TO_KEY = {contractorfacts.label_for(fact.key): fact.key
                 for fact in contractorfacts.FACTS}


# Phase 2c's own finding (`.reviews/NEXT-ROUND.md`): `_credential_backed`
# used to return a bool and the two callers below `continue`d past the
# WHOLE sentence on True. hvac's own material corroborates
# `licensed_insured` — but "Licensed and insured, award-winning and voted
# best in Plano." is one sentence, and the old behaviour let the real
# credential vouch for the two invented superlatives riding along with it.
# The bag-of-words laundering gap Phase 2b closed once (a word anywhere in
# their material excusing a whole sentence), reopened one level up (a FACT
# anywhere in the sentence excusing the whole sentence). Fixed the same way:
# narrow what gets exempted to exactly the matched span, never the sentence
# around it, and let every other check run on what is left.
_CONNECTIVE_ONLY_RE = re.compile(r"^[\s,&]*(?:and[\s,&]*)*$", re.IGNORECASE)


def _credential_backed_remainder(sentence: str, material_facts: frozenset[str]) -> str:
    """`sentence` with every span a corroborated credential accounts for
    removed — a `contractorfacts` pattern match for a fact in
    `material_facts`, and the device's own exact label
    (`_LABEL_TO_KEY`) when the whole sentence IS that label. Only ever
    removes what is actually backed; a fact this material does not
    corroborate leaves its span untouched, so an uncorroborated
    credential word still reaches CLAIM_RE / the provenance check same
    as before."""
    spans: list[tuple[int, int]] = []
    for fact in contractorfacts.FACTS:
        if fact.key not in material_facts:
            continue
        spans.extend(m.span() for m in fact.pattern.finditer(sentence))
    stripped = sentence.strip()
    key = _LABEL_TO_KEY.get(stripped)
    if key is not None and key in material_facts and stripped:
        start = sentence.find(stripped)
        spans.append((start, start + len(stripped)))
    if not spans:
        return sentence
    parts: list[str] = []
    cursor = 0
    for start, end in sorted(spans):
        if start < cursor:
            continue
        parts.append(sentence[cursor:start])
        cursor = end
    parts.append(sentence[cursor:])
    return "".join(parts)


def _is_pure_connective_remainder(remainder: str) -> bool:
    """"Licensed & insured" backs both halves of itself, via two separate
    contractorfacts spans for the same fact -- what is left after removing
    both is just the "&" that joined them. Nothing left to explain."""
    return bool(_CONNECTIVE_ONLY_RE.match(remainder))


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

    Phase 2c's own finding: a backed credential exempts only its own
    matched span (`_credential_backed_remainder`), never the rest of the
    sentence it sits in — CLAIM_RE runs on what is left, so "Licensed and
    insured, award-winning and voted best in Plano." still surfaces the
    two invented claims even though "licensed ... insured" is genuinely
    corroborated.
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
            remainder = _credential_backed_remainder(sentence, material_facts)
            for match in CLAIM_RE.finditer(remainder):
                claim = match.group(0)
                if claim.lower() not in seen:
                    seen.add(claim.lower())
                    found.append(claim)
    return found


# Four more shapes found running Step 2's fix against the real
# 19-fixture corpus (documented in .reviews/phase-2b-seam.md's
# "boilerplate list" section) — none of them a model-authored sentence,
# all of them structural output the rendered page carries regardless of
# which business it names:
#
# A run of star glyphs (a rating widget drawn as repeated characters,
# not text) has no claim in it to explain.
_STAR_ONLY_RE = re.compile(r"^[★☆\s]+$")

# A bare 1-2 digit run (a <span class="idx"> carousel/list index sitting
# beside a heading) is a structural position label, not a number CLAIM
# about the business — the same reasoning "24/7" already gets in
# unbacked_numbers, and the round's own worked example (barbecue-rich's
# "03" beside "Turkey Sandwich review") is exactly this shape colliding
# with a DIFFERENT check (the review-count regex) for the same reason.
_STRUCTURAL_INDEX_RE = re.compile(r"^\d{1,2}$")

# A merged call-to-action + directions label ("Find us Get directions") —
# render.py glues a short CTA and a directions label into one run with
# no intervening punctuation for SENTENCE_RE to split on. Checked by
# subtraction (remove every known phrase, nothing survives) rather than
# enumerating every combination, so a CTA this corpus does not happen to
# pair with "directions" is still recognised.
_GENERIC_CTA_PHRASES = (
    "Find us", "Call us", "Book a table", "Book an appointment",
    "Get a free estimate", "Call to order", "Schedule a consultation",
    "Get directions", "Directions",
)


def _is_generic_cta_combo(sentence: str) -> bool:
    remainder = sentence
    for phrase in sorted(_GENERIC_CTA_PHRASES, key=len, reverse=True):
        remainder = remainder.replace(phrase, "")
    return not remainder.strip()


# A review's own author name, printed with its source platform
# ("Jeff Willie · Google") — `material.quotes` carries the bare author
# name only; the " · Google" is render.py's own attribution suffix, not
# part of the sourced text, so a literal own-words check never matches
# the combined string.
_AUTHOR_PLATFORM_RE = re.compile(r"^(.*?)\s*·\s*\S+$")


def _is_quote_author_with_platform(sentence: str, material) -> bool:
    match = _AUTHOR_PLATFORM_RE.match(sentence)
    if not match:
        return False
    name = match.group(1).strip().lower()
    if not name:
        # A review with no stated author renders as just "· Google" --
        # still the same attribution shape, not a claim.
        return True
    return any(str(q.get("author", "")).strip().lower() == name
              for q in material.quotes)


def _is_known_structural_shape(sentence: str, material) -> bool:
    return (bool(_STAR_ONLY_RE.match(sentence))
            or bool(_STRUCTURAL_INDEX_RE.match(sentence))
            or _is_generic_cta_combo(sentence)
            or _is_quote_author_with_platform(sentence, material))


# A footer or stat line combining SEVERAL corroborated fields with
# render.py's own label/connective words ("Address 9225 Preston Rd,
# Frisco, TX 75033, USA Phone (972) 377-2046 Instagram Follow along") —
# every fact-bearing NUMBER in it is unbacked_numbers()'s job,
# unconditionally, so this only ever has to answer for WORDS. That is
# the real difference from Phase 2's removed `_is_all_facts_and_
# boilerplate`: that one exempted the numbers too, silently, which is
# gap 2 — this one only ever looks at [a-z]+ tokens, and a genuine claim
# word ("certified", "award-winning") is neither a glue word here nor
# present in _corroborated_facts, so it still reaches a finding.
_FOOTER_GLUE_WORDS = frozenset({
    "address", "phone", "email", "follow", "along", "get", "directions",
    "instagram", "facebook", "tiktok", "linkedin", "yelp", "twitter", "x",
    # Review/rating connective words. Phase 2's _BOILERPLATE_WORDS
    # included these too and it was a real masking risk THERE, because
    # that mechanism also hid the number beside them (gap 2). Safe here:
    # unbacked_numbers() checks every number in this same text
    # unconditionally, regardless of whether the text passes this check,
    # so "18702" in "18702 Google reviews" is still independently
    # checked against material.reviews even when the WORDS around it are
    # recognised as glue.
    "average", "rating", "stars", "star", "google", "reviews", "review",
    "from", "across",
    "mon", "tue", "wed", "thu", "fri", "sat", "sun",
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    "am", "pm",
    # "N dishes on the menu" / "N services offered" -- the counts
    # themselves are in _corroborated_numbers (len(menu_items)/
    # len(services)), so these connective words are safe the same way.
    "dishes", "menu", "services", "offered", "on", "call",
})
_WORD_RE = re.compile(r"[a-z]+")


def _is_all_facts_and_footer_glue(text: str, material) -> bool:
    facts_words = frozenset(_WORD_RE.findall(_corroborated_facts(material)))
    words = _WORD_RE.findall(text.lower())
    return bool(words) and all(w in _FOOTER_GLUE_WORDS or w in facts_words
                              for w in words)


def unexplained_prose(runs: list[VisibleRun], material) -> list[str]:
    """Port of `provenance.unexplained_sentences()`: every visible
    sentence that is not template chrome (`is_template_chrome` — now
    only nav/label/form and a short `<a>`/`<button>`, Phase 2b's own
    tightened rule), checked the same verbatim-or-prefix-cut way as
    before. Also backed by `_credential_backed_remainder` (the same path
    `unsupported_sentences` uses — a device label like "Manufacturer
    certified" is not itself a literal source sentence, but IS a fact
    genuinely present in the material) and `_is_known_structural_shape`
    (a star-glyph rating, a carousel index, a merged CTA label, a
    review's own author+platform attribution — all real, all
    deterministic renderer output, none of them a sentence to trace to
    a source).

    Phase 2c's own finding: a credential backs only its own matched span,
    same as `unsupported_sentences` — a sentence is exempted here only
    when what is left after removing every backed span is nothing but
    connective glue (`_is_pure_connective_remainder`); a real remaining
    claim keeps the WHOLE original sentence in `found`, since this check
    (unlike CLAIM_RE) reports full sentences, not fragments.
    """
    own = _own(material)
    material_facts = _material_contractor_facts(material)
    found: list[str] = []
    seen: set[str] = set()
    for run in runs:
        if is_template_chrome(run):
            continue
        for sentence in _sentences_of(run):
            if sentence in provenance.GENERIC_COPY:
                continue
            if _is_known_structural_shape(sentence, material):
                continue
            if _is_all_facts_and_footer_glue(sentence, material):
                continue
            bare = _bare(sentence)
            if bare and bare in own:
                continue
            remainder = _credential_backed_remainder(sentence, material_facts)
            if _is_pure_connective_remainder(remainder):
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
        # A rendered phone number is usually punctuated ("(972) 471-5462"),
        # which splits it into separate digit runs for _NUMBER_RE -- the
        # single concatenated string above never matches any of them
        # individually.
        nums.update(_normalize_number(n) for n in _NUMBER_RE.findall(material.phone))
    if material.address:
        # Street number, suite number, zip code -- every digit run in
        # their own real address, the same way phone digits already are.
        nums.update(_normalize_number(n) for n in _NUMBER_RE.findall(material.address))
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
            if _STRUCTURAL_INDEX_RE.match(sentence):
                # A bare 1-2 digit run is a carousel/list position label
                # (<span class="idx">03</span>), not a quantity claim —
                # same reasoning as "24/7" below, and the round's own
                # worked example for why a NUMBER beside unrelated text
                # is not automatically a claim about the business.
                continue
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
            claimed = int(match.group("num").replace(",", ""))
            lower_bound = bool(match.group("bound") or match.group("plus"))
            if (contradiction.contradicts(claimed, material.reviews, lower_bound)
                    and sentence not in seen):
                seen.add(sentence)
                found.append(sentence)
    return found


def gate(runs: list[VisibleRun], material) -> list[str]:
    """The ported `pipeline._gate()`: all four, concatenated."""
    return (unsupported_sentences(runs, material)
            + unexplained_prose(runs, material)
            + unbacked_numbers(runs, material)
            + contradicted_review_counts(runs, material))
