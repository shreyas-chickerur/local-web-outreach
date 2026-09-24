"""Assemble a version's findings from the same material the prompt was built
from — the brief, the text the crawl read from the business's own site, and the
page itself.

Kept apart from `checks` so the checks stay pure functions over text, testable
without a database, and apart from `store.reviews` so the record does not
depend on how a finding was produced.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from app.review import checks
from app.store import brief_archive, folders


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def page_text(brief: dict) -> str:
    """Every page the crawl read on their own site, as one text to search.

    This replaced `captures/<slug>/live-site.md`, a copy made by hand that
    nothing kept current: the checks gave confident answers from a site as it
    stood weeks earlier. Pages are separated by a blank line, so a passage
    never runs from one page into the next.
    """
    return "\n\n".join(p.get("text", "") for p in brief.get("pages") or []
                        if p.get("read") and p.get("text"))


def material(name: str, *, root: Path | None = None) -> tuple[dict, str, dict]:
    """The archived brief for a business and the page text it carries, hashed.

    A brief with no page text is not an error — every crawl before the crawl
    kept its pages has none — but it is recorded, because a claim check run
    without the business's own words can only ever return "unsourced".
    """
    base = root or Path()
    # Through the archive's own layout: this module once built its own path
    # to the crawls and would have gone on reading a folder nothing wrote.
    brief_path = brief_archive.directory(
        name, None if root is None else base / folders.ROOT) / "current.json"

    brief: dict = {}
    if brief_path.exists():
        brief = json.loads(brief_path.read_text())
        # `current.json` is a POINTER — {"path", "hash", "captured_at"} — that
        # `brief_archive.save` rewrites on every crawl. Read literally it is a
        # three-key dictionary with no facts in it, which every check then
        # reports as "unsourced" while the screen says a brief was loaded. So
        # follow it to the archived crawl it names.
        if "facts" not in brief and brief.get("path"):
            pointed_at = base / str(brief["path"])
            if pointed_at.exists():
                brief = json.loads(pointed_at.read_text())
                brief_path = pointed_at
            else:
                brief = {}
    text = page_text(brief)
    pages = brief.get("pages") or []
    return brief, text, {
        "brief_file": str(brief_path) if brief else "",
        "brief_hash": _hash(json.dumps(brief, sort_keys=True, default=str)) if brief else "",
        # Kept under the old key names: the reviews table and the review screen
        # already store and print them.
        "capture_file": (f"page text of {sum(1 for p in pages if p.get('read'))} of "
                         f"{len(pages)} pages, in {brief_path}") if pages else "",
        "capture_hash": _hash(text) if text else "",
        "capture_missing": not text,
    }


def _without_superseded(brief: dict, text: str) -> tuple[dict, str, list[dict] | None]:
    """The brief and page text with every value a correction replaced removed.

    A correction outranks the crawl, but the crawl's page text still prints the
    old value, and so does the brief's own record of what was superseded. Both
    are searched for support, so a page repeating the corrected-away phone
    number came back corroborated by the very text the correction replaced.
    """
    # ponytail: matches the old value's words with any punctuation between, so
    # "(111) 111-1111" also catches "111-111-1111"; an abbreviated address
    # ("E" for "East") still gets through. Normalise per field if that bites.
    old = [str(f["superseded"]) for f in brief.get("facts") or [] if f.get("superseded")]
    patterns = [r"\W*".join(map(re.escape, words)) for words in
                (re.findall(r"[A-Za-z0-9]+", value) for value in old) if words]

    def clean(words: str) -> str:
        for pattern in patterns:
            words = re.sub(pattern, " ", words, flags=re.IGNORECASE)
        return words

    pages = brief.get("pages")
    judged = {k: v for k, v in brief.items() if k != "pages"}
    judged["facts"] = [{k: v for k, v in f.items() if k != "superseded"}
                       for f in brief.get("facts") or []]
    return judged, clean(text), (None if pages is None
                                 else [{**p, "text": clean(p.get("text", ""))} for p in pages])


def findings(html: str, brief: dict, capture: str) -> list[dict]:
    """Everything the checks can see, ordered so the sharp end is first."""
    brief, capture, pages = _without_superseded(brief, capture)
    where = []
    if brief.get("website_url"):
        where.append({"label": "The business's own site", "url": brief["website_url"]})
    for fact in brief.get("facts") or []:
        for source in (fact.get("sources") or [])[:1]:
            url = source.get("source_url")
            if url and not any(w["url"] == url for w in where):
                where.append({"label": f"{source.get('source_type','source')}"
                                       f" — {fact.get('label', fact.get('field'))}",
                              "url": url})

    found = list(checks.contradictions(html, brief, where))
    found += checks.mechanics(html, brief)
    found += checks.inventory(html, brief, capture, where, pages)
    for page in pages or []:
        if not page.get("read"):
            found.insert(0, checks.Finding(
                stage="claim", verdict="unmeasured",
                title=f"Could not read {page.get('url', 'a page')}",
                detail=f"The crawl tried this {page.get('kind', 'page')} and could not "
                       f"read it: {page.get('reason') or 'no reason recorded'}. A claim "
                       "only that page could back shows as unsourced below.",
                locator=page.get("url", "")))
    if pages is None:
        found.insert(0, checks.Finding(
            stage="claim", verdict="unmeasured",
            title="This brief was crawled before page text was kept",
            detail="Every claim below is unsourced by default, because there is "
                   "none of the business's own text to check it against. Re-crawl "
                   "before reading this as evidence of anything."))
    return [f.as_row() for f in found]
