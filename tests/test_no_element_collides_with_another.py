"""BRIEF §5, Phase 2 (`.reviews/<phase>.md`): a mechanical check for the
class of defect a sampled Slice G design review found and no test here
could — a control clipped by the viewport edge, or one element's text
painted over by another's, at any of the three review widths.

Runs the real rendered corpus through a live Chrome at genuine viewports
(`tests/layout_probe.py`) and reads element geometry directly, rather than
reading it back off a screenshot a vision model has to interpret. The pages
are the old generator's, which the workbench's build button still makes;
`test_designed_pages_do_not_collide.py` holds pages from the design tool to
the same probe.

Two checks:

1. CLIPPED — an interactive control (a link or button) with visible text
   whose bounding box extends past the viewport's left or right edge. This
   is the exact shape of the "duplicated CTA cropped at the mobile edge"
   finding — which turned out not to be a page defect at all (a genuine
   390px viewport shows it fine; the design review's own screenshot tool
   silently rendered at ~500px and cropped the output to 390px, see
   `tools.contact_sheet.CDP_MIN_WIDTH`) — but a real version of the same
   shape exists independently: `.hero.first-proof .proof`'s three-column
   grid has a genuine 570px minimum, wider than any phone, and grew the
   whole hero to match rather than wrapping, clipping the second action
   button. Fixed in `app/site/styles.py` (`.hero .wrap{min-width:0}`);
   this is the standing guard against it recurring in any shape.

2. COVERED — an element carrying its own direct text whose centre point,
   read with `elementFromPoint`, resolves to a DIFFERENT element that is
   neither its ancestor nor its descendant — i.e. something else is
   painted on top of its text. `position:fixed` chrome (the sticky nav,
   the mobile call bar, the scroll-progress hairline) is excluded: floating
   above whatever is scrolled beneath it is what "fixed" means, not a
   collision, and every fixture legitimately has one.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from layout_probe import WIDTHS, chrome, link_photographs, measure

FIXTURES = Path("tests/fixtures/briefs")
OUT = Path("artifacts/layout-probe")

pytestmark = pytest.mark.unit


@pytest.mark.skipif(chrome() is None, reason="no Chrome/Chromium on this machine")
def test_no_control_is_clipped_and_no_text_is_covered_at_any_review_width():
    from app.site.pipeline import STAGES, run_stage, spec_from_config
    from app.site.render import build_from_spec
    from app.store import db, leads, sites

    OUT.mkdir(parents=True, exist_ok=True)
    offenders: dict[str, dict[str, list[str]]] = {}
    with db.session(":memory:") as conn:
        for path in sorted(FIXTURES.glob("*.json")):
            slug = path.stem
            lead_id = leads.save_brief(conn, json.loads(path.read_text()))
            for stage in STAGES:
                run_stage(conn, lead_id, stage)
            brief = leads.brief_with_overrides(conn, lead_id)
            stored = sites.recall_stage(conn, lead_id, "direction") or {}
            config = dict(stored.get("config") or {})
            assert config.get("read_by") == "frozen", (
                f"{slug} did not replay a frozen direction")
            spec = spec_from_config(config)
            page = build_from_spec(brief, spec)
            site_file = OUT / f"{slug}.html"
            site_file.write_text(link_photographs(page, brief, OUT))

            for label, width, height in WIDTHS:
                result = measure(site_file, width, height)
                if result["clipped"] or result["collided"]:
                    offenders[f"{slug}:{label}"] = result

    assert not offenders, (
        f"an element is clipped by the viewport or painted over at these "
        f"(fixture, width) combinations: {json.dumps(offenders, indent=2)}")
