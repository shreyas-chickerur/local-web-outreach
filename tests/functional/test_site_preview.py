"""The generated site must be a real, viewable page — not just a content model."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.main import create_app, get_session
from app.render.site_html import render_site

pytestmark = pytest.mark.functional


@pytest.fixture
def client(session):
    app = create_app()

    def _override():
        yield session

    app.dependency_overrides[get_session] = _override
    return TestClient(app)


def test_preview_serves_the_generated_site(client, session, make_site_drafted):
    from app.models.website import Website

    biz, _ = make_site_drafted(name="The Heritage Table")
    site = session.query(Website).filter_by(business_id=biz.id).one()

    res = client.get(f"/preview/{site.preview_token}")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    assert "The Heritage Table" in res.text
    # a private proposal: never indexable, and visibly a draft
    assert res.headers["X-Robots-Tag"] == "noindex, nofollow"
    assert 'content="noindex, nofollow"' in res.text
    assert "Draft proposal" in res.text


def test_unknown_preview_token_is_404(client):
    assert client.get("/preview/nope").status_code == 404


def test_preview_url_points_at_the_real_route(session, make_site_drafted):
    """It used to point at preview-<token>.lwo.example, a domain that does not
    exist — so nobody could ever see the site they were approving."""
    from app.models.website import Website

    biz, _ = make_site_drafted()
    site = session.query(Website).filter_by(business_id=biz.id).one()
    assert "lwo.example" not in site.preview_url
    assert site.preview_url.endswith(f"/preview/{site.preview_token}")


# ------------------------------ renderer ---------------------------------- #
def test_renderer_escapes_third_party_values():
    """Every value comes from third-party data; none of it may become markup."""
    html = render_site({
        "business_name": "<script>alert(1)</script>",
        "industry": "restaurant",
        "sections": [{"type": "hero", "heading": "x", "subheading": "y"}],
    })
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_renderer_shows_only_what_the_model_contains():
    html = render_site({
        "business_name": "Acme", "industry": "service",
        "sections": [
            {"type": "hero", "heading": "Acme", "subheading": "Frisco, TX"},
            {"type": "contact", "heading": "Contact",
             "facts": [{"label": "Phone", "field": "phone", "value": "(972) 555-0148"}]},
        ],
    })
    assert "(972) 555-0148" in html
    assert "Contact" in html
    assert "Hours" not in html  # never invents a section


def test_rating_renders_as_stars():
    html = render_site({
        "business_name": "Acme", "industry": "restaurant",
        "sections": [
            {"type": "hero", "heading": "Acme", "subheading": ""},
            {"type": "standing", "heading": "Rated by customers",
             "facts": [{"label": "Rating", "field": "rating", "value": "4.6"}]},
        ],
    })
    assert "★★★★" in html
    assert "4.6" in html


def test_approved_site_drops_the_draft_ribbon():
    content = {"business_name": "Acme", "industry": "service",
               "sections": [{"type": "hero", "heading": "Acme", "subheading": ""}]}
    assert "Draft proposal" in render_site(content, draft=True)
    assert "Draft proposal" not in render_site(content, draft=False)
