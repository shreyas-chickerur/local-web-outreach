"""What a photograph shows, according to a person.

Shape is measurable and subject matter is not. A landscape shot of raw peppers
is the wrong lead for a fine dining room, and no amount of filename parsing
finds that out. Rather than guess, the operator labels a handful of candidates
once per lead and every later decision — the hero above all — uses those.
"""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import UTC, datetime

from app.store.db import operator

# What a picture can be, ordered by how well it leads a page. The list is
# deliberately short: a longer one is slower to apply and no more useful.
LABELS = ("dish", "room", "exterior", "people", "team", "work", "product",
          "detail", "drink", "ingredients", "award", "logo", "other",
          "unclear")

# Written by the vision pass rather than by a person. Kept apart because the
# operator's judgement outranks the machine's and has to stay attributed —
# a machine label unblocks the first build, and is replaced the moment a
# person disagrees with it.
MACHINE_ACTOR = "claude-vision"

# "I looked at this one and cannot tell what it is" — a decision, and a
# different thing from never having looked. Without somewhere to record it,
# a blank field means both, and the build cannot know whether the operator is
# finished. It never leads: an unidentifiable photograph is the worst possible
# first impression.
UNREVIEWED = ""
SKIPPED = "unclear"

# What a description means, longest phrase first so "award badge" beats "badge"
# and "dining room" is never read as two separate things. Same matching
# discipline as the instruction parser: ordered tuples, first match wins.
_TAG_PHRASES: tuple[tuple[str, str], ...] = (
    # Ordered most specific to most generic, and first match wins. Ordering is
    # the whole design: "chef in the kitchen" is a photograph of a person, not
    # of a room, and "a cocktail on the bar" is a drink. Put the generic room
    # words first and both come out wrong.
    ("award badge", "award"), ("james beard", "award"), ("best of", "award"),
    ("award", "award"), ("badge", "award"), ("laurel", "award"),
    ("medal", "award"), ("nominee", "award"), ("nominated", "award"),
    ("winner", "award"), ("certificate", "award"), ("rosette", "award"),

    ("logo", "logo"), ("wordmark", "logo"), ("brand mark", "logo"),

    # People before rooms: someone photographed at work is the subject.
    ("chef", "people"), ("staff", "people"), ("team", "people"),
    ("owner", "people"), ("barista", "people"), ("bartender", "people"),
    ("server", "people"), ("people", "people"), ("guests", "people"),
    ("customers", "people"), ("portrait", "people"), ("us ", "people"),

    # Drinks before rooms: a cocktail on the bar is a drink.
    ("cocktail", "drink"), ("wine", "drink"), ("beer", "drink"),
    ("coffee", "drink"), ("espresso", "drink"), ("drink", "drink"),
    ("glass of", "drink"), ("pint", "drink"),

    # Dishes before rooms: a plate on a table is a dish.
    ("plated", "dish"), ("plate", "dish"), ("dish", "dish"), ("meal", "dish"),
    ("sandwich", "dish"), ("burger", "dish"), ("dessert", "dish"),
    ("bread", "dish"), ("brisket", "dish"), ("steak", "dish"),
    ("pizza", "dish"), ("menu item", "dish"), ("food", "dish"),

    ("raw ", "ingredients"), ("produce", "ingredients"),
    ("ingredient", "ingredients"), ("vegetable", "ingredients"),
    ("peppers", "ingredients"), ("tomatoes", "ingredients"),
    ("farm", "ingredients"), ("harvest", "ingredients"),

    ("storefront", "exterior"), ("signage", "exterior"), ("sign", "exterior"),
    ("outside", "exterior"), ("exterior", "exterior"), ("building", "exterior"),
    ("patio", "exterior"), ("street", "exterior"), ("front of", "exterior"),

    ("dining room", "room"), ("interior", "room"), ("inside", "room"),
    ("room", "room"), ("bar", "room"), ("table", "room"), ("seating", "room"),
    ("counter", "room"), ("kitchen", "room"),
)


def tag_for(description: str) -> str:
    """The category a description falls into, or "other".

    Free text is the honest interface — you know what the picture shows and no
    dropdown covers it — but placement needs a category, so one is derived and
    shown back for correction rather than assumed.
    """
    text = " ".join((description or "").lower().split())
    if not text:
        return "other"
    for phrase, tag in _TAG_PHRASES:
        if phrase in text:
            return tag
    return "other"

