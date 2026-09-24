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
    `language_model.available` itself, which overrides this.
    """
    monkeypatch.setattr(config, "anthropic_api_key", lambda: None)
    # The models are named only in `.env`. A test sees stand-in names, so no
    # result depends on which model this machine happens to be set to.
    monkeypatch.setenv("ANTHROPIC_MODEL", "test-model")
    monkeypatch.setenv("DESIGN_MODEL", "test-design-model")


@pytest.fixture(autouse=True)
def no_agent_runs(monkeypatch):
    """No test starts a real design or edit run.

    `no_api_calls` blanks the key inside this process, but the agent kit starts
    its own process, which reads ANTHROPIC_API_KEY from the environment. A test
    whose page counted as designed once went through to a real edit run, billed
    to the project's key. A test that exercises a run replaces `bridge.query`
    with its own, which overrides this.
    """
    from app.design import bridge

    def refuse(*_args, **_kwargs):
        raise AssertionError("a test reached a real, paid agent run; replace bridge.query")

    monkeypatch.setattr(bridge, "query", refuse)


@pytest.fixture(autouse=True)
def business_folders_in_a_temporary_place(monkeypatch, tmp_path):
    """No test writes into the real `sites/` folder.

    Every saved version, crawl, master mark and proposal is also written to the
    business's folder, and the suite saves thousands of versions for businesses
    that do not exist.
    """
    from app.store import folders

    monkeypatch.setattr(folders, "ROOT", tmp_path / "sites")


@pytest.fixture(autouse=True)
def no_photograph_downloads(monkeypatch):
    """Research fetches a lead's photographs from Google as it finishes. With a
    real key in the environment every lookup test would pay for them."""
    from app.web import server

    monkeypatch.setattr(server, "fetch_photo", lambda key, name, width=2400: None)


@pytest.fixture(autouse=True)
def no_layout_measuring(request, monkeypatch):
    """The layout check starts Chrome four times per version. A test that
    measures layout says so with the `layout` marker; the rest see a clean page."""
    if request.node.get_closest_marker("layout"):
        return
    from app.review import layout

    monkeypatch.setattr(layout, "defects", lambda html, brief, lead_id: [])

