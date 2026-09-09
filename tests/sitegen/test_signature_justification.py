"""§2.3: the signature device's justification — one sentence, reaches the
workspace, never the page. `app/site/signature.py` had DEVICES, `available()`,
`render()`, `decorate()` and no justification anywhere; nothing in `app/web/`
surfaced one either. This is the missing half.
"""

from __future__ import annotations

import pytest

from app.adapters import claude
from app.site import opening, pipeline
from app.store import db, leads, sites

pytestmark = pytest.mark.unit

BRIEF = {
    "name": "The Heritage Table",
    "trade": "Restaurant",
    "facts": [{"field": "phone", "value": "(469) 664-0100",
               "confidence": "verified"}],
    "published": {"tagline": "A neighbourhood restaurant.",
                  "photos": [f"https://x/{n}.jpg" for n in range(1, 5)],
                  "services": ["Dinner"], "hours": ["Mon-Sat 5pm-9pm"],
                  "menu_items": [], "blocks": [], "products": [],
                  "socials": [], "emails": [], "menu_media": []},
    "ratings": [{"source": "google", "value": 4.6, "reviews": 676}],
    # So `quote` is actually AVAILABLE — `signature.available()` requires
    # `m.quotes`, and a thinner brief would silently fall the answer back to
    # `none` regardless of what the model chose, which is the right behaviour
    # for that brief and the wrong fixture for THIS test.
    "testimonials": [{"text": "The best table in the neighbourhood.",
                      "rating": 5, "author": "A regular"}],
}

ANSWER = {
    "mood": "refined", "accent": "burgundy", "cta": "book",
    "first_screen": "photo", "type_treatment": "quiet",
    "architecture": "stacked", "signature": "quote",
    "signature_why": "One named diner's own account is more convincing than "
                    "anything the restaurant could say about itself.",
    "rationale": "A neighbourhood spot that leans on its regulars.",
}


@pytest.fixture
def conn():
    with db.session(":memory:") as connection:
        yield connection


@pytest.fixture
def lead(conn):
    return leads.save_brief(conn, BRIEF)


@pytest.fixture
def answered(monkeypatch):
    monkeypatch.setattr(claude, "available", lambda: True)
    monkeypatch.setattr(opening.claude, "structured", lambda *a, **kw: dict(ANSWER))
    monkeypatch.setattr(pipeline.vision, "look", lambda urls, names: {
        url: {"subject": "dish", "quality": 4, "is_hero_candidate": True,
              "alt_text": "A plate of food"} for url in urls})


def test_the_justification_is_recorded_and_read_back_on_replay(conn, lead, answered):
    """Persisted with the rest of the plan — a rebuild reads it back rather
    than asking again, the same replay guarantee `rationale` already has."""
    pipeline.open_site(conn, lead)
    stored = sites.recall_stage(conn, lead, "direction") or {}
    assert stored.get("config", {}).get("signature_why") == ANSWER["signature_why"]

    notes = sites.versions(conn, lead)[0].get("notes") or {}
    assert notes.get("signature") == "quote"
    assert notes.get("signature_why") == ANSWER["signature_why"]


def test_the_justification_never_reaches_the_rendered_page(conn, lead, answered):
    """The same boundary `rationale` already keeps: model prose about the
    business reaches the workspace and never the HTML `render` produces."""
    pipeline.open_site(conn, lead)
    version = sites.versions(conn, lead)[0]["version"]
    html = sites.html_for(conn, lead, version)
    assert ANSWER["signature_why"] not in html
