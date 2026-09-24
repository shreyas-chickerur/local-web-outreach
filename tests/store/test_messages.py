"""The workspace conversation, and the boundary it exists to draw.

Model prose is allowed in a message to the operator and forbidden on a
generated page. The rule is enforced by where the data can go rather than by
remembering it, which is the only way a rule like this survives.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from app.store import db, leads, messages

pytestmark = pytest.mark.unit

BRIEF = {"name": "The Heritage Table", "facts": [], "published": {}}


@pytest.fixture
def conn():
    with db.session(":memory:") as connection:
        yield connection


@pytest.fixture
def lead(conn):
    return leads.save_brief(conn, BRIEF)


def test_a_thread_keeps_the_order_it_was_said_in(conn, lead):
    messages.add(conn, lead, "assistant", "Opened warm, led with the gallery.",
                 version=1)
    messages.add(conn, lead, "user", "make it darker")
    messages.add(conn, lead, "assistant", "Done — v2 is night.", version=2)
    said = messages.thread(conn, lead)
    assert [m["role"] for m in said] == ["assistant", "user", "assistant"]
    assert [m["version"] for m in said] == [1, None, 2]


def test_a_turn_that_produced_no_version_says_so(conn, lead):
    """A rejected instruction and a question back both produced none."""
    messages.add(conn, lead, "assistant", "Which part looks cramped?")
    assert messages.thread(conn, lead)[0]["version"] is None


def test_an_unknown_role_is_refused(conn, lead):
    with pytest.raises(ValueError):
        messages.add(conn, lead, "system", "you are a helpful assistant")


def test_an_empty_message_records_nothing(conn, lead):
    with pytest.raises(ValueError):
        messages.add(conn, lead, "assistant", "   ")


def test_the_thread_knows_whether_it_has_been_opened(conn, lead):
    assert messages.opened(conn, lead) is False
    messages.add(conn, lead, "assistant", "Opened refined, charcoal.")
    assert messages.opened(conn, lead) is True


# --- the boundary --------------------------------------------------------- #

def test_what_builds_pages_cannot_reach_the_conversation():
    """The structural half of the rule. Model prose is allowed in a message and
    forbidden on a page, and the way that survives is that nothing which writes
    a page has a path to this table at all, not that someone remembers. Pages
    are written by `app/design` now; the older generator held this rule before.
    """
    offenders = []
    for path in Path("app/design").glob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                names = {alias.name for alias in node.names}
                if (node.module == "app.store" and "messages" in names) \
                        or node.module == "app.store.messages":
                    offenders.append(path.name)
            elif isinstance(node, ast.Import):
                offenders += [path.name for alias in node.names
                              if alias.name == "app.store.messages"]
    assert list(Path("app/design").glob("*.py")), "app/design moved; point this test at it"
    assert offenders == [], offenders
