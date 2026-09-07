"""Looking at the photographs.

Everything else in this system reasons about pictures without seeing them:
their shape, their file size, the words in their filename, and whatever the
operator typed. That is enough to rule out a portrait crop and not enough to
notice that the "hero" is a photograph of a menu, or that the sentence "Plan
your next event with us" is burned across it, or that the only face in the
frame sits exactly where the headline goes.

So one batched call per lead looks at them. What comes back is measurement, not
judgement about the business: what is in the picture, whether it is sharp,
where the subject sits, how bright the top-left is. The one exception is
`alt_text`, and it is allowed for a specific reason — it describes a
photograph, which is a thing anyone can check by looking, rather than
asserting something about the business, which is a thing only their own
sources can establish. It is gated anyway.

Batched because the alternative is thirty round trips per lead. Downscaled
because the API resizes anything past 1568px on the long edge regardless, so
sending a 2400px original is paying to have it thrown away — and Google will
serve the same photograph at 512 for the same call.
"""

from __future__ import annotations

import httpx

from app.adapters import claude, photos
from app.adapters.imageinfo import dimensions_of, media_type_of
from app.core import config
from app.core.claims import reads_as_claim
from app.store.photos import LABELS

# Small enough that a dozen fit in one request, large enough to read a sign.
THUMB_WIDTH = 512
BATCH = 8
# A batched call over eight photographs is not a twenty-second question.
TIMEOUT = 90.0

WHERE = ("left", "centre", "right", "full")
LUMINANCE = ("dark", "mixed", "bright")

SYSTEM = """\
You are looking at photographs belonging to one small business, to decide how
they can be used on a website. You are measuring them, not judging the
business.

For each image, in the order given, report what is actually visible. Do not
infer anything the picture does not show — not the cuisine, not the price
point, not how good the business is. If you cannot tell, say so through
`subject: unclear` and a low `quality`.

`alt_text` is one plain sentence describing what a person would see. It is the
only text of yours that reaches the page, and it must describe the photograph
and nothing else. "A plated fish dish with greens on a wooden table" is right.
"Chef Marco's award-winning signature dish" is not: it asserts things the
photograph cannot establish.

`headline_region_luminance` describes the top-left third of the image, where
the page will put white or dark type over it.

`dominant_colours` are up to four hex values actually present in the image,
strongest first.
"""


def _tool(count: int) -> dict:
    return {
        "name": "describe",
        "description": f"What is visible in each of the {count} images.",
        "input_schema": {
            "type": "object",
            "properties": {
                "images": {
                    "type": "array",
                    "description": "One entry per image, in the order given.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "index": {"type": "integer"},
                            "subject": {"type": "string",
                                        "enum": list(LABELS)},
                            "is_hero_candidate": {"type": "boolean"},
                            "why_not": {
                                "type": "string",
                                "description": "A few words, only when "
                                               "is_hero_candidate is false."},
                            "has_text_overlay": {"type": "boolean"},
                            "is_logo_or_badge": {"type": "boolean"},
                            "is_screenshot_or_document": {"type": "boolean"},
                            "quality": {
                                "type": "integer",
                                "description": "1 to 5: focus, exposure and "
                                               "composition. Not taste.",
                            },
                            "subject_position": {"type": "string",
                                                 "enum": list(WHERE)},
                            "headline_region_luminance": {
                                "type": "string", "enum": list(LUMINANCE)},
                            "dominant_colours": {
                                "type": "array",
                                "items": {"type": "string"}},
                            "alt_text": {"type": "string"},
                        },
                        "required": ["index", "subject", "is_hero_candidate",
                                     "quality", "alt_text"],
                    },
                },
            },
            "required": ["images"],
        },
    }


def thumbnail(url: str, place_photos: tuple[str, ...]) -> bytes | None:
    """The bytes to send for one photograph, small.

    A proxied `/photo/<lead>/<n>` is re-fetched from Google at the thumbnail
    width, which costs nothing extra and is cached like every other width.
    Anything scraped from their own site is sent as it came, and skipped when
    it is too large to send — checked here rather than discovered in
    production.
    """
    if url.startswith("/photo/"):
        index = url.rsplit("/", 1)[-1].split("?")[0]
        if not index.isdigit() or int(index) >= len(place_photos):
            return None
        return photos.fetch(config.google_places_api_key() or "",
                            place_photos[int(index)], width=THUMB_WIDTH)
    try:
        response = httpx.get(url, timeout=15.0, follow_redirects=True)
    except httpx.HTTPError:
        return None
    if response.status_code != 200 or not response.content:
        return None
    data = response.content
    if len(data) > claude.MAX_IMAGE_BYTES:
        return None
    size = dimensions_of(data)
    if size and max(size) > claude.MAX_IMAGE_EDGE * 2:
        # The API resizes past 1568px anyway; well beyond that we are paying to
        # upload pixels that are discarded before the model sees them.
        return None
    return data


