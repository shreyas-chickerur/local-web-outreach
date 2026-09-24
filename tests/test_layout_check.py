"""The layout check the review runs on every version, against a page built to fail it."""

from __future__ import annotations

import pytest

from app.review import layout

pytestmark = [pytest.mark.layout,
              pytest.mark.skipif(not layout.chrome(), reason="needs Chrome")]

_CAPPED = """<!doctype html><meta name="viewport" content="width=device-width">
<style>body{margin:0;font:20px/1.4 serif} .hero{max-height:200px;background:#222;color:#fff}
.next{background:#eee;padding:20px}</style>
<section class="hero"><h1>Sushi, skewers and a cold drink</h1>
<p>A lively Japanese pub.</p><p>Nigiri and rolls at the sushi bar.</p><p>Small plates.</p>
<p>Open late.</p><p>Call ahead.</p></section>
<section class="next"><h2>Where</h2><p>8600 Preston Rd</p></section>"""


def test_a_section_shorter_than_its_text_is_a_defect_at_every_size_it_happens():
    """Yama's opening section was capped at 900 pixels and its text ran over the
    hours below. The only layout check ran in the test suite, looked for text
    under other text, and never saw it: the spill sat beside the next section's
    words rather than beneath them."""
    found = layout.defects(_CAPPED, {}, 1)
    spills = [f for f in found if f.title.startswith("Text runs past")]
    assert spills and all(f.verdict == "defect" for f in spills)
    assert "past the bottom of hero" in spills[0].detail
    assert layout.summary(found).startswith("Layout: ")


def test_the_same_page_without_the_cap_is_clean():
    assert layout.defects(_CAPPED.replace("max-height:200px;", ""), {}, 1) == []
