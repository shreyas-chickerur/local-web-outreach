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
          "logo", "other")

# How well each label works as a hero, per kind of business. A roofer's hero is
# finished work; a restaurant's is a plate or the room.
HERO_PREFERENCE: dict[str, tuple[str, ...]] = {
    "food": ("dish", "room", "drink", "people", "exterior"),
    "trade": ("exterior", "people", "room", "dish"),
    "default": ("room", "exterior", "people", "dish"),
}


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def label(conn: sqlite3.Connection, lead_id: int, url: str, what: str,
          actor: str | None = None) -> None:
    if what not in LABELS:
        raise ValueError(f"unknown label {what!r} — one of {', '.join(LABELS)}")
    conn.execute(
        "INSERT INTO photo_labels (lead_id, url, label, actor, at)"
        " VALUES (?,?,?,?,?)"
        " ON CONFLICT(lead_id, url) DO UPDATE SET label=excluded.label,"
        " actor=excluded.actor, at=excluded.at",
        (lead_id, url, what, actor or operator(), _now()))


def labels_for(conn: sqlite3.Connection, lead_id: int) -> dict[str, str]:
    rows = conn.execute("SELECT url, label FROM photo_labels WHERE lead_id = ?",
                        (lead_id,))
    return {row["url"]: row["label"] for row in rows}


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
        if what in ("logo", "other", "ingredients"):
            return (2, urls.index(url))          # never a lead if we know better
        return (0, preference.index(what) if what in preference else len(preference))
    return sorted(urls, key=rank)
