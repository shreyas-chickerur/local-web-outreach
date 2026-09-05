"""Turning a sentence into changes to a site's configuration.

An iteration is a *delta*: "make it more rustic and move the gallery up" has to
leave everything else exactly as it was, which is why this takes the current
spec and returns a new one rather than parsing a page's worth of intent from
scratch each time.

The matching is a longest-phrase-first pass over a consumed token stream. Three
properties make it deterministic, which the generator's guarantee depends on:

* rules live in ordered tuples, so iteration order is source order — never a
  dict's insertion order or a set's hash order;
* longer phrases match first, so "book a table" beats "book" and "day spa" is
  never split into "day" and "spa";
* every match consumes its tokens, so what is left over IS the residue — the
  ignored list is a by-product of matching rather than a second guess at it.

What it cannot do is understand. "Make the specials the star" will land in
`ignored_tokens`, and that is the right outcome: visibly ignored beats
silently misread.
"""

from __future__ import annotations

import re

# The configuration an iteration edits. Anything not mentioned carries forward.
DEFAULT_SPEC: dict = {
    "mood": "fresh",
    "hero_offset": 0,
    "lead_with": None,
    "emphasis": [],
    "suppress": [],
    "cta": None,
    "accent": None,
}

# (phrase, accent name). Colour is the thing people say first about a page, so
# not having it here meant the commonest instruction there is landed in
# `ignored_tokens` and produced a version identical to its parent.
#
# Two-word phrases sit here rather than in MOOD_PHRASES because "dark blue" is
# a colour, not a mood plus a colour — and this table is matched first so the
# mood pass never gets to split it.
COLOUR_PHRASES: tuple[tuple[str, str], ...] = (
    ("navy blue", "navy"), ("dark blue", "navy"), ("midnight blue", "navy"),
    ("sky blue", "sky"), ("light blue", "sky"), ("pale blue", "sky"),
    ("royal blue", "blue"), ("navy", "navy"), ("blue", "blue"),
    ("cobalt", "blue"), ("azure", "sky"),
    ("forest green", "forest"), ("dark green", "forest"),
    ("olive green", "olive"), ("sage green", "sage"), ("mint green", "mint"),
    ("emerald", "forest"), ("forest", "forest"), ("olive", "olive"),
    ("sage", "sage"), ("mint", "mint"), ("green", "green"),
    ("teal", "teal"), ("turquoise", "teal"), ("aqua", "teal"),
    ("burnt orange", "terracotta"), ("terracotta", "terracotta"),
    ("rust", "terracotta"), ("orange", "orange"), ("amber", "amber"),
    ("mustard", "mustard"), ("gold", "gold"), ("golden", "gold"),
    ("yellow", "yellow"),
    ("burgundy", "burgundy"), ("maroon", "burgundy"), ("wine", "burgundy"),
    ("crimson", "crimson"), ("scarlet", "crimson"), ("red", "red"),
    ("dusty rose", "rose"), ("rose", "rose"), ("pink", "pink"),
    ("blush", "pink"),
    ("indigo", "indigo"), ("violet", "violet"), ("purple", "purple"),
    ("lilac", "violet"), ("plum", "plum"), ("aubergine", "plum"),
    ("brown", "brown"), ("chocolate", "brown"),
    ("charcoal", "charcoal"), ("grey", "grey"), ("gray", "grey"),
    ("greyscale", "grey"), ("monochrome", "grey"),
)

MOODS = ("warm", "fresh", "bold", "refined", "industrial", "night")

# (phrase, mood). Ordered longest-first within each mood so a two-word phrase
# is tried before either of its halves.
MOOD_PHRASES: tuple[tuple[str, str], ...] = (
    ("farm house", "warm"), ("warmer", "warm"), ("warm", "warm"),
    ("rustic", "warm"),
    ("cosy", "warm"), ("cozy", "warm"), ("homely", "warm"),
    ("welcoming", "warm"), ("farmhouse", "warm"), ("comfort", "warm"),
    ("family", "warm"), ("earthy", "warm"),
    ("cleaner", "fresh"), ("clean", "fresh"), ("minimal", "fresh"),
    ("simpler", "fresh"), ("modern", "fresh"),
    ("fresh", "fresh"), ("simple", "fresh"), ("airy", "fresh"),
    ("bright", "fresh"), ("light", "fresh"), ("calm", "fresh"),
    ("bolder", "bold"), ("bold", "bold"), ("louder", "bold"), ("loud", "bold"),
    ("punchy", "bold"),
    ("vibrant", "bold"), ("energetic", "bold"), ("playful", "bold"),
    ("fun", "bold"),
    ("upscale", "refined"), ("elegant", "refined"), ("refined", "refined"),
    ("premium", "refined"), ("luxury", "refined"), ("classy", "refined"),
    ("sophisticated", "refined"), ("fine dining", "refined"),
    ("industrial", "industrial"), ("urban", "industrial"),
    ("raw", "industrial"), ("workshop", "industrial"),
    ("rugged", "industrial"), ("concrete", "industrial"),
    ("darker", "night"), ("dark", "night"), ("moodier", "night"),
    ("moody", "night"), ("night", "night"),
    ("speakeasy", "night"), ("lounge", "night"), ("izakaya", "night"),
)

