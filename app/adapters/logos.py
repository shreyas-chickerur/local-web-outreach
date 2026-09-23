"""A business's logo: downloaded once, kept, and handed to the workbench.

Every page view asks the workbench for `/logo/<lead>`; the business's own
server should be asked once. The type is read from the bytes, because Fish
Shack's logo is a JPEG and The Heritage Table's a PNG, and an address does
not always say which.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from app.adapters.image_text import media_type_of
from app.adapters.site_fetch import download

CACHE = Path(".cache/logos")


def fetch(url: str) -> tuple[bytes, str] | None:
    """The logo's bytes and media type, or `None` if it cannot be had."""
    cached = CACHE / hashlib.sha256(url.encode()).hexdigest()[:32]
    if cached.exists():
        kept = cached.read_bytes()
        return kept, media_type_of(kept)
    fresh, _why = download(url)
    if not fresh:
        return None
    CACHE.mkdir(parents=True, exist_ok=True)
    cached.write_bytes(fresh)
    return fresh, media_type_of(fresh)
