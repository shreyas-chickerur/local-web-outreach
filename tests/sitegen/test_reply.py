"""Slice H item 2b/2c: the reply to one instruction.

The binding claim this file exists to hold: the reply builder cannot see
the rendered page (structurally, not by convention), and an unmet
instruction produces a question rather than a silent no-op.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

from app.site.pipeline import IterationResult
from app.site.reply import reply_for

pytestmark = pytest.mark.unit


# --- the structural half of the binding claim ------------------------------ #

def test_reply_for_takes_no_page_and_could_not_be_handed_one():
    """The signature IS the proof. `reply_for` accepts exactly one
    parameter, typed `IterationResult` — there is no `html`/`page`
    parameter for a caller to pass one into, even by mistake."""
    params = inspect.signature(reply_for).parameters
    assert list(params) == ["result"]
    assert params["result"].annotation in (IterationResult, "IterationResult")


def test_iteration_result_itself_carries_no_rendered_html():
    """The second half of the same proof: even if `reply_for` accepted
    more, there is nowhere on `IterationResult` a page could ride in on."""
    import dataclasses
    field_names = {f.name for f in dataclasses.fields(IterationResult)}
    for suspect in ("html", "page", "rendered", "markup"):
        assert suspect not in field_names, (
            f"IterationResult grew a {suspect!r} field — reply_for could "
            f"see rendered output through it")


def test_reply_py_never_imports_the_renderer():
    """Belt and suspenders on the same claim: a static scan, not trust that
    nobody adds `from app.site.render import ...` later. Mirrors
    tests/store/test_messages.py's own AST technique for the messages
    boundary, applied here to the opposite direction of the same rule —
    prose is allowed to describe a page, never to be built from one."""
    source = Path("app/site/reply.py").read_text()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            assert "render" not in node.module, (
                f"reply.py imports from {node.module!r}")
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert "render" not in alias.name, (
                    f"reply.py imports {alias.name!r}")


# --- the behavioural half: a defect becomes a question --------------------- #

def _result(**kw) -> IterationResult:
    return IterationResult(lead_id=1, spec={}, **kw)


def test_an_unreachable_model_is_disclosed_not_hidden():
    text = reply_for(_result(reader_error="timeout", version=1,
                             changed=["mood: 'quiet' -> 'warm'"]))
    assert "couldn't reach the model" in text
    assert "timeout" in text


def test_a_rejection_reports_what_it_would_have_shipped():
    text = reply_for(_result(rejected=True,
                             findings=["an unverified phone number"]))
    assert "couldn't make that change" in text
    assert "unverified phone number" in text


def test_unmet_becomes_a_question_not_a_silent_no_op():
    text = reply_for(_result(
        version=2, changed=["mood: 'quiet' -> 'warm'"],
        unmet=["no menu section: no menu items available"]))
    assert text.rstrip().endswith("?")
    assert "no menu items available" in text


def test_contradictions_and_ignored_tokens_both_surface_in_the_question():
    text = reply_for(_result(
        contradictions=["warmer and also more serious"],
        ignored_tokens=["thingamajig"]))
    assert "warmer and also more serious" in text
    assert "thingamajig" in text
    assert text.rstrip().endswith("?")


def test_a_clean_edit_says_what_changed_grounded_in_the_result():
    text = reply_for(_result(
        version=3, changed=["mood: 'quiet' -> 'warm'"]))
    assert "warm" in text
    assert "?" not in text


def test_an_unchanged_instruction_says_so_plainly():
    text = reply_for(_result(unchanged=True, kind="style"))
    assert "already how it looks" in text


def test_a_blast_radius_is_disclosed_as_unasked_for():
    text = reply_for(_result(
        version=4, changed=["mood: 'quiet' -> 'warm'", "accent: 'navy' -> 'gold'"],
        blast_radius=["accent"]))
    assert "didn't ask for" in text
    assert "accent" in text


def test_a_non_style_kind_never_gets_the_style_reply_shape():
    """A bug report answered by restyling the page is the exact misread
    BRIEF §5 already named once; the reply for one must not look like an
    edit confirmation."""
    text = reply_for(_result(
        kind="defect", unchanged=True, defect="the nav overlaps the photo",
        defects=["nav sits on top of the hero image with no scrim"]))
    assert "nav sits on top of the hero image" in text
    assert "Done —" not in text


def test_unsupported_is_disclosed_as_queued_not_dropped():
    text = reply_for(_result(
        kind="defect", unchanged=True, unsupported=["a live chat widget"]))
    assert "a live chat widget" in text
    assert "queued" in text or "outside what" in text
