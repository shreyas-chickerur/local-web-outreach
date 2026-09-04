"""What a photograph shows, according to a person.

Shape is measurable and subject matter is not. A landscape shot of raw peppers
is the wrong lead for a fine dining room, and no amount of filename parsing
finds that out. Rather than guess, the operator labels a handful of candidates
once per lead and every later decision — the hero above all — uses those.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

from app.store.db import operator

# What a picture can be, ordered by how well it leads a page. The list is
# deliberately short: a longer one is slower to apply and no more useful.
LABELS = ("dish", "room", "exterior", "people", "drink", "ingredients",
          "award", "logo", "other")

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
    "food": ("dish", "room", "drink", "people", "exterior"),
    "trade": ("exterior", "people", "room", "dish"),
    "default": ("room", "exterior", "people", "dish"),
}

# Never the lead image, for different reasons: a wordmark is not a photograph,
# an award badge belongs in the recognition band at size, and raw produce does
# not make anyone want dinner.
NEVER_LEADS = ("logo", "award", "ingredients", "other")


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
    conn.execute(
        "INSERT INTO photo_labels (lead_id, url, label, description, actor, at)"
        " VALUES (?,?,?,?,?,?)"
        " ON CONFLICT(lead_id, url) DO UPDATE SET label=excluded.label,"
        " description=excluded.description, actor=excluded.actor, at=excluded.at",
        (lead_id, url, tag, text, actor or operator(), _now()))


def labels_for(conn: sqlite3.Connection, lead_id: int) -> dict[str, str]:
    rows = conn.execute("SELECT url, label FROM photo_labels WHERE lead_id = ?",
                        (lead_id,))
    return {row["url"]: row["label"] for row in rows}


def described(conn: sqlite3.Connection, lead_id: int) -> dict[str, dict]:
    """Everything said about each photograph: the tag and the words."""
    rows = conn.execute(
        "SELECT url, label, description FROM photo_labels WHERE lead_id = ?",
        (lead_id,))
    return {row["url"]: {"label": row["label"],
                         "description": row["description"] or ""} for row in rows}


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
