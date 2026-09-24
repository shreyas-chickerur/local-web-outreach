"""The crawl's page text, from the fetch to the brief the checks read.

One seam per hop, with nothing hand-made in between: `build_brief`, then
`brief_to_dict`, then the archive and the database exactly as `make brief`
writes them, then the brief with the operator's corrections applied.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.adapters.site_fetch import FetchResult
from app.store import brief_archive, db, leads
from app.web.serialize import brief_to_dict
from app.workbench.brief import build_brief

pytestmark = pytest.mark.unit

_HOME = ('<html><head><title>Home | Craftway Kitchen | Frisco TX</title></head>'
         '<body><p>Call (972) 555-0100.</p><a href="/wine/">Wine</a></body></html>')
_WINE = '<html><body><h2>Wine</h2><p>Cabernet Sauvignon, Napa Valley</p></body></html>'


class _Site:
    def fetch(self, url):
        html = {"https://craftwaykitchen.com/": _HOME,
                "https://craftwaykitchen.com/wine/": _WINE}.get(url)
        return FetchResult(ok=html is not None, status=200 if html else 404,
                           final_url=url, html=html or "", elapsed_ms=5)


def test_the_crawls_page_text_survives_to_the_corrected_brief(tmp_path: Path):
    """If any hop drops `pages`, the checks see a brief with no text of the
    business's own and call every claim unsourced — while the screen says a
    brief loaded. That is how the `current.json` pointer bug shipped."""
    payload = brief_to_dict(build_brief("craftwaykitchen.com", fetcher=_Site()))
    pointer = brief_archive.save(payload, root=tmp_path / "briefs")
    conn = db.connect(tmp_path / "t.db")
    try:
        lead_id = leads.save_brief(conn, payload)
        # A correction on the lead must not take the page text with it.
        leads.verify(conn, lead_id, "phone", "(972) 555-0199")
        corrected = leads.brief_with_overrides(conn, lead_id)
    finally:
        conn.close()

    archived = json.loads(Path(pointer["path"]).read_text())
    for brief in (archived, corrected):
        texts = {p["url"]: p["text"] for p in brief["pages"]}
        assert "Cabernet Sauvignon, Napa Valley" in texts["https://craftwaykitchen.com/wine/"]


def test_the_checks_find_a_crawl_where_make_brief_put_it(tmp_path: Path):
    """The checks once built their own path to the crawls, so moving where
    `make brief` writes would have left them reading a folder nothing wrote,
    reporting every claim unsourced while the screen said a brief loaded."""
    from app.review.run import material
    from app.store import folders

    payload = brief_to_dict(build_brief("craftwaykitchen.com", fetcher=_Site()))
    pointer = brief_archive.save(payload)
    assert Path(pointer["path"]).parent == folders.of(payload["name"]) / "briefs"
    brief, text, _meta = material(payload["name"])
    assert "Cabernet Sauvignon, Napa Valley" in text