SECTION_PHRASES: tuple[tuple[str, str], ...] = (
    ("what we do", "services"), ("our services", "services"),
    ("services", "services"), ("offerings", "services"), ("offers", "services"),
    ("menu", "menu"), ("dishes", "menu"), ("food", "menu"), ("prices", "menu"),
    ("pricing", "menu"),
    ("gallery", "gallery"), ("photos", "gallery"), ("pictures", "gallery"),
    ("images", "gallery"),
    ("reviews", "reviews"), ("testimonials", "reviews"), ("quotes", "reviews"),
    ("about section", "about"), ("about us", "about"), ("our story", "about"),
    ("story", "about"),
    ("hours", "hours"), ("opening times", "hours"), ("times", "hours"),
    ("contact", "contact"), ("directions", "contact"), ("map", "contact"),
    ("find us", "contact"),
    ("stats", "stats"), ("numbers", "stats"),
)

# (phrase, cta key, button label)
CTA_PHRASES: tuple[tuple[str, str, str], ...] = (
    ("book a table", "book", "Book a table"),
    ("book a room", "book", "Book a room"),
    ("make a booking", "book", "Book now"),
    ("reservation", "book", "Reserve a table"),
    ("reserve", "book", "Reserve a table"),
    ("booking", "book", "Book now"),
    ("book", "book", "Book now"),
    ("order online", "order", "Order online"),
    ("takeaway", "order", "Order online"),
    ("takeout", "order", "Order online"),
    ("delivery", "order", "Order online"),
    ("order", "order", "Order online"),
    ("get a quote", "quote", "Get a quote"),
    ("free estimate", "quote", "Get a free estimate"),
    ("estimate", "quote", "Get an estimate"),
    ("quote", "quote", "Get a quote"),
    ("call us", "call", "Call us"),
    ("phone", "call", "Call us"),
    ("call", "call", "Call us"),
    ("directions", "visit", "Find us"),
    ("visit", "visit", "Find us"),
)

# Intent markers. A section name alone says nothing about what to do with it:
# "move the gallery up" and "remove the gallery" differ only here.
HOIST_BEFORE = ("lead with", "start with", "open with", "begin with",
                "move", "put", "promote", "raise", "hoist")
HOIST_AFTER = ("first", "at the top", "up top", "to the top", "on top", "up")
DROP_BEFORE = ("remove", "drop", "delete", "hide", "lose", "cut", "kill",
               "without", "no", "take out", "get rid of")

# How far from a section name an intent word still counts as attached to it.
INTENT_WINDOW = 3

_WORD_RE = re.compile(r"[a-z][a-z'&-]*")

# Words that carry no instruction. Left out of `ignored_tokens` so the operator
# sees the words that actually went unused, not the grammar around them.
_FILLER = frozenset("""
a an the and or but so then also just very really quite bit more less much
make made makes making it its this that these those them they their there here
please can could would should want wants need needs like feel feels look looks
looking site website page pages design designed style styled version thing
things something anything for with from into onto about around out up down
some any all our your my me we i you is are was be been being have has had do
does did to of on in at as by
top bottom above below first last next order section sections put move show
give add keep use try let actually maybe perhaps still even bring back
""".split())


def _tokens(sentence: str) -> list[str]:
    return _WORD_RE.findall(sentence.lower())


def _find_phrases(tokens: list[str], used: list[bool],
                  table: tuple[tuple[str, ...], ...]) -> list[tuple[int, tuple]]:
    """Every match of `table` in `tokens`, longest phrases first.

    Returns (index, row) pairs in source order. Marks the tokens it matched as
    consumed, so a later, shorter rule cannot claim them again.
    """
    by_length: dict[int, list[tuple[str, ...]]] = {}
    for row in table:
        by_length.setdefault(len(row[0].split()), []).append(row)

    found: list[tuple[int, tuple]] = []
    for length in sorted(by_length, reverse=True):
        for row in by_length[length]:
            words = row[0].split()
            for start in range(len(tokens) - length + 1):
                if any(used[start:start + length]):
                    continue
                if tokens[start:start + length] == words:
                    for offset in range(length):
                        used[start + offset] = True
                    found.append((start, row))
    return sorted(found, key=lambda pair: pair[0])


def _marker_near(tokens: list[str], used: list[bool], index: int,
                 markers: tuple[str, ...], *, before: bool) -> str | None:
    """The nearest intent marker attached to the section named at `index`.

    Consumes what it matches. An intent word that was acted on is not an
    ignored word, and reporting "remove" as unused after honouring it would be
    worse than saying nothing.
    """
    for marker in markers:
        words = marker.split()
        span = range(max(0, index - INTENT_WINDOW - len(words)), index) if before \
            else range(index + 1, min(len(tokens), index + 1 + INTENT_WINDOW))
        for start in span:
            if tokens[start:start + len(words)] == words:
                for offset in range(len(words)):
                    if start + offset < len(used):
                        used[start + offset] = True
                return marker
    return None


