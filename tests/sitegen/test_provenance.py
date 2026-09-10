"""BRIEF §5: every visible sentence of free prose is a verbatim-or-
prefix-cut span of source material, a whitelisted generic phrase, or a
corroborated field value. Nothing else. A second, separate layer from
`app.core.claims`'s `CLAIM_RE` check — see `app.site.provenance`'s own
docstring for why they are not folded into one.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.site.provenance import unexplained_sentences

pytestmark = pytest.mark.unit


class _Material:
    """The handful of fields `unexplained_sentences` reads — not the real
    `Material` dataclass, so this test does not depend on its full shape."""

    def __init__(self, **kw):
        self.tagline = kw.get("tagline")
        self.about = kw.get("about")
        self.services = kw.get("services", ())
        self.products = kw.get("products", ())
        self.menu_items = kw.get("menu_items", ())
        self.quotes = kw.get("quotes", ())
        self.blocks = kw.get("blocks", ())


def test_a_verbatim_sentence_of_their_own_about_text_is_explained():
    material = _Material(about="A neighbourhood restaurant serving dinner "
                                "nightly since we opened our doors.")
    page = ('<section id="about"><p class="standfirst">A neighbourhood '
            'restaurant serving dinner nightly since we opened our '
            'doors.</p></section>')
    assert unexplained_sentences(page, material) == []


def test_a_prefix_cut_sentence_is_explained():
    """`trim_to_sentence`/`_truncate_quote` end a shortened sentence in an
    ellipsis — stripped before the check, since it is never in the source."""
    material = _Material(quotes=[{"text": "Everything was amazing, from "
                                          "the food to the service to the "
                                          "prices, and we will be back."}])
    # Cut at a word boundary with a plain ellipsis, the same shape
    # `_truncate_quote` actually produces.
    page = ('<figure class="quote"><p>&ldquo;Everything was amazing, from '
            'the food to the service…&rdquo;</p></figure>')
    assert unexplained_sentences(page, material) == []


def test_a_fabricated_sentence_is_not_explained():
    """The failure this exists to catch: a sentence nothing in the
    material backs, however plausible it reads."""
    material = _Material(about="A neighbourhood restaurant serving dinner "
                                "nightly.")
    page = ('<section id="about"><p class="prose">Family owned and '
            'operated since 1994, we pride ourselves on quality.</p>'
            '</section>')
    found = unexplained_sentences(page, material)
    assert found == ["Family owned and operated since 1994, we pride "
                     "ourselves on quality."]


def test_a_menu_item_description_is_explained():
    """Widened from `render.unsupported`'s own-words corpus, which only
    ever needed menu item NAMES — a full-sentence check also needs
    descriptions, since `.d` is one of the five prose spots this checks."""
    material = _Material(menu_items=[
        {"name": "Short Rib", "description": "Braised eight hours, "
         "finished on the grill."}])
    page = ('<li><span class="n">Short Rib</span>'
            '<p class="d">Braised eight hours, finished on the grill.</p>'
            '</li>')
    assert unexplained_sentences(page, material) == []


def test_headings_and_labels_are_never_checked():
    """Template chrome — a heading, a button, a stat label — is not
    "selected sentences" at all, and is out of scope by construction."""
    material = _Material()
    page = ('<h2>What we do</h2><button class="cta">Call now</button>'
            '<span>4.9 stars from 200 reviews</span>')
    assert unexplained_sentences(page, material) == []


def test_no_fixture_in_the_corpus_ships_unexplained_prose():
    from app.site.pipeline import STAGES, run_stage, spec_from_config
    from app.site.render import build_from_spec, material_from_brief
    from app.store import db, leads, sites

    offenders: dict[str, list[str]] = {}
    with db.session(":memory:") as conn:
        for path in sorted(Path("tests/fixtures/briefs").glob("*.json")):
            slug = path.stem
            lead_id = leads.save_brief(conn, json.loads(path.read_text()))
            for stage in STAGES:
                run_stage(conn, lead_id, stage)
            brief = leads.brief_with_overrides(conn, lead_id)
            stored = sites.recall_stage(conn, lead_id, "direction") or {}
            config = dict(stored.get("config") or {})
            assert config.get("read_by") == "frozen", (
                f"{slug} did not replay a frozen direction")
            spec = spec_from_config(config)
            page = build_from_spec(brief, spec)
            material = material_from_brief(brief)
            found = unexplained_sentences(page, material)
            if found:
                offenders[slug] = found

    assert not offenders, (
        f"these fixtures ship prose with no traceable source: {offenders}")
