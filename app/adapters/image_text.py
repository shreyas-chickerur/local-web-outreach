"""Reading a menu that a business publishes only as an image.

The Heritage Table's wine list is a photograph of a printed page. Nothing else
in the crawl can read it, so every wine on the generated page came back
unsourced. A model can read it, and that costs a call, so each image is read
once: the answer is kept on disk under a fingerprint of the image's bytes, and
a re-crawl of an unchanged menu, or the same file uploaded under a new name,
costs nothing.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from app.adapters import language_model

CACHE = Path(".cache/image-text")

_SYSTEM = ("You transcribe restaurant menus, drink lists and price lists from "
           "photographs. You copy what is printed, exactly, and add nothing.")
_PROMPT = ("Transcribe every word and price printed in this image, line by line, "
           "in reading order, exactly as printed. Do not describe the image, do not "
           "summarise, do not correct spelling. If the text cannot be read, say so.")
_TOOL = {
    "name": "transcription",
    "description": "What is printed in the image.",
    "input_schema": {
        "type": "object",
        "properties": {
            "legible": {"type": "boolean",
                        "description": "Whether the printed text could be read."},
            "text": {"type": "string",
                     "description": "Every printed line, in reading order, verbatim."},
        },
        "required": ["legible", "text"],
    },
}


def media_type_of(data: bytes) -> str:
    """What the bytes are, whatever the address says. Every image used to be
    sent as a JPEG, and the API refused The Heritage Table's PNG drinks list."""
    if data.startswith(b"\x89PNG"):
        return "image/png"
    if data.startswith(b"GIF8"):
        return "image/gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return "image/jpeg"


def read(data: bytes, media_type: str | None = None) -> tuple[str | None, str]:
    """The text printed in an image, or `None` and the reason it was not read."""
    media_type = media_type or media_type_of(data)
    key = hashlib.sha256(data).hexdigest()
    cached = CACHE / f"{key}.json"
    if cached.exists():
        stored = json.loads(cached.read_text())
        return stored["text"] or None, stored["reason"]
    if not language_model.available():
        # Not cached: once a key is set the same image should be read.
        return None, "no Anthropic key configured"
    try:
        answer = language_model.structured(_SYSTEM, _PROMPT, _TOOL, max_tokens=4096,
                                   timeout=90.0,
                                   blocks=[language_model.image_block(data, media_type)])
    except language_model.ModelError as exc:
        # A refusal or a timeout is not an answer about the image; try again next crawl.
        return None, f"the model call failed ({exc})"
    text = str(answer.get("text") or "").strip()
    result = ((text, "") if answer.get("legible") and text
              else (None, "the model could not read it"))
    CACHE.mkdir(parents=True, exist_ok=True)
    cached.write_text(json.dumps({"text": result[0] or "", "reason": result[1]}))
    return result
