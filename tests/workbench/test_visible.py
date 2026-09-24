"""Phase 2, Step 2: `app/site/visible.py` — the one extraction function
every gate reads, and the explicit render-or-not decision in front of it.
"""

from __future__ import annotations

import pytest

from app.adapters.chrome_cdp import cdp_session, chrome
from app.workbench.visible import needs_render, render, visible_text_runs

pytestmark = pytest.mark.unit


# --------------------------------- needs_render --------------------------- #

def test_a_page_with_no_script_tag_never_needs_rendering():
    assert needs_render("<html><body><p>Just words.</p></body></html>") is False


def test_a_page_with_any_script_tag_needs_rendering():
    assert needs_render('<html><body><script>x=1</script></body></html>') is True
    assert needs_render('<html><body><SCRIPT>x=1</SCRIPT></body></html>') is True
    assert needs_render('<script src="app.js"></script>') is True


def test_a_bundled_page_is_exactly_the_case_this_exists_for():
    """A bundled page (the round's own locked example) is almost entirely
    <script> — this is the flag that routes a caller to render() instead
    of reading source directly."""
    assert needs_render(
        '<!doctype html><html><body><div id="root"></div>'
        '<script>/* entire app bundled here */ render(...)</script>'
        '</body></html>') is True


# ------------------------------ visible_text_runs -------------------------- #

def test_head_and_title_are_never_visible_text():
    """Found running the ported gates against the real seam fixtures:
    a page's own <title> text was leaking into a run tagged with
    whatever block happened to be open when <body> started, since
    neither <head> nor <title> is a block tag and neither was being
    skipped — the exact "found by using it" class of bug this codebase
    keeps catching."""
    runs = visible_text_runs(
        '<html><head><title>Milestone Plumbing — Plano, TX</title>'
        '<meta name="description" content="also not visible"></head>'
        '<body><p>Real text.</p></body></html>')
    texts = [r.text for r in runs]
    assert texts == ["Real text."]
    assert not any("Milestone Plumbing" in t for t in texts)


def test_script_and_style_contents_are_never_visible_text():
    runs = visible_text_runs(
        '<body><script>var x = "not real content";</script>'
        '<style>.a { content: "also not real"; }</style>'
        '<p>Real text.</p></body>')
    texts = [r.text for r in runs]
    assert texts == ["Real text."]


def test_text_split_across_inline_spans_reads_as_one_run():
    """The exact shape `tests/fixtures/seam/*-foreign.html` uses to split
    a sentence across elements — this must merge back into one run or
    every sentence-level check downstream sees two incomplete fragments."""
    runs = visible_text_runs(
        '<div class="story__copy">'
        '<span>Julien hosted underground dinners for 20 to 100 guests</span>'
        '<span>while living in Paris.</span>'
        '</div>')
    assert len(runs) == 1
    assert runs[0].text == (
        "Julien hosted underground dinners for 20 to 100 guests "
        "while living in Paris.")


def test_a_nested_block_element_starts_its_own_run():
    runs = visible_text_runs(
        '<div class="outer">Outer text.<p>Inner paragraph.</p>More outer.</div>')
    texts = [r.text for r in runs]
    assert "Inner paragraph." in texts
    assert any("Outer text." in t for t in texts)
    assert any("More outer." in t for t in texts)
    # The inner paragraph must not be glued onto the outer div's own text.
    assert not any("Outer text. Inner paragraph." in t for t in texts)


def test_each_run_carries_its_own_tag_and_a_tag_only_path():
    runs = visible_text_runs(
        '<html><body><section><h1>A Heading</h1></section></body></html>')
    heading = next(r for r in runs if r.text == "A Heading")
    assert heading.tag == "h1"
    assert heading.path == "html>body>section>h1"
    # No CSS classes anywhere in the path — a foreign page never shares
    # render.py's own class vocabulary, so the path must not depend on it.
    assert "." not in heading.path
    assert "class" not in heading.path.lower()


