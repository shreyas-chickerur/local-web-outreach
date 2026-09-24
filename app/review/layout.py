"""Measure a page in a real browser for text something else covers or spills past.

Reads element geometry in Chrome at real window sizes, rather than asking anyone
to judge a screenshot. Three faults, each a `defect` in the review:

1. CLIPPED: a link or button whose text runs past the window's left or right edge.
2. COVERED: text where a point on it (left edge, centre, right edge) belongs to a
   different element painted on top. Anything with a fixed position (a sticky
   navbar, a pinned call bar) floats above what scrolls under it by design.
3. SPILLS: text that runs past the bottom of its own section. Yama's opening
   section was capped at 900 pixels while its text needed up to 1,430, and ran
   over the hours below; the covered check never saw it, because the spilled
   text sat beside the next section's words rather than under them.

Checking three points rather than the centre is what catches the fault Fish
Shack's version 5 shipped: a photograph covering the ends of a paragraph's
lines, every centre left clear.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path

from app.adapters import photos
from app.adapters.chrome_cdp import cdp_session, chrome
from app.review.checks import Finding

# (label, width, height): the windows a page is measured in.
WIDTHS = (("phone", 390, 844), ("tablet", 768, 1024), ("laptop", 1280, 800),
          ("wide screen", 1920, 1080))

PROBE = """
(async function() {
  // Fade-ins start hidden and shifted; scrolling through reveals them, so
  // nothing is measured half-way through arriving.
  for (let y = 0; y < document.documentElement.scrollHeight; y += 500) {
    window.scrollTo(0, y); await new Promise(r => setTimeout(r, 20)); }
  window.scrollTo(0, 0); await new Promise(r => setTimeout(r, 300));
  const vw = window.innerWidth, vh = window.innerHeight;
  const clipped = [], collided = [], spilled = [];
  const floating = (node) => { for (let n = node; n && n !== document.body; n = n.parentElement)
    if (getComputedStyle(n).position === 'fixed') return true; return false; };
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
  const textEls = [...document.querySelectorAll(
    'p, h1, h2, h3, span, a, button, li, figcaption, dt, dd')].filter(el =>
    [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim()));
  for (const el of textEls) {
    const text = (el.textContent || '').trim();
    const style = getComputedStyle(el);
    if (style.visibility === 'hidden' || style.display === 'none'
        || parseFloat(style.opacity) === 0) continue;
    const rect = el.getBoundingClientRect();
    if (rect.width === 0 || rect.height === 0) continue;
    const section = el.closest('section, header, footer, main > *');
    if (section && !floating(el)) {
      const box = section.getBoundingClientRect();
      if (rect.bottom > box.bottom + 2 && rect.top < box.bottom) {
        const name = section.id || (typeof section.className === 'string'
          ? section.className.split(' ')[0] : '') || section.tagName.toLowerCase();
        spilled.push(`"${text.slice(0, 40)}" runs ${Math.round(rect.bottom - box.bottom)}px `
          + `past the bottom of ${name}`);
      }
    }
    const cy = rect.top + rect.height / 2;
    if (cy < 0 || cy > vh) continue;
    for (const cx of [rect.left + 4, rect.left + rect.width / 2, rect.right - 4]) {
      if (cx < 0 || cx > vw) continue;
      const topEl = document.elementFromPoint(cx, cy);
      if (!topEl) continue;
      if (topEl !== el && !el.contains(topEl) && !topEl.contains(el)) {
        if (floating(topEl)) continue;
        const label = topEl.className && typeof topEl.className === 'string'
          ? topEl.tagName + '.' + topEl.className.split(' ').join('.')
          : topEl.tagName;
        collided.push(`"${text.slice(0, 40)}" covered by ${label}`);
        break;
      }
    }
  }
  return JSON.stringify({clipped, collided, spilled});
})()
"""


def measure(page: Path, width: int, height: int) -> dict[str, list[str]]:
    """The clipped controls, covered text and spilled text on `page` in one window."""
    binary = chrome()
    if not binary:
        raise RuntimeError("the layout check needs Chrome")
    # Reduced motion from the start, so a page's fade-ins and slow zooms stay
    # still while it is measured, without a second load to switch them off.
    with cdp_session(binary, page, width, height, 1.0, 30.0,
                     extra_flags=("--force-prefers-reduced-motion",)) as call:
        result = call("Runtime.evaluate", {"expression": PROBE, "returnByValue": True,
                                           "awaitPromise": True})
    found = result.get("result", {})
    if found.get("exceptionDetails"):
        raise RuntimeError(f"the probe failed: {found['exceptionDetails']}")
    return dict(json.loads(found["result"]["value"]))


def link_photographs(page: str, brief: dict, out_dir: Path) -> str:
    """Point `/photo/<lead>/<n>` at the cached files, so a file on disk stands
    alone without the workbench to ask, and a missing photograph cannot change
    the layout being measured."""
    names = list(brief.get("place_photos") or [])

    def local(match: re.Match) -> str:
        index = int(match.group(1))
        if index >= len(names):
            return match.group(0)
        cached = photos._cache_path(names[index], photos.MAX_WIDTH)
        return os.path.relpath(cached, out_dir) if cached.exists() else match.group(0)

    lead_id = brief.get("lead_id")
    return re.sub(rf"/photo/{lead_id}/(\d+)(?:\?[^\s\"'&)]*)?", local, page)


_SAY = {"spilled": "Text runs past the bottom of its section",
        "collided": "Text is covered by something else",
        "clipped": "A link or button runs off the edge of the screen"}


def defects(html: str, brief: dict, lead_id: int) -> list[Finding]:
    """Every layout fault on this page at each window size, as review findings."""
    if not chrome():
        return [Finding(stage="technical", verdict="unmeasured",
                        title="The layout was not measured",
                        detail="Chrome was not found on this machine, so nothing checked "
                               "for text that is covered or runs out of its section.")]
    found: list[Finding] = []
    with tempfile.TemporaryDirectory() as folder:
        page = Path(folder) / "index.html"
        page.write_text(link_photographs(html, {**brief, "lead_id": lead_id}, Path(folder)))
        seen: dict[tuple[str, str], list[str]] = {}
        for label, width, height in WIDTHS:
            for kind, items in measure(page, width, height).items():
                for item in items:
                    seen.setdefault((kind, item), []).append(f"{label} ({width} wide)")
    for (kind, item), where in seen.items():
        found.append(Finding(stage="technical", verdict="defect",
                             title=_SAY.get(kind, kind), detail=f"{item}, on {', '.join(where)}.",
                             locator=item.split('"')[1] if '"' in item else item))
    return found


def summary(found: list[Finding]) -> str:
    """One line for the chat: whether the new version's layout holds."""
    faults = [f for f in found if f.verdict == "defect"]
    if not faults:
        return ("Layout: not measured." if found
                else f"Layout: nothing covered or spilling, at {len(WIDTHS)} screen sizes.")
    return (f"Layout: {len(faults)} problem{'s' if len(faults) > 1 else ''}, first "
            f"{faults[0].title.lower()}: {faults[0].detail}")