def _clean(entry: dict, url: str) -> dict:
    """One answer, validated. Nothing here is trusted because it came back."""
    def flag(name: str) -> bool:
        return bool(entry.get(name)) is True

    subject = entry.get("subject")
    if subject not in LABELS:
        subject = "unclear"
    quality = entry.get("quality")
    quality = quality if isinstance(quality, int) and 1 <= quality <= 5 else 1
    where = entry.get("subject_position")
    luminance = entry.get("headline_region_luminance")
    colours = [c for c in (entry.get("dominant_colours") or [])
               if isinstance(c, str) and _is_hex(c)][:4]
    alt = entry.get("alt_text")
    alt = alt.strip()[:200] if isinstance(alt, str) else ""
    # The one place model-written text reaches the page, so it is checked
    # against the same expression that guards every other sentence. A
    # description that has drifted into asserting something is dropped rather
    # than repaired: there is no safe way to edit a claim into a description.
    if reads_as_claim(alt):
        alt = ""
    why = entry.get("why_not")
    why = why.strip()[:120] if isinstance(why, str) else ""
    return {
        "url": url,
        "subject": subject,
        "is_hero_candidate": flag("is_hero_candidate"),
        "why_not": why,
        "has_text_overlay": flag("has_text_overlay"),
        "is_logo_or_badge": flag("is_logo_or_badge"),
        "is_screenshot_or_document": flag("is_screenshot_or_document"),
        "quality": quality,
        "subject_position": where if where in WHERE else "full",
        "headline_region_luminance": (luminance if luminance in LUMINANCE
                                      else "mixed"),
        "dominant_colours": colours,
        "alt_text": alt,
    }


def _is_hex(value: str) -> bool:
    text = value.strip().lstrip("#")
    return len(text) in (3, 6) and all(c in "0123456789abcdefABCDEF"
                                       for c in text)


def look(urls: list[str], place_photos: tuple[str, ...] = (),
         *, client: httpx.Client | None = None) -> dict[str, dict]:
    """What is in each photograph, keyed by URL.

    Raises nothing: a lead whose photographs cannot be looked at is a lead with
    fewer facts, not a broken build. Anything missing simply does not appear in
    the result, and every caller already handles an absent answer because the
    keyless path has always had to.
    """
    if not claude.available() or not urls:
        return {}
    seen: dict[str, dict] = {}
    for start in range(0, len(urls), BATCH):
        chunk = urls[start:start + BATCH]
        blocks: list[dict] = []
        sent: list[str] = []
        for url in chunk:
            data = thumbnail(url, place_photos)
            if not data:
                continue
            kind = media_type_of(data)
            if kind is None:
                # An AVIF, or something that is not an image at all. Sending it
                # under a guessed type fails the whole batch rather than that
                # one picture.
                continue
            blocks.append(claude.image_block(data, kind))
            sent.append(url)
        if not blocks:
            continue
        seen.update(_ask(sent, blocks, client))
    return seen


def _ask(sent: list[str], blocks: list[dict],
         client: httpx.Client | None) -> dict[str, dict]:
    """One batch, halved and retried if it fails.

    The API rejects the whole request when any single block is unusable, so an
    oversized or malformed image used to take every photograph beside it down
    with it — eighteen came back undescribed because of four. Splitting
    isolates the bad one and costs an extra call only when something is wrong.
    """
    if not sent:
        return {}
    listing = "\n".join(f"  image {i}: {u}" for i, u in enumerate(sent))
    try:
        answer = claude.structured(
            SYSTEM,
            f"{len(sent)} images, in this order:\n{listing}\n\n"
            f"Describe each one.",
            _tool(len(sent)), client=client, blocks=blocks,
            max_tokens=4096, timeout=TIMEOUT)
    except claude.ClaudeError:
        if len(sent) == 1:
            return {}
        half = len(sent) // 2
        return {**_ask(sent[:half], blocks[:half], client),
                **_ask(sent[half:], blocks[half:], client)}

    out: dict[str, dict] = {}
    for entry in answer.get("images") or []:
        # A schema is not a guarantee. The model returned bare strings in this
        # array for two of eleven fixtures, and an unguarded `.get` on one of
        # them took the whole lead down at the first stage.
        if not isinstance(entry, dict):
            continue
        index = entry.get("index")
        if not isinstance(index, int) or not 0 <= index < len(sent):
            continue
        out[sent[index]] = _clean(entry, sent[index])
    return out