# How well each label works as a hero, per kind of business. A roofer's hero is
# finished work; a restaurant's is a plate or the room.
HERO_PREFERENCE: dict[str, tuple[str, ...]] = {
    # The plate first: nobody books a table because of the carpet.
    "food": ("dish", "room", "drink", "people", "exterior"),
    # Finished work, then the crew. A roofer sells competence, not premises.
    "trade": ("exterior", "people", "room"),
    # The practitioner, then the room. A waiting room is not a reason to go,
    # but a face is — and the equipment photograph is actively off-putting.
    "care": ("people", "room", "exterior"),
    # The room sells the treatment here in a way it does not in a clinic.
    "groom": ("room", "people", "exterior"),
    # Bodies moving in the space, then the space.
    "body": ("people", "room", "exterior"),
    # Professional services rarely have a photograph worth leading with, which
    # is a fact about the trade rather than about the business — the identity
    # call should be free to reach for type instead.
    "desk": ("people", "exterior", "room"),
    # What is on the shelves, then the shopfront.
    "retail": ("dish", "room", "exterior", "people"),
    "default": ("room", "exterior", "people", "dish"),
}
# The subjects added for the trades that had nowhere to put them: a roofer's
# finished job, a shop's stock, a practice's team.
HERO_PREFERENCE["trade"] = ("work", "exterior", "people", "team", "room")
HERO_PREFERENCE["care"] = ("people", "team", "room", "exterior")
HERO_PREFERENCE["groom"] = ("room", "work", "people", "exterior")
HERO_PREFERENCE["body"] = ("people", "room", "work", "exterior")
HERO_PREFERENCE["desk"] = ("people", "team", "exterior", "room")
HERO_PREFERENCE["retail"] = ("product", "room", "detail", "exterior", "people")
HERO_PREFERENCE["food"] = ("dish", "room", "drink", "detail", "people",
                           "exterior")

# Never the lead image, for different reasons: a wordmark is not a photograph,
# an award badge belongs in the recognition band at size, raw produce does not
# make anyone want dinner, and "can't tell" is the operator saying so.
NEVER_LEADS = ("logo", "award", "ingredients", "unclear")

# Not a veto, and this is the difference that matters. `tag_for` returns
# "other" for any description it cannot categorise, so a perfectly good
# photograph described in words the phrase table does not know was silently
# made ineligible to lead. A weak signal must not act as a veto — the same
# mistake as letting any label outrank measured quality.
WEAK_LEADS = ("other",)


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def label(conn: sqlite3.Connection, lead_id: int, url: str,
          description: str, what: str | None = None,
          actor: str | None = None) -> None:
    """Record what a photograph shows.

    `description` is what you wrote and is kept verbatim — it becomes the alt
    text on the finished page, which is worth as much as the placement. `what`
    overrides the derived tag when the parse gets it wrong.
    """
    text = (description or "").strip()
    tag = what or tag_for(text)
    if tag not in LABELS:
        raise ValueError(f"unknown label {tag!r} — one of {', '.join(LABELS)}")
    if not text and not what:
        raise ValueError("describe the photograph, or pick a category")
    if tag == SKIPPED:
        # Marked unclear on purpose. Any words written before that stand as a
        # note, but they must not become alt text claiming to describe it.
        text = ""
    conn.execute(
        "INSERT INTO photo_labels (lead_id, url, label, description, actor, at)"
        " VALUES (?,?,?,?,?,?)"
        " ON CONFLICT(lead_id, url) DO UPDATE SET label=excluded.label,"
        " description=excluded.description, actor=excluded.actor, at=excluded.at",
        (lead_id, url, tag, text, actor or operator(), _now()))


def record_vision(conn: sqlite3.Connection, lead_id: int, url: str,
                  seen: dict) -> bool:
    """What the vision pass saw about one photograph.

    Never overwrites a person. The operator's judgement outranks the machine's
    — that is in the requirements, not a preference — so a row already written
    by anyone other than the vision pass is left exactly as it is, and this
    returns False to say so.
    """
    row = conn.execute(
        "SELECT actor FROM photo_labels WHERE lead_id = ? AND url = ?",
        (lead_id, url)).fetchone()
    if row is not None and row["actor"] != MACHINE_ACTOR:
        return False
    tag = str(seen.get("subject") or "other")
    if tag not in LABELS:
        tag = "other"
    conn.execute(
        "INSERT INTO photo_labels"
        " (lead_id, url, label, description, actor, at, vision_json)"
        " VALUES (?,?,?,?,?,?,?)"
        " ON CONFLICT(lead_id, url) DO UPDATE SET label=excluded.label,"
        " description=excluded.description, actor=excluded.actor,"
        " at=excluded.at, vision_json=excluded.vision_json",
        (lead_id, url, tag, str(seen.get("alt_text") or ""), MACHINE_ACTOR,
         _now(), json.dumps(seen, sort_keys=True)))
    return True


