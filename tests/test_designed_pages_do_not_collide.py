"""Pages designed by Claude Design, held to the same layout probe.

The committed fixtures are real pages from Claude Design runs (three home
services businesses, first pass and revision, and one exported design). A page
the design bridge writes has the same shape: free-form markup, its own fixed
chrome, photographs placed as the design chose.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from layout_probe import WIDTHS, chrome, measure

pytestmark = pytest.mark.unit

DESIGNED = sorted(Path("tests/fixtures/design").glob("*.html")) + [
    Path("tests/fixtures/seam/hvac-claude-design.html")]


@pytest.mark.skipif(chrome() is None, reason="needs a real Chrome")
@pytest.mark.parametrize("page", DESIGNED, ids=lambda p: p.stem)
def test_no_text_on_a_designed_page_is_clipped_or_covered(page):
    """A photograph or button painted over a line of text is invisible in a
    code review and obvious to an owner opening the page on a phone."""
    offenders = {label: found for label, width, height in WIDTHS
                 if any((found := measure(page.resolve(), width, height)).values())}
    assert not offenders, offenders


@pytest.mark.skipif(chrome() is None, reason="needs a real Chrome")
def test_the_probe_catches_a_photograph_over_the_end_of_a_line(tmp_path):
    """Fish Shack's version 5 shipped with its shrimp polaroid covering the ends
    of the description's lines, and a probe that read only each line's centre
    passed it. This is that fault, reduced to one paragraph and one image."""
    page = tmp_path / "polaroid.html"
    page.write_text("""<!doctype html><html><body style="margin:0;font:18px sans-serif">
      <p id="lede" style="width:600px;margin:40px">Fish Shack is a casual grill and
      oyster bar on East 15th Street: shrimp boiled hot by the pound.</p>
      <div style="position:absolute;left:560px;top:30px;width:200px;height:120px;
      background:#fff;border:8px solid #eee"></div></body></html>""")
    assert measure(page, 1440, 900)["collided"]
