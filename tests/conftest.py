"""Test-wide guards.

The suite must never reach the network. That was true by construction until an
API key became something the code looks for: with one set in the environment,
every pipeline test started calling Anthropic for real and passing only because
the fallback caught it — slower, billable, and behaving differently on a funded
account than on an empty one.
"""

from __future__ import annotations

import pytest

from app.core import config


@pytest.fixture(autouse=True)
def no_image_measuring(monkeypatch):
    """No test reaches out to size an image either.

    `pick_hero` measures every candidate now rather than the first ten, and the
    fixtures use URLs like https://x/1.jpg — so without this the suite spends
    thirty seconds waiting for DNS to fail. A test that cares about size stubs
    `render.measure` or passes its own `size_of`.
    """
    from app.adapters import imageinfo
    from app.site import render

    monkeypatch.setattr(imageinfo, "measure", lambda url, client=None: None)
    monkeypatch.setattr(render, "measure", lambda url: None)
    # `Material.size_of` reads proxied photographs from the bytes on disk, and
    # fetches them from Google when they are not there yet. With a real key in
    # the environment that is a billable call from a unit test.
    monkeypatch.setattr(render, "google_places_api_key", lambda: "")


@pytest.fixture(autouse=True)
def no_api_calls(monkeypatch):
    """No test uses a real key unless it deliberately arranges one.

    A test that wants the model path stubs the transport (respx) or patches
    `claude.available` itself, which overrides this.
    """
    monkeypatch.setattr(config, "anthropic_api_key", lambda: None)
