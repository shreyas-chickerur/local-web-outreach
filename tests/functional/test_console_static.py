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
