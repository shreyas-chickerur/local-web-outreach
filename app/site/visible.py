"""Phase 2, Step 2: the one extraction function every gate reads.

Every existing content gate (`render.unsupported()`, `provenance.
unexplained_sentences()`) reads SOURCE markup with a regex. That is fine
for `render.py`'s own output — server-rendered, nothing added after
load — and blind on a bundled page whose entire document lives inside a
`<script>` tag: the roadmap's locked decision (see `.reviews/
phase-2-seam.md`) is that a gate must read the RENDERED document, not
source, or it passes vacuously on exactly the pages it most needs to
check.

`visible_text_runs()` is that one shared reader. Given a page (rendered
or plain), it returns an ORDERED list of every visible text run, each
tagged with its own element and a simple tag-path — not CSS classes,
which only `render.py`'s own output ever carries, and a foreign page
never will. A gate built on tag/word-count shape (a heading, a button, a
nav item) ports to any markup; a gate built on `render.py`'s own class
names does not, which is exactly what stayed broken in `provenance.py`
until this file existed.

`needs_render()` and `render()` are kept separate, deliberately, per
this round's own rule ("make the choice explicit in the function, not
implicit"): a page with no `<script>` tag cannot possibly differ once
"rendered" — there is nothing to run — so a caller checks first and only
pays for a real headless-Chrome round trip when the page could actually
have added content after load.
"""

from __future__ import annotations

import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from html.parser import HTMLParser

# Never contribute visible text: script/style bodies are code or CSS, not
# prose, and a bundled page's entire document sometimes lives inside one
# of these — the exact case `needs_render()` exists to route around, not
# to accidentally read as text here.
_SKIP_TAGS = frozenset({"script", "style", "template", "svg", "noscript"})

# Block-level tags start a new run; everything else (span, a, b, em,
# strong, label, and any tag not listed) is inline and folds into
# whatever run is already open. This is what lets
# `<span>Julien hosted ... guests</span><span>while living in Paris.</span>`
# read as ONE sentence rather than two incomplete fragments — the exact
# shape a foreign page's markup uses to split a sentence across elements.
_BLOCK_TAGS = frozenset({
    "html", "body", "p", "div", "section", "article", "header", "footer",
    "nav", "aside", "main", "h1", "h2", "h3", "h4", "h5", "h6", "li",
    "blockquote", "figure", "figcaption", "table", "tr", "td", "th",
    "ul", "ol", "form", "button",
})

# Void elements never carry a closing tag — treated as an inline word
# boundary (a line break should not glue two words together), never as
# something that opens or closes a run.
_VOID_TAGS = frozenset({
    "br", "hr", "img", "input", "meta", "link", "area", "base", "col",
    "embed", "source", "track", "wbr",
})

_WS_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class VisibleRun:
    """One run of visible text, as a real browser (or, for a scriptless
    page, the source markup itself) would show it — the element it
    belongs to, and a plain tag breadcrumb from the document root, e.g.
    ``"html>body>section>div>p"``. No CSS classes: those are `render.
    py`'s own vocabulary, not something a foreign page shares."""

    text: str
    tag: str
    path: str


class _Walker(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._stack: list[str] = []
        self._skip_depth = 0
        self._buf: list[str] = []
        self._buf_tag = "body"
        self._buf_path = "body"
        self.runs: list[VisibleRun] = []

    def _flush(self) -> None:
        text = _WS_RE.sub(" ", "".join(self._buf)).strip()
        if text:
            self.runs.append(VisibleRun(text=text, tag=self._buf_tag,
                                        path=self._buf_path))
        self._buf = []

    def _path(self) -> str:
        return ">".join(self._stack) or "body"

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if self._skip_depth or tag in _SKIP_TAGS:
            self._skip_depth += 1
            self._stack.append(tag)
            return
        if tag in _VOID_TAGS:
            self._buf.append(" ")
            return
        if tag in _BLOCK_TAGS:
            self._flush()
            self._stack.append(tag)
            self._buf_tag, self._buf_path = tag, self._path()
        else:
            self._stack.append(tag)
            self._buf.append(" ")

    def handle_startendtag(self, tag: str, attrs: list) -> None:
        if not self._skip_depth:
            self._buf.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if self._skip_depth:
            if tag in self._stack:
                while self._stack and self._stack[-1] != tag:
                    self._stack.pop()
                if self._stack:
                    self._stack.pop()
            if tag in _SKIP_TAGS:
                self._skip_depth = max(0, self._skip_depth - 1)
            return
        if tag in _BLOCK_TAGS:
            self._flush()
        else:
            self._buf.append(" ")
        if tag in self._stack:
            while self._stack and self._stack[-1] != tag:
                self._stack.pop()
            if self._stack:
                self._stack.pop()
        if tag in _BLOCK_TAGS:
            self._buf_tag = self._stack[-1] if self._stack else "body"
            self._buf_path = self._path()

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            self._buf.append(data)


def visible_text_runs(html: str) -> list[VisibleRun]:
    """Every visible text run in `html`, in document order.

    `html` is whatever the caller has already decided is "the page" —
    source markup for a page `needs_render()` says has nothing left to
    run, or a rendered `document.documentElement.outerHTML` otherwise.
    This function does not render anything itself and does not care
    which one it was handed; that choice belongs to the caller, not
    hidden inside here.
    """
    walker = _Walker()
    walker.feed(html or "")
    walker._flush()
    return walker.runs


_SCRIPT_TAG_RE = re.compile(r"<script\b", re.IGNORECASE)


def needs_render(html: str) -> bool:
    """Could this page's DOM differ from its own source markup?

    True the moment a `<script>` tag is present anywhere — the exact
    shape of the roadmap's locked risk (a bundled page's whole document
    lives inside one) and the class-5 planting in `tests/fixtures/
    seam/*-foreign.html`. Mechanical, not a guess about what the script
    actually does: a page that never adds visible content after load
    still costs nothing extra to render correctly, and a page that does
    is exactly the one a shortcut here would miss.
    """
    return bool(_SCRIPT_TAG_RE.search(html or ""))


def render(call: Callable[[str, dict | None], dict], url: str, *,
          timeout: float = 60.0, settle_seconds: float = 1.5) -> str:
    """Navigate an ALREADY-OPEN CDP session to `url` and return the DOM's
    outerHTML once the page settles.

    Takes `call` from an existing `app.adapters.chrome_cdp.cdp_session`
    rather than opening its own — this round's resource rule is one
    browser process for the whole round, reused, so every page this
    round renders (the ported gates' corpus re-run, the one real design
    page) navigates the SAME tab in sequence rather than launching a
    fresh Chrome per page, which `site_fetch.render_document` does (by
    design, for the production crawl, where the isolation is worth the
    cost) and this round explicitly must not.
    """
    call("Page.navigate", {"url": url})
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        state = call("Runtime.evaluate", {
            "expression": "document.readyState", "returnByValue": True})
        if state.get("result", {}).get("result", {}).get("value") == "complete":
            break
        time.sleep(0.05)
    else:
        raise TimeoutError(f"document.readyState never reached 'complete' "
                          f"within {timeout}s: {url}")
    time.sleep(settle_seconds)
    dom = call("Runtime.evaluate", {
        "expression": "document.documentElement.outerHTML",
        "returnByValue": True})
    return dom.get("result", {}).get("result", {}).get("value") or ""
