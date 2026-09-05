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
def no_api_calls(monkeypatch):
    """No test uses a real key unless it deliberately arranges one.

    A test that wants the model path stubs the transport (respx) or patches
    `claude.available` itself, which overrides this.
    """
    monkeypatch.setattr(config, "anthropic_api_key", lambda: None)
