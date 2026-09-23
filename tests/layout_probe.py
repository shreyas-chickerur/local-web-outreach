"""Measure a rendered page for text something else is painted over.

Shared by the layout tests. Reads element geometry in a real Chrome at a real
viewport, rather than asking anyone to judge a screenshot. Two faults:

1. CLIPPED: a link or button with text whose box runs past the viewport's
   left or right edge.
2. COVERED: an element with its own text where a point on it (left edge,
   centre, right edge) resolves to a different element that is neither its
   ancestor nor its descendant, so something is painted on top of the text.
   Anything with a fixed position (a sticky navbar, a pinned call bar) floats
   above what scrolls under it by design and is not a collision.

Checking three points rather than the centre is what catches the fault Fish
Shack's version 5 shipped: a photograph covering the ends of a paragraph's
lines, every centre left clear.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from app.adapters import photos
from app.adapters.chrome_cdp import cdp_session, chrome

__all__ = ["WIDTHS", "chrome", "link_photographs", "measure"]

# (label, width, height): the widths a design review is read at.
WIDTHS = (("desktop", 1440, 1100), ("mobile", 390, 844), ("page", 1440, 6000))

PROBE = """
(function() {
  const vw = window.innerWidth, vh = window.innerHeight;
  const clipped = [], collided = [];
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
  return JSON.stringify({clipped, collided});
})()
"""


def measure(page: Path, width: int, height: int) -> dict[str, list[str]]:
    """The clipped controls and covered text on `page` at one viewport."""
    binary = chrome()
    assert binary, "the layout probe needs Chrome"
    with cdp_session(binary, page, width, height, 1.0, 20.0) as call:
        result = call("Runtime.evaluate", {"expression": PROBE, "returnByValue": True})
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
