"""How much of a business's own site actually reaches the brief.

    .venv/bin/python tools/capture_census.py

There is no such number before this tool. `content_census.py` measures
BRIEF-TO-PAGE: given what got extracted, how much of it reaches the
rendered site. Nothing before this measured SITE-TO-BRIEF: given what
the business actually PUBLISHES, how much of it ever reaches the brief
in the first place. That is the gap "thicken the brief" is about — a
business's own material can be completely invisible before the content
census ever gets a chance to drop it, and the four causes fixed
alongside this tool (PDFs discarded, no JavaScript rendering, a
keyword-gated one-level crawl, and aggressive truncation caps) are
exactly the reasons it was.

For each fixture with a real `website_url` (16 of 19 — `contractor-bare`,
`restaurant-bare`, and `threadbare` have none):

1. Crawl the live site INDEPENDENTLY of `app.workbench.brief`'s own
   production crawl — a different, deliberately generous BFS (depth 2,
   a page budget of `PAGE_BUDGET`) through real headless Chrome
   (`app.adapters.site_fetch.render_document`), so JavaScript-built
   content is visible here too. Any PDF linked from a crawled page is
   read the same way `app.workbench.brief._read_menu_pdfs` reads a menu.
   This crawl is the measurement's OWN yardstick for "what the site
   actually says" — it must not be defined by whatever the production
   pipeline happens to fetch, or fixing the production crawl would move
   the ruler along with the number it is supposed to measure.
2. Build the REAL current brief via `app.workbench.brief.build_brief()`
   — whatever the production pipeline actually does today, unmodified.
3. Reduce both to a vocabulary: lowercase words of three or more letters,
   a short list of common English words excluded, so the percentage
   reflects real content overlap rather than "the" and "and" appearing
   everywhere regardless of how good the extraction is.

Capture % = |site_vocab ∩ brief_vocab| / |site_vocab|. A rough, honest,
word-level measure of "how much of what they publish did we actually
carry" — not exact (no measurement of unstructured text ever is), but
real: two independently-built readings of the same site, compared,
rather than assumed.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urljoin

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.adapters.chrome_cdp import chrome  # noqa: E402
from app.adapters.pdf_read import read_pdf_text  # noqa: E402
from app.adapters.site_fetch import default_fetcher, fetch_bytes, render_document  # noqa: E402
from app.workbench.brief import build_brief  # noqa: E402
from app.workbench.extract import ExtractedSite, content_page_urls, html_to_text  # noqa: E402

FIXTURES = Path("tests/fixtures/briefs")

# A different, more generous crawl than `app.workbench.brief`'s own
# production one (CRAWL_DEPTH=2, CRAWL_PAGE_BUDGET=24) — deliberately not
# reused, on purpose: this crawl is the ruler, and a ruler that moves with
# the thing it measures cannot show whether the thing got better.
CRAWL_DEPTH = 2
PAGE_BUDGET = 30

_WORD_RE = re.compile(r"[a-z]{3,}")
_PDF_HREF_RE = re.compile(r'href=["\']([^"\']+\.pdf(?:\?[^"\']*)?)["\']', re.IGNORECASE)

# Common enough to say nothing about content, in EITHER direction: leaving
# them in would inflate the denominator with words no extraction ever
# needs to carry, and would inflate the intersection with matches that
# prove nothing about whether real content reached the brief.
_STOPWORDS = frozenset({
    "the", "and", "for", "are", "but", "not", "you", "your", "our", "with",
    "this", "that", "from", "have", "has", "had", "was", "were", "will",
    "can", "all", "out", "get", "use", "used", "into", "who", "how", "why",
    "what", "when", "where", "which", "their", "them", "they", "there",
    "here", "over", "more", "most", "some", "such", "than", "then",
    "each", "few", "own", "same", "too", "very", "just", "one", "two",
    "three", "off", "about", "also", "any", "been", "being", "both", "call",
    "come", "could", "did", "does", "down", "every", "find", "first",
    "give", "going", "good", "great", "help", "home", "its", "know",
    "let", "like", "look", "made", "make", "many", "may", "might", "must",
    "new", "now", "only", "other", "page", "part", "people", "place",
    "please", "right", "see", "should", "site", "still", "take", "time",
    "today", "under", "want", "way", "web", "well", "would", "year",
    "years", "you're", "we're", "don't", "it's", "we've", "com", "www",
})


def _words(text: str) -> set[str]:
    return {w for w in _WORD_RE.findall(text.lower()) if w not in _STOPWORDS}


@dataclass
class CrawlResult:
    pages: int = 0
    text: str = ""
    pdf_texts: list[str] = field(default_factory=list)


def _independent_crawl(binary: str, base_url: str) -> CrawlResult:
    """Everything a visitor could actually read on this site — a BROAD
    crawl, not the production one. See the module docstring for why the
    two must stay separate."""
    out = CrawlResult()
    home = render_document(binary, base_url, timeout=25.0)
    if not home.ok or not home.html:
        return out
    out.pages = 1
    texts = [html_to_text(home.html)]
    pdf_urls = {urljoin(base_url, m) for m in _PDF_HREF_RE.findall(home.html)}

    visited = {base_url}
    queue = content_page_urls(home.html, base_url, limit=PAGE_BUDGET)
    depth = {u: 1 for u in queue}
    i = 0
    while i < len(queue) and out.pages < PAGE_BUDGET:
        url = queue[i]
        i += 1
        if url in visited:
            continue
        visited.add(url)
        page = render_document(binary, url, timeout=25.0)
        out.pages += 1
        if not (page.ok and page.html):
            continue
        texts.append(html_to_text(page.html))
        pdf_urls |= {urljoin(url, m) for m in _PDF_HREF_RE.findall(page.html)}
        if depth[url] < CRAWL_DEPTH:
            remaining = PAGE_BUDGET - len(queue)
            if remaining > 0:
                for link in content_page_urls(page.html, url, limit=remaining):
                    if link not in visited and link not in depth:
                        depth[link] = depth[url] + 1
                        queue.append(link)

    for pdf_url in pdf_urls:
        data = fetch_bytes(pdf_url)
        text = read_pdf_text(data) if data else None
        if text:
            out.pdf_texts.append(text)

    out.text = "\n".join(texts)
    return out


def _brief_text(published: ExtractedSite | None) -> str:
    parts: list[str] = []
    if published is None:
        return ""
    for field_name in ("title", "description", "about"):
        value = getattr(published, field_name, None)
        if value:
            parts.append(str(value))
    parts.extend(published.services)
    parts.extend(published.products)
    parts.extend(published.hours)
    for block in published.blocks:
        parts.append(str(block.get("heading", "")))
        parts.append(str(block.get("text", "")))
    for item in published.menu_items:
        parts.append(str(item.get("name", "")))
        parts.append(str(item.get("description", "")))
    return "\n".join(parts)


def _fixture_website(path: Path) -> str | None:
    data = json.loads(path.read_text())
    return data.get("website_url") or None


def main() -> int:
    binary = chrome()
    if not binary:
        print("No Chrome or Chromium found.", file=sys.stderr)
        return 1

    rows: list[dict[str, object]] = []
    captures: list[float] = []
    for path in sorted(FIXTURES.glob("*.json")):
        slug = path.stem
        website = _fixture_website(path)
        if not website:
            print(f"  {slug:18} (no website_url — skipped)")
            continue

        crawl = _independent_crawl(binary, website)
        site_words = _words(crawl.text) | _words("\n".join(crawl.pdf_texts))
        if not site_words:
            print(f"  {slug:18} FAILED: could not read the live site "
                 f"({website})", file=sys.stderr)
            continue

        brief = build_brief(website, fetcher=default_fetcher())
        pub = brief.published
        brief_words = _words(_brief_text(pub))
        capture = len(site_words & brief_words) / len(site_words)

        blocks = len(pub.blocks) if pub else 0
        block_chars = sum(len(b.get("text", "")) for b in pub.blocks) if pub else 0
        menu_items = len(pub.menu_items) if pub else 0
        services = len(pub.services) if pub else 0

        rows.append({
            "slug": slug, "pages_crawled": crawl.pages,
            "blocks": blocks, "block_chars": block_chars,
            "menu_items": menu_items, "services": services,
            "capture_pct": capture,
        })
        captures.append(capture)
        print(f"  {slug:18} pages={crawl.pages:3}  blocks={blocks:3}  "
             f"block_chars={block_chars:5}  menu_items={menu_items:3}  "
             f"services={services:3}  capture={capture:.0%}")

    if captures:
        print()
        avg = sum(captures) / len(captures)
        print(f"{len(captures)} fixtures measured, mean capture {avg:.0%}")

    out_path = Path("tests/fixtures/capture_baseline.json")
    out_path.write_text(json.dumps(rows, indent=2, sort_keys=False) + "\n")
    print(f"  wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