def test_a_script_injected_run_is_visible_once_the_caller_hands_in_the_dom():
    """visible_text_runs() itself does not render anything — it reads
    whatever string it is given. Handed a post-script DOM (what render()
    would return), the injected content is visible text like any other,
    which is the whole point: the reader does not care how the content
    got there, only that it is now in the DOM."""
    post_script_dom = (
        '<body><section class="hero"><h1>Real Heading</h1></section>'
        '<p class="award">Named Best Emergency Plumber by the Plano '
        'Chamber of Commerce in 2023.</p></body>')
    runs = visible_text_runs(post_script_dom)
    texts = [r.text for r in runs]
    assert any("Named Best Emergency Plumber" in t for t in texts)


def test_void_elements_do_not_glue_adjacent_words_together():
    runs = visible_text_runs('<p>Line one<br>Line two</p>')
    assert runs[0].text == "Line one Line two"


def test_whitespace_is_normalised_and_empty_runs_are_dropped():
    runs = visible_text_runs('<div>   \n\n  </div><p>  Real   text  \n here.  </p>')
    texts = [r.text for r in runs]
    assert texts == ["Real text here."]


def test_document_order_is_preserved():
    runs = visible_text_runs(
        '<body><p>First.</p><p>Second.</p><p>Third.</p></body>')
    assert [r.text for r in runs] == ["First.", "Second.", "Third."]


def test_the_script_injected_planting_is_absent_from_source_but_flagged_by_needs_render():
    """The other half of the contrast above, read from the real fixture:
    hvac-foreign.html's class-5 planting is genuinely invisible reading
    its own source (visible_text_runs sees the <script> body as code, not
    text — it never runs it), and needs_render() correctly says this page
    cannot be trusted read that way."""
    from pathlib import Path

    html = Path("tests/fixtures/seam/hvac-foreign.html").read_text()
    assert needs_render(html) is True
    runs = visible_text_runs(html)
    assert not any("Best Emergency Plumber" in r.text for r in runs)


def test_reproduces_the_seam_baseline_pages_without_a_browser():
    """Both `-foreign.html` fixtures have no un-scripted content that
    should be invisible, and the control pages have no script at all —
    sanity that this function does not choke on the real corpus it will
    be run against in Step 3."""
    from pathlib import Path

    for name in ("hvac-control.html", "restaurant-casual-control.html"):
        html = Path(f"tests/fixtures/seam/{name}").read_text()
        assert not needs_render(html), name
        runs = visible_text_runs(html)
        assert runs, name


# ------------------------------------ render -------------------------------- #
# This round's own resource rule: one browser process for the whole round,
# reused, single worker. This test is real and gated exactly like the
# other seven in this corpus (tests/adapters/test_chrome_cdp.py,
# test_site_fetch.py, tests/tools/test_perf_census.py,
# tests/test_no_element_collides_with_another.py) — not run separately
# during this round's own development, folded into the one real session
# Step 3/4 open instead, so this round launches Chrome once, not twice.

@pytest.mark.skipif(chrome() is None, reason="no Chrome/Chromium on this machine")
def test_render_returns_the_dom_a_script_produces_not_the_source_that_asked_for_it(tmp_path):
    """The one thing needs_render()/visible_text_runs() cannot prove on
    their own: that render() actually drives a real page through a real
    script and hands back what the DOM became, not what was sent."""
    binary = chrome()
    page = tmp_path / "page.html"
    page.write_text(
        "<html><body><div id='slot'></div>"
        "<script>document.getElementById('slot').textContent"
        " = 'added by script';</script></body></html>")
    with cdp_session(binary, "about:blank", 1440, 900, 1.0, timeout=30.0) as call:
        html = render(call, page.resolve().as_uri(), timeout=30.0)
    assert "added by script" in html
    runs = visible_text_runs(html)
    assert any("added by script" in r.text for r in runs)