def vision_for(conn: sqlite3.Connection, lead_id: int) -> dict[str, dict]:
    """Everything the vision pass recorded, by photograph URL."""
    out: dict[str, dict] = {}
    for row in conn.execute(
            "SELECT url, vision_json FROM photo_labels WHERE lead_id = ?",
            (lead_id,)):
        try:
            seen = json.loads(row["vision_json"] or "{}")
        except json.JSONDecodeError:
            seen = {}
        if seen:
            out[row["url"]] = seen
    return out


def labels_for(conn: sqlite3.Connection, lead_id: int) -> dict[str, str]:
    rows = conn.execute("SELECT url, label FROM photo_labels WHERE lead_id = ?",
                        (lead_id,))
    return {row["url"]: row["label"] for row in rows}


def described(conn: sqlite3.Connection, lead_id: int) -> dict[str, dict]:
    """Everything said about each photograph: the tag, the words, and who said
    them — so the screen can invite correction of a machine guess without
    pretending a person made it."""
    rows = conn.execute(
        "SELECT url, label, description, actor, vision_json"
        " FROM photo_labels WHERE lead_id = ?", (lead_id,))
    out: dict[str, dict] = {}
    for row in rows:
        try:
            seen = json.loads(row["vision_json"] or "{}")
        except json.JSONDecodeError:
            seen = {}
        out[row["url"]] = {
            "label": row["label"], "description": row["description"] or "",
            "actor": row["actor"], "by_machine": row["actor"] == MACHINE_ACTOR,
            "quality": seen.get("quality"), "why_not": seen.get("why_not", ""),
        }
    return out


def unreviewed(conn: sqlite3.Connection, lead_id: int, urls: list[str],
               *, by_person: bool = False) -> list[str]:
    """Photographs nothing has made a decision about yet.

    A decision includes "unclear", and — since the vision pass — it includes a
    machine label. That is the difference between waiting for thirty
    hand-typed descriptions per lead and opening on a site that has already
    looked at the pictures. The screen still shows every guess for correction,
    and the operator's answer replaces it and stays attributed.

    `by_person` asks the stricter question, for the keyless path where no
    machine label will ever arrive.
    """
    rows = conn.execute(
        "SELECT url, actor FROM photo_labels WHERE lead_id = ?", (lead_id,))
    decided = {row["url"] for row in rows
               if not by_person or row["actor"] != MACHINE_ACTOR}
    return [url for url in urls if url not in decided]


def rank_for_hero(urls: list[str], labels: dict[str, str],
                  trade: str = "default") -> list[str]:
    """Candidates, best lead first. Unlabelled photographs keep their order.

    Unlabelled is not the same as unsuitable: a business nobody has labelled
    should still get its original ordering rather than an empty page.
    """
    preference = HERO_PREFERENCE.get(trade, HERO_PREFERENCE["default"])
    def rank(url: str) -> tuple[int, int]:
        what = labels.get(url)
        if what is None:
            return (1, urls.index(url))          # after labelled, in page order
        if what in NEVER_LEADS:
            return (2, urls.index(url))          # never a lead if we know better
        return (0, preference.index(what) if what in preference else len(preference))
    return sorted(urls, key=rank)


# Words that are noise in a filename rather than a description of the picture.
_FILENAME_NOISE = frozenset({
    "jpg", "jpeg", "png", "webp", "gif", "scaled", "final", "copy", "edit",
    "photo", "image", "img", "dsc", "mg", "web", "small", "large", "wide",
    "crop", "new", "site", "home", "resized", "compressed", "min", "full",
})


def suggest_from_url(url: str) -> str:
    """A description read out of the filename, or "" when it says nothing.

    Their own uploads are often named after what they show — Short-Rib.jpg,
    housemade-bread.jpg — so those can be filled in without anyone squinting at
    a thumbnail. A proxied Google photo has an opaque URL and gets nothing,
    which is the honest answer rather than a guess.
    """
    stem = url.rsplit("/", 1)[-1].rsplit(".", 1)[0]
    words = [w for w in re.split(r"[-_.\s]+", stem.lower())
             if w and not w.isdigit() and w not in _FILENAME_NOISE
             and not re.fullmatch(r"\d+x\d+", w) and len(w) > 2]
    if not words:
        return ""
    return " ".join(words)


def suggest_all(urls: list[str]) -> dict[str, str]:
    """Descriptions we can read off the filenames. Silent about the rest."""
    return {url: text for url in urls if (text := suggest_from_url(url))}
