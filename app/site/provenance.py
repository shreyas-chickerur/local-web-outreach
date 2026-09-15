"""BRIEF §5: every visible sentence of free prose on the page is one of
exactly three things — a verbatim or prefix-cut span of source material, a
member of a small whitelisted generic-copy library, or a value rendered
from a corroborated field. Nothing else.

A second, separate layer from `app.core.claims`'s `CLAIM_RE` check
(`render.unsupported`) — kept apart deliberately, per BRIEF §5 ("keep the
claim expression as a second layer. Do not fold it in"). That one catches
a specific SHAPE of assertion nothing backs ("since 1994", a credential);
this one checks that every sentence of prose is traceably theirs at all,
whatever shape it takes. The two catch different things and both stay
wired into the same gate.

Scoped to the five spots free, multi-sentence prose from the business
reaches the page — a heading, a button, a stat tile, or a single name or
price is template chrome or a single field value, never "selected
sentences", and is out of scope by construction, not by omission.
"""

from __future__ import annotations

import html
import re

# Small and boring on purpose (BRIEF §5) — nothing in this codebase
# currently authors a prose sentence outside the five sourced spots below,
# so this is empty rather than populated with something invented to look
# used. A real generic phrase belongs here the day one actually ships.
GENERIC_COPY: frozenset[str] = frozenset()

# One pattern per prose spot, keyed to the exact class `render.py` gives
# it. `re.S` so a sentence spanning a line break in the emitted HTML still
# matches; the class list is closed rather than "any <p>", so a button or
# a heading can never be mistaken for prose.
_PROSE_RE = re.compile(
    r'<p class="(?:standfirst|prose(?: dropcap)?|d|accolade-note)"[^>]*>'
    r'(.*?)</p>'
    r'|<figure class="quote(?:-feature)?"[^>]*>.*?<p>&ldquo;(.*?)&rdquo;</p>',
    re.S)

_TAG_RE = re.compile(r"<[^>]+>")
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


def _prose_sentences(page: str) -> list[str]:
    """Every sentence of free prose actually rendered, in the five known
    prose containers only."""
    sentences: list[str] = []
    for m in _PROSE_RE.finditer(page):
        inner = m.group(1) if m.group(1) is not None else m.group(2)
        text = html.unescape(_TAG_RE.sub(" ", inner or "")).strip()
        if not text:
            continue
        sentences.extend(s.strip() for s in SENTENCE_RE.split(text) if s.strip())
    return sentences


def own_words(material) -> str:
    """Every field a sentence of prose could legitimately have come from,
    as one normalised blob for a substring check.

    Widened from `render.unsupported`'s own-words corpus by one field:
    menu item DESCRIPTIONS, not just names. `CLAIM_RE` rarely lands in a
    menu description, so the old check never needed it; a full-sentence
    check does, since `.d` (`_menu`'s per-item description) is one of the
    five prose spots this checks.
    """
    parts = [
        material.tagline or "", material.about or "",
        " ".join(material.services), " ".join(material.products),
        " ".join(str(i.get("name", "")) for i in material.menu_items),
        " ".join(str(i.get("description", "")) for i in material.menu_items),
        " ".join(str(q.get("text", "")) for q in material.quotes),
        " ".join(str(b.get("text", "")) for b in material.blocks),
    ]
    return re.sub(r"\s+", " ", " ".join(parts)).strip().lower()


def unexplained_sentences(page: str, material) -> list[str]:
    """Sentences of rendered prose that are none of: verbatim-or-
    prefix-cut source material, whitelisted generic copy, or (by
    construction elsewhere) a corroborated field value.

    A prefix cut ends in an ellipsis (`_truncate_quote`,
    `trim_to_sentence`) — stripped before the substring check, since the
    ellipsis itself is never in the source text.
    """
    own = own_words(material)
    found: list[str] = []
    seen: set[str] = set()
    for sentence in _prose_sentences(page):
        normalised = re.sub(r"\s+", " ", sentence).strip()
        if normalised in GENERIC_COPY:
            continue
        bare = normalised.rstrip("…").strip().lower()
        if bare and bare in own:
            continue
        if normalised not in seen:
            seen.add(normalised)
            found.append(normalised)
    return found
