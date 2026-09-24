"""A design prompt written from the brief, so a new lead can be designed from the workbench.

Fish Shack's and The Heritage Table's prompts were written by hand in a
separate session, which left the workbench's build button with nothing to hand
a design run: it fell back to the older generator, and Yama Izakaya's first
page came out of that. This writes the same sections from what is stored —
the business, what its own site says, its menu, its reviews, its photographs,
the playbook it will be scored against and every earlier site it must not look
like — and the brief itself, whole, as the appendix.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from pathlib import Path

from app.store import brief_archive, folders, leads

PLAYBOOKS = Path(__file__).parent / "playbooks"

_INSTRUCTION = """Design and build the website for the business described below. One page,
responsive — the same page at phone width and desktop width, not two designs.

Write it the way you would if this were a real client paying a thousand dollars for it,
and it has to make the people who would love this place want to go. Use the material
below as your knowledge of the business. You are not restricted to repeating it verbatim:
write headings, connective prose, section framing and anything else the page needs in
your own words.

Every factual claim the finished page makes will be enumerated and checked afterwards
against this brief, and anything unsupported comes back to you as a comment. That check
happens after you build, not while. Build the best page.

Write as the business, in its own voice: this is their website. Never quote the business
back to itself or say where a fact came from ("from their own website", "as listed on
Google"). Use the plain, specific words the owner would use. No stock phrases: "you're in
luck", "look no further", "nestled", "elevate", "a feast for the senses", "whether you're
... or ...", questions as headings, lists of three for rhythm.

Look at every photograph. Name a dish only with high confidence: when the photograph
shows it unmistakably. Where it is a dish on the menu, use the menu's exact name. Where it
matches nothing on the menu but is unmistakable, use its usual name ("tonkotsu ramen");
the claim check lists that name for the operator to confirm with the business. Name no
more than you can see: "yakitori", not which cuts. When you are not sure, a short plain
caption, or none. A wrong dish name is worse than a plain caption. A menu kept on a
listing site sometimes carries that site's own filler as a description ("Ray-finned
fish" for salmon): never print those.

Anything that depends on the day or the time (today's hours picked out, "open now") is
worked out in the visitor's browser, in the business's own time zone, and the hours
after midnight belong to the evening before. Never write a day into the page."""

# A trade names a restaurant in many ways; a brief with a menu is one whatever it says.
_FOOD = re.compile(r"restaurant|cafe|café|bar\b|grill|bakery|food|diner|sushi|pizz|izakaya"
                   r"|kitchen|bistro|taco|bbq|barbecue|coffee", re.I)


def playbook_for(brief: dict) -> Path:
    published = brief.get("published") or {}
    food = _FOOD.search(str(brief.get("trade") or "")) or published.get("menu_items")
    return PLAYBOOKS / ("restaurant.md" if food else "home_services.md")


def _earlier_sites(conn: sqlite3.Connection, lead_id: int) -> list[str]:
    rows = conn.execute(
        "SELECT DISTINCT l.name, l.location FROM sites s JOIN leads l ON l.id = s.lead_id"
        " WHERE s.lead_id != ? AND TRIM(COALESCE(s.spec, '')) = ''", (lead_id,))
    return [f"{r['name']} ({r['location']})" for r in rows]


def render(conn: sqlite3.Connection, lead_id: int, brief: dict, revision: int) -> str:
    """The whole prompt, as text."""
    name = str(brief.get("name") or f"lead {lead_id}")
    pointer = brief_archive.current(name) or {}
    playbook = playbook_for(brief)
    playbook_text = playbook.read_text()
    out = [f"# Design prompt — {name} (revision {revision})", "", "## Provenance",
           f"- Brief file: {pointer.get('path', 'not archived')}",
           f"- Brief content hash: {pointer.get('hash', '')}",
           f"- Playbook: app/design/playbooks/{playbook.name} "
           f"(sha256 {hashlib.sha256(playbook_text.encode()).hexdigest()[:16]})",
           "- Written by app/design/prompt.py from the stored brief, with corrections applied.",
           "", "## Instruction", "", _INSTRUCTION]
    earlier = _earlier_sites(conn, lead_id)
    if earlier:
        out += ["", "It must not look like any site this system made before: "
                + "; ".join(earlier) + ". The playbook's last section lists every device "
                "they used. Take the register from this place, not from them."]

    published = brief.get("published") or {}
    out += ["", "## The business", "", name, str(brief.get("location") or "")]
    for key in ("website_url", "trade"):
        if brief.get(key):
            out.append(str(brief[key]))
    facts = brief.get("facts") or []
    sure = [f for f in facts if f.get("confidence") in ("verified", "operator_verified")]
    unsure = [f for f in facts if f not in sure]
    if sure:
        out += ["", "Verified facts (backed by two independent sources, or by the operator):"]
        out += [f"- {f.get('label') or f['field']}: {f.get('value')}" for f in sure]
    if unsure:
        # Told "do not state these as fact", Yama's design hedged in the page
        # itself ("per Google's listing", "please call to confirm"). The claim
        # inventory lists these for the operator; the visitor never hears of it.
        out += ["", "Found by one source only, or disagreed on. Use one if the page needs it, "
                "stated plainly, or leave it out; never tell the visitor it is unconfirmed "
                "or where it came from. The claim check lists these for the operator:"]
        out += [f"- {f.get('label') or f['field']} ({f.get('confidence')}): {f.get('value')}"
                for f in unsure]
    for rating in brief.get("ratings") or []:
        out.append(f"\n{str(rating.get('source', '')).title()} rating: {rating.get('value')} "
                   f"from {rating.get('reviews')} reviews.")

    pages = brief.get("pages") or []
    site = [p for p in pages if p.get("kind") == "page" and p.get("read")]
    menus = [p for p in pages if p.get("kind") in ("pdf", "image", "menu") and p.get("read")]
    unread = [p for p in pages if not p.get("read")]
    if site:
        out += ["", "## What their own site says"]
        for page in site:
            out += ["", f"{page['url']}:", page.get("text", "")]
    if menus:
        out += ["", "## The menu, in full, as their site prints it", "",
                "Prices are theirs; print them exactly, in one format."]
        for page in menus:
            where = ("the menu their site links to, kept on another site"
                     if page.get("kind") == "menu" else "their site")
            out += ["", f"{page['url']} ({where}):", page.get("text", "")]
    elif published.get("menu_items"):
        out += ["", "## Menu items their site lists", ""]
        out += [f"- {json.dumps(item, ensure_ascii=False)}" for item in published["menu_items"]]
    else:
        out += ["", "## The menu", "", "Their own site publishes no menu the crawl could read. "
                "Do not invent dishes or prices; describe the food only as the material "
                "above and the reviews do."]
    if unread:
        out += ["", "Pages the crawl could not read, and why:"]
        out += [f"- {p['url']}: {p.get('reason') or 'no reason recorded'}" for p in unread]

    reviews = brief.get("testimonials") or []
    if reviews:
        out += ["", "## Reviews (verbatim; a person's name may be printed with their words)", ""]
        out += [f"- {r.get('author')}, {r.get('rating')} stars: \"{r.get('text')}\""
                for r in reviews]

    count = len(brief.get("place_photos") or [])
    out += ["", "## Photographs available", "",
            "The business's own place photographs, served by the workbench so no key appears "
            "in the page. Look at each one before choosing where it goes. Use these paths as "
            "given; `w` may be 800, 1600, 2400 or 3200.", ""]
    out += [f"- `/photo/{lead_id}/{n}?w=1600`" for n in range(count)] or ["- none"]

    out += ["", "## The playbook this page will be scored against", "", playbook_text,
            "", "## Appendix: the brief, verbatim", "",
            "Everything above was taken from this file. Where the sections above and this "
            "file disagree, this file is right.", "", "```json",
            json.dumps(brief, indent=2, ensure_ascii=False, default=str), "```", ""]
    return "\n".join(out)


def write(conn: sqlite3.Connection, lead_id: int) -> Path:
    """Write the next revision of this lead's design prompt into its folder."""
    brief = leads.brief_with_overrides(conn, lead_id)
    folder = folders.of(str(brief.get("name") or f"lead {lead_id}")) / "prompts"
    folder.mkdir(parents=True, exist_ok=True)
    taken = [int(m.group(1)) for f in folder.glob("v*.md")
             if (m := re.fullmatch(r"v(\d+)\.md", f.name))]
    revision = max(taken, default=0) + 1
    path = folder / f"v{revision}.md"
    path.write_text(render(conn, lead_id, brief, revision))
    return path
