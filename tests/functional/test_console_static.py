"""The FastAPI app serves the Operator Console at / without shadowing /api."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.main import create_app

pytestmark = pytest.mark.functional


def test_root_serves_console_and_api_still_works():
    client = TestClient(create_app())

    # /api routes take precedence over the static mount.
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json() == {"ok": True}

    # Root serves the console shell (index.html).
    root = client.get("/")
    assert root.status_code == 200
    assert "text/html" in root.headers["content-type"]
    assert "x-dc" in root.text  # the console's root element

    # The wired data layer is served as a static asset.
    api_js = client.get("/api.js")
    assert api_js.status_code == 200
    assert "listBusinesses" in api_js.text
    assert 'fetch("/api"' in api_js.text  # it calls the real backend, not the mock
    assert "/pipeline" in api_js.text


def _console_html() -> str:
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    return (root / "console" / "index.html").read_text()


def test_console_template_tags_are_balanced():
    """A stray </sc-if> nests one screen inside another and silently blanks it —
    which is exactly how the help screen broke the first time."""
    import re

    html = _console_html()
    assert len(re.findall(r"<sc-if", html)) == len(re.findall(r"</sc-if>", html))
    assert len(re.findall(r"<sc-for", html)) == len(re.findall(r"</sc-for>", html))


def test_every_screen_is_reachable_from_the_nav():
    html = _console_html()
    for screen in ("isBoard", "isReview", "isApprovals", "isHelp"):
        assert f'value="{{{{ {screen} }}}}"' in html, f"{screen} has no rendered block"


def test_help_screen_explains_the_gates_and_the_send_guard():
    html = _console_html()
    assert "Nothing reaches a real business until you approve it" in html
    assert "Nothing sends yet" in html


def test_claim_verification_is_offered_in_the_console():
    html = _console_html()
    assert "I verified this" in html
    assert "verifyClaim" in (
        __import__("pathlib").Path(__file__).resolve().parents[2]
        / "console" / "api.js"
    ).read_text()
