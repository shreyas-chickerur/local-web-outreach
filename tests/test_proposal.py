"""A proposal an owner can open before anything is hosted."""

from __future__ import annotations

import pytest

from app.design import proposal
from app.store import db, leads, sites

pytestmark = pytest.mark.unit


@pytest.fixture()
def lead(tmp_path, monkeypatch):
    conn = db.connect(tmp_path / "t.db")
    lead_id = leads.save_brief(conn, {
        "name": "Fish Shack", "location": "Plano, TX", "website_url": "http://fish.test/",
        "facts": [], "published": {"logo": "http://fish.test/fslogo2.jpg"},
        "assumptions": [], "open_questions": [], "sources_consulted": [],
        "place_photos": ["places/x/photos/a", "places/x/photos/b"]})
    sites.save(conn, lead_id, "<p>old</p>", spec="")
    sites.save(conn, lead_id, (
        f'<link rel="icon" href="/logo/{lead_id}"><img src="/logo/{lead_id}">'
        f'<img src="/photo/{lead_id}/1?w=1600" width="1600" height="1200">'
        f'<meta property="og:image" content="/photo/{lead_id}/0?w=1600">'), spec="")
    monkeypatch.setattr(proposal.photos, "fetch",
                        lambda key, name, width=1600: b"\xff\xd8" + name.encode())
    monkeypatch.setattr(proposal.logos, "fetch", lambda url: (b"\xff\xd8logo", "image/jpeg"))
    yield conn, lead_id
    conn.close()


def test_a_proposal_is_one_file_with_nothing_it_has_to_fetch_from_us(lead):
    """Shreyas proposes before paying for hosting. The workbench's /photo/ and
    /logo/ addresses exist only on his machine; a proposal naming them shows an
    owner broken images. Every one is carried inside the file."""
    conn, lead_id = lead
    path = proposal.export(conn, lead_id)
    page = path.read_text()
    assert path == proposal.folders.of("Fish Shack") / "proposals" / "v2.html"
    assert f"/photo/{lead_id}/" not in page and f"/logo/{lead_id}" not in page
    assert page.count("data:image/jpeg;base64,") == 4


def test_a_proposal_never_carries_the_review_layer(lead):
    """A review link shows every doubt the system has about the business. A
    proposal is the thing most likely to be forwarded."""
    conn, lead_id = lead
    page = proposal.export(conn, lead_id).read_text()
    assert "annotate.js" not in page and "?review=" not in page