def parse_iteration_instruction(sentence: str, current_spec: dict) -> dict:
    """Apply one sentence to the current configuration.

    Returns a NEW spec — `current_spec` is never mutated, because a version's
    stored configuration has to stay exactly what produced it.
    """
    spec: dict = {**DEFAULT_SPEC, **(current_spec or {})}
    spec["emphasis"] = list(spec.get("emphasis") or [])
    spec["suppress"] = list(spec.get("suppress") or [])

    understood: list[str] = []
    contradictions: list[str] = []
    tokens = _tokens(sentence)
    used = [False] * len(tokens)

    # --- accent colour: before mood, so "dark blue" is not read as "dark" ----
    for _, (_, colour) in _find_phrases(tokens, used, COLOUR_PHRASES):
        spec["accent"] = colour
        understood.append(f"accented {colour}")
        break

    # --- mood: first in source order wins, and a conflict is said out loud --
    moods = _find_phrases(tokens, used, MOOD_PHRASES)
    chosen: str | None = None
    for _, (phrase, mood) in moods:
        if chosen is None:
            chosen, spec["mood"] = mood, mood
            understood.append(f"styled {mood}")
        elif mood != chosen:
            contradictions.append(
                f"“{phrase}” asks for {mood}, but “{moods[0][1][0]}” came first "
                f"— kept {chosen}")

    # --- call to action ----------------------------------------------------
    for _, (_, key, label) in _find_phrases(tokens, used, CTA_PHRASES):
        spec["cta"] = {"kind": key, "label": label}
        understood.append(f"a “{label}” call to action")
        break

    # --- back to the best lead photograph ----------------------------------
    # Labelling a photo is a more precise instruction than "show me another
    # one", so there has to be a way back to the top of the ranking.
    if re.search(r"(first|best|original|default)\s+(the\s+)?"
                 r"(hero|lead|main|cover)\s*(photo|image|picture|shot)?"
                 r"|(hero|lead)\s*(photo|image)?\s*back", sentence, re.IGNORECASE):
        spec["hero_offset"] = 0
        understood.append("back to the best lead photograph")
        for index, token in enumerate(tokens):
            if token in {"first", "best", "original", "default", "hero", "lead",
                         "main", "cover", "photo", "image", "picture", "back"}:
                used[index] = True

    # --- a different lead photograph --------------------------------------
    # Subject matter is the one thing nothing here can judge, so the operator
    # gets a one-phrase way to move past a picture they do not like.
    if spec.get("hero_offset") == 0 and understood[-1:] == [
            "back to the best lead photograph"]:
        pass                        # already handled just above
    elif re.search(r"(different|another|change|new|next)\s+(the\s+)?"
                 r"(hero|lead|main|top|first|cover)\s*(photo|image|picture|shot)?",
                 sentence, re.IGNORECASE) or re.search(
                     r"(hero|lead|cover)\s*(photo|image|picture|shot)\s*"
                     r"(is|looks)?\s*(bad|wrong|awful|boring|ugly)",
                     sentence, re.IGNORECASE):
        spec["hero_offset"] = int(spec.get("hero_offset") or 0) + 1
        understood.append("changed the lead photograph")
        for index, token in enumerate(tokens):
            if token in {"hero", "lead", "cover", "photo", "image", "picture",
                         "different", "another", "change", "next", "main",
                         "shot", "first", "top"}:
                used[index] = True

    # --- sections: the verb around the name decides what happens to it ------
    for index, (phrase, section) in _find_phrases(tokens, used, SECTION_PHRASES):
        if _marker_near(tokens, used, index, DROP_BEFORE, before=True):
            if section not in spec["suppress"]:
                spec["suppress"].append(section)
            spec["emphasis"] = [s for s in spec["emphasis"] if s != section]
            if spec["lead_with"] == section:
                spec["lead_with"] = None
            understood.append(f"dropped the {section}")
            continue

        hoisted = (_marker_near(tokens, used, index, HOIST_BEFORE, before=True)
                   or _marker_near(tokens, used, index, HOIST_AFTER, before=False))
        spec["suppress"] = [s for s in spec["suppress"] if s != section]
        if hoisted:
            spec["lead_with"] = section
            understood.append(f"led with the {section}")
        elif section not in spec["emphasis"]:
            spec["emphasis"].append(section)
            understood.append(f"emphasised the {section}")
        _ = phrase

    # --- the residue is what we could not use ------------------------------
    ignored = sorted({
        token for token, spent in zip(tokens, used, strict=True)
        if not spent and token not in _FILLER and len(token) > 2
    })

    spec["understood"] = understood
    spec["contradictions"] = contradictions
    spec["ignored_tokens"] = ignored
    return spec
