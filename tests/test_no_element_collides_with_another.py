"""BRIEF §5, Phase 2 (`.reviews/<phase>.md`): a mechanical check for the
class of defect a sampled Slice G design review found and no test here
could — a control clipped by the viewport edge, or one element's text
painted over by another's, at any of the three review widths.

Runs the real rendered corpus through a live, CDP-driven Chrome (see
`tools.contact_sheet.evaluate_in_page` — genuine narrow viewports, not the
`--screenshot` CLI flag's ~500px floor) and reads element geometry
directly, rather than reading it back off a screenshot a vision model has
to interpret.

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

import pytest

from tools.contact_sheet import FIXTURES, OUT, _link_photographs, chrome
from tools.contact_sheet import evaluate_in_page as _evaluate

pytestmark = pytest.mark.unit

# (label, width, height) — matching the three widths a Slice G design
# review judges (`tools/design_review.py`'s own `WIDTHS`), so this test
# holds the corpus to the same viewports a review is read against.
WIDTHS = (("desktop", 1440, 1100), ("mobile", 390, 844), ("page", 1440, 6000))

_PROBE = """
(function() {
  const vw = window.innerWidth, vh = window.innerHeight;
  const clipped = [], collided = [];
  for (const el of document.querySelectorAll('a, button')) {
    const text = (el.textContent || '').trim();
    if (!text) continue;
    const style = getComputedStyle(el);
    if (style.visibility === 'hidden' || style.display === 'none') continue;
    const rect = el.getBoundingClientRect();
    if (rect.width === 0 && rect.height === 0) continue;
    if (rect.top >= vh || rect.bottom <= 0) continue;
    if (rect.right > vw + 1 || rect.left < -1) {
      clipped.push(text.slice(0, 60) + ` (right=${Math.round(rect.right)}, `
        + `left=${Math.round(rect.left)}, viewport=${vw})`);
    }
  }
  const textEls = document.querySelectorAll(
    'p, h1, h2, h3, span, a, button, li, figcaption, dt, dd');
  for (const el of textEls) {
    let hasDirectText = false;
    for (const node of el.childNodes) {
      if (node.nodeType === 3 && node.textContent.trim()) {
        hasDirectText = true;
        break;
      }
    }
    if (!hasDirectText) continue;
    const text = (el.textContent || '').trim();
    const style = getComputedStyle(el);
    if (style.visibility === 'hidden' || style.display === 'none'
        || parseFloat(style.opacity) === 0) continue;
    const rect = el.getBoundingClientRect();
    if (rect.width === 0 || rect.height === 0) continue;
    const cx = rect.left + rect.width / 2, cy = rect.top + rect.height / 2;
    if (cx < 0 || cx > vw || cy < 0 || cy > vh) continue;
    const topEl = document.elementFromPoint(cx, cy);
    if (!topEl) continue;
    if (topEl !== el && !el.contains(topEl) && !topEl.contains(el)) {
      if (topEl.closest('.bar, .callbar, .progress')) continue;
      const label = topEl.className && typeof topEl.className === 'string'
        ? topEl.tagName + '.' + topEl.className.split(' ').join('.')
        : topEl.tagName;
      collided.push(`"${text.slice(0, 40)}" covered by ${label}`);
    }
  }
  return JSON.stringify({clipped, collided});
})()
"""


@pytest.mark.skipif(chrome() is None, reason="no Chrome/Chromium on this machine")
def test_no_control_is_clipped_and_no_text_is_covered_at_any_review_width():
    from app.site.pipeline import STAGES, run_stage, spec_from_config
    from app.site.render import build_from_spec
    from app.store import db, leads, sites

    binary = chrome()
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
            site_file.write_text(_link_photographs(page, brief))

            for label, width, height in WIDTHS:
                result = json.loads(
                    _evaluate(binary, site_file, width, height, _PROBE))
                if result["clipped"] or result["collided"]:
                    offenders[f"{slug}:{label}"] = result

    assert not offenders, (
        f"an element is clipped by the viewport or painted over at these "
        f"(fixture, width) combinations: {json.dumps(offenders, indent=2)}")
