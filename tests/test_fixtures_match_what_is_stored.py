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


def test_a_fixture_carries_no_lead_id():
    """It would point at whichever business held that id elsewhere, and the
    proxied photographs would be someone else's pictures."""
    for slug, brief in fixtures():
        assert brief.get("lead_id") is None, slug


def test_the_serialiser_does_not_re_cap_below_the_extractors_own_limit():
    """"Thicken the brief" (Cause 4) raised extract.py's own caps on
    services/products/menu_items — found, re-freezing the fixture corpus
    against them, that `published_to_dict` had its OWN, smaller caps
    (8/8/12) that silently threw the extra content away again before a
    fixture or a rendered page ever saw it. The same "two functions have
    to agree about one field" failure this file's own docstring already
    names for `photos`, found a second time for a different field."""
    from app.workbench.extract import _SERVICE_LIMIT

    site = ExtractedSite()
    site.services = [f"Service {i}" for i in range(_SERVICE_LIMIT)]
    site.products = [f"Product {i}" for i in range(_SERVICE_LIMIT)]
    site.menu_items = [{"name": f"Dish {i}"} for i in range(_SERVICE_LIMIT)]
    stored = brief_to_dict(Brief(name="X", location=None, website_url="https://x",
                                 notes=None, published=site))
    pub = stored["published"]
    assert len(pub["services"]) == _SERVICE_LIMIT
    assert len(pub["products"]) == _SERVICE_LIMIT
    assert len(pub["menu_items"]) == _SERVICE_LIMIT


def test_the_serialiser_puts_photographs_where_a_design_reads_them():
    """The bug itself, pinned. Two functions have to agree about one field."""
    site = ExtractedSite()
    site.images = [f"https://x/{n}.jpg" for n in range(3)]
    stored = brief_to_dict(Brief(name="X", location=None, website_url="https://x",
                                 notes=None, published=site))
    assert (stored.get("published") or {}).get("photos") == site.images
