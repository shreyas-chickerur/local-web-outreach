"""Google Place photos, fetched through us so the key stays here.

A photo URL from the Places API carries the API key. Putting that in a page we
hand to a business owner would publish the key to anyone who views source, so
the generated site asks this server for `/photo/<lead>/<n>` and the key never
leaves the machine.

Fetched bytes are cached on disk: photos do not change, and each request is
billed.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import httpx

CACHE = Path(".cache/photos")
# Google will serve the same photograph far larger than we were asking for:
# 1600px got a 1600x1200 file when 3200x2400 was available for the same call.
# A hero at 1600 on a retina laptop is visibly soft, and that was the whole of
# the "low resolution" problem — nothing needed upscaling, we needed to ask.
MAX_WIDTH = 2400
WIDTHS = (800, 1600, 2400, 3200)


def nearest_width(requested: int) -> int:
    """Clamp to a small set so the cache does not fill with near-duplicates."""
    for width in WIDTHS:
        if requested <= width:
            return width
    return WIDTHS[-1]


def _cache_path(name: str, width: int) -> Path:
    key = hashlib.sha256(f"{name}@{width}".encode()).hexdigest()[:32]
    return CACHE / f"{key}.jpg"


def fetch(api_key: str, photo_name: str, width: int = MAX_WIDTH,
          client: httpx.Client | None = None) -> bytes | None:
    """The image bytes, from disk if we have already paid for them."""
    if not api_key or not photo_name:
        return None
    cached = _cache_path(photo_name, width)
    if cached.exists():
        return cached.read_bytes()

    http = client or httpx.Client(timeout=20.0, follow_redirects=True)
    try:
        resp = http.get(
            f"https://places.googleapis.com/v1/{photo_name}/media",
            params={"maxWidthPx": str(width), "key": api_key})
        if resp.status_code != 200 or not resp.content:
            return None
    except httpx.HTTPError:
        return None

    CACHE.mkdir(parents=True, exist_ok=True)
    cached.write_bytes(resp.content)
    return resp.content
