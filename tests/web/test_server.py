"""The UI layer: serialization and routing.

The page is only trustworthy if it shows what the brief actually established,
so these tests pin the two ways that can go wrong — a conflict rendered as
though it were a fact, and a failing lookup blanking the screen.
"""

from __future__ import annotations

import json

import pytest

from app.web import server
from app.web.serialize import brief_to_dict
from app.workbench.brief import Brief
from app.workbench.corroborate import Fact
from app.workbench.types import Confidence

pytestmark = pytest.mark.unit


def _brief(**kw) -> Brief:
    base = {"name": "Test Co", "location": "Frisco, TX",
            "website_url": None, "notes": None}
    return Brief(**{**base, **kw})


def test_a_conflict_carries_its_candidates_not_a_winner():
    """The UI must be able to name each source; a conflict has no single value."""
    conflict = Fact(field="address", value="A | B", confidence=Confidence.CONFLICT,
                    score=0.3, corroborations=2, sources=[],
                    candidates=[{"value": "A", "source_type": "google",
                                 "source_url": "https://g"},
                                {"value": "B", "source_type": "yelp",
                                 "source_url": "https://y"}])
    payload = brief_to_dict(_brief(facts=[conflict]))
    assert payload["facts"][0]["confidence"] == "conflict"
    assert [c["source_type"] for c in payload["facts"][0]["candidates"]] == [
        "google", "yelp"]
    # A conflicting address must not be promoted into the header.
    assert payload["location"] == "Frisco, TX"


def test_an_established_address_becomes_the_header():
    verified = Fact(field="address", value="2770 Main St, Frisco, TX",
                    confidence=Confidence.VERIFIED, score=0.9, corroborations=2,
                    sources=[{"source_type": "google", "source_url": "https://g"}])
    assert brief_to_dict(_brief(facts=[verified]))["location"] == (
        "2770 Main St, Frisco, TX")


def test_blank_query_is_a_message_not_a_traceback():
    assert "error" in server.lookup("   ", None, None)


def test_a_failing_source_does_not_blank_the_page(monkeypatch):
    """A directory being down should read as an error, not an empty screen."""
    def boom(*a, **k):
        raise RuntimeError("yelp timed out")
    monkeypatch.setattr(server, "build_brief", boom)
    result = server.lookup("Hutchins BBQ", None, None)
    assert "yelp timed out" in result["error"]


def test_routes(monkeypatch):
    monkeypatch.setattr(server, "lookup", lambda *a: {"name": "Test Co"})
    assert json.loads(json.dumps(server.lookup("x", None, None)))["name"] == "Test Co"
    assert (server._UI).exists()


def test_the_pages_script_parses():
    """An unbalanced paren in the page silently killed every bit of its
    behaviour: no examples, no results, and no console error to find it by.
    The page has no build step, so nothing else would catch it."""
    import shutil
    import subprocess
    import tempfile

    node = shutil.which("node")
    if node is None:
        pytest.skip("node not installed")
    html = server._UI.read_text()
    script = html.split("<script>", 1)[1].rsplit("</script>", 1)[0]
    with tempfile.NamedTemporaryFile("w", suffix=".mjs", delete=False) as fh:
        fh.write(script)
        path = fh.name
    done = subprocess.run([node, "--check", path], capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
