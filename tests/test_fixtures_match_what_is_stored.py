"""The fixtures must be the shape the product actually stores.

They were not. `tools/make_fixtures.py` dumped the `Brief` dataclass, and the
server stores a lead through `brief_to_dict` — which is not a straight dump: it
maps the extractor's `images` onto `published.photos`, the field the renderer
reads. So every fixture carried zero of the business's own photographs, and the
whole corpus was measuring a path the product does not have.

That is the same failure as the dead `rank_for_hero`: a second definition of
something, green against a path production never runs.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.site.render import material_from_brief
from app.web.serialize import brief_to_dict
from app.workbench.brief import Brief
from app.workbench.extract import ExtractedSite

FIXTURES = Path("tests/fixtures/briefs")
pytestmark = pytest.mark.unit


def fixtures() -> list[tuple[str, dict]]:
    return [(p.stem, json.loads(p.read_text()))
            for p in sorted(FIXTURES.glob("*.json"))]


def test_the_corpus_exists_and_covers_the_shapes_that_matter():
    names = {slug for slug, _ in fixtures()}
    assert len(names) >= 8, "the corpus is the basis of every metric"
    briefs = dict(fixtures())
    assert any(not b.get("website_url") for b in briefs.values()), \
        "no fixture without a website — the highest-scoring prospect there is"
    assert any(not b.get("website_url")
               and "plumb" in str(b.get("trade", "")).lower()
               for b in briefs.values()), \
        "no contractor without a website — the shape the operator walks into"


def test_a_business_with_its_own_photographs_is_in_the_corpus():
    """Google's photographs come first in the pool, so a corpus where nobody
    has their own can never catch a regression in how the site's own pictures
    are ranked."""
    with_own = [slug for slug, brief in fixtures()
                if (brief.get("published") or {}).get("photos")]
    assert with_own, "no fixture carries the business's own photographs"
    assert len(with_own) >= 3, with_own


def test_every_fixture_is_readable_as_material():
    for slug, brief in fixtures():
        # A fixture carries no lead id — proxied photo URLs are built from one,
        # and a frozen id would point at whichever business happened to hold it
        # in somebody else's database. The tools assign one when they load it.
        material = material_from_brief({**brief, "lead_id": 1})
        assert material.name, slug
        # Both pools reach the renderer: proxied Google photographs and, after
        # them, whatever the business publishes itself.
        assert len(material.images) == (
            len(brief.get("place_photos") or [])
            + len((brief.get("published") or {}).get("photos") or [])), slug


def test_a_fixture_carries_no_lead_id():
    """It would point at whichever business held that id elsewhere, and the
    proxied photographs would be someone else's pictures."""
    for slug, brief in fixtures():
        assert brief.get("lead_id") is None, slug


def test_the_serialiser_puts_photographs_where_the_renderer_reads_them():
    """The bug itself, pinned. Two functions have to agree about one field."""
    site = ExtractedSite()
    site.images = [f"https://x/{n}.jpg" for n in range(3)]
    stored = brief_to_dict(Brief(name="X", location=None, website_url="https://x",
                                 notes=None, published=site))
    assert (stored.get("published") or {}).get("photos") == site.images
    material = material_from_brief({**stored, "lead_id": 1})
    for url in site.images:
        assert url in material.images


def test_every_fixture_carries_what_the_vision_pass_saw():
    """Without this a census depends on `artifacts/fixtures.db`, which is not
    committed — so a clean clone measures a different system, `hero_subject` is
    constant, and the fingerprints move. The ruler was versioned and its inputs
    were not, which makes the versioning worth less than it looks."""
    for slug, brief in fixtures():
        # Read through Material, which re-keys proxied photographs onto the
        # lead they are loaded under — the URLs carry the id, so the raw
        # fixture keys never match.
        material = material_from_brief({**brief, "lead_id": 1})
        if not material.images:
            continue
        assert material.photo_vision, f"{slug} carries no vision labels"
        missing = [url for url in material.images
                   if url not in material.photo_vision]
        assert not missing, f"{slug}: {len(missing)} photographs unaccounted for"


def test_a_fixture_is_enough_on_its_own_to_score_a_hero():
    """The specific thing the missing labels hid: with no vision in the brief,
    every candidate scores the same and the sweep cannot tell axes apart."""
    from app.site.render import hero_scores

    subjects = set()
    for slug, brief in fixtures():
        loaded = {**brief, "lead_id": 1}
        material = material_from_brief(loaded)
        if not material.images:
            continue
        scored = hero_scores(material.images, material.photo_labels,
                             material.trade_kind, lambda url: None,
                             material.photo_vision)
        assert len({s.total for s in scored}) > 1 or len(scored) == 1, slug
        subjects.add(scored[0].label)
    assert len(subjects) > 1, \
        "every fixture's hero has the same subject — the corpus cannot vary"
