"""How big a picture is, without downloading the whole thing.

Choosing a hero without knowing the shape of the image is guesswork: a macro
close-up of raw peppers in portrait crop is the wrong lead for a restaurant no
matter how good the photograph is, and there is no way to tell from a URL.

Image formats put their dimensions in the first few bytes, so a ranged request
answers the question for about two kilobytes instead of two megabytes.
"""

from __future__ import annotations

import struct
from pathlib import Path

import httpx

CACHE = Path(".cache/imagesize")
HEAD_BYTES = 4096


def _png(data: bytes) -> tuple[int, int] | None:
    if data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        return None
    width, height = struct.unpack(">II", data[16:24])
    return int(width), int(height)


def _gif(data: bytes) -> tuple[int, int] | None:
    if data[:6] not in (b"GIF87a", b"GIF89a"):
        return None
    width, height = struct.unpack("<HH", data[6:10])
    return int(width), int(height)


def _webp(data: bytes) -> tuple[int, int] | None:
    if data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        return None
    chunk = data[12:16]
    if chunk == b"VP8X":
        width = int.from_bytes(data[24:27], "little") + 1
        height = int.from_bytes(data[27:30], "little") + 1
        return width, height
    if chunk == b"VP8 ":
        return (int.from_bytes(data[26:28], "little") & 0x3FFF,
                int.from_bytes(data[28:30], "little") & 0x3FFF)
    return None


def _jpeg(data: bytes) -> tuple[int, int] | None:
    if data[:2] != b"\xff\xd8":
        return None
    index = 2
    while index < len(data) - 9:
        if data[index] != 0xFF:
            index += 1
            continue
        marker = data[index + 1]
        # The frame headers are the ones carrying the dimensions.
        if marker in range(0xC0, 0xD0) and marker not in (0xC4, 0xC8, 0xCC):
            height, width = struct.unpack(">HH", data[index + 5:index + 9])
            return int(width), int(height)
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
            index += 2
            continue
        length = int.from_bytes(data[index + 2:index + 4], "big")
        if length <= 0:
            return None
        index += 2 + length
    return None


def dimensions_of(data: bytes) -> tuple[int, int] | None:
    for reader in (_png, _jpeg, _gif, _webp):
        size = reader(data)
        if size and all(size):
            return size
    return None


def measure(url: str, client: httpx.Client | None = None) -> tuple[int, int] | None:
    """(width, height), from a ranged request and cached on disk.

    Returns None when the server will not say — an unknown shape must not be
    mistaken for a bad one.
    """
    CACHE.mkdir(parents=True, exist_ok=True)
    key = CACHE / (str(abs(hash(url))) + ".txt")
    if key.exists():
        cached = key.read_text().strip()
        if cached == "?":
            return None
        width, _, height = cached.partition("x")
        return int(width), int(height)

    http = client or httpx.Client(timeout=8.0, follow_redirects=True)
    try:
        response = http.get(url, headers={"Range": f"bytes=0-{HEAD_BYTES}"})
        data = response.content if response.status_code in (200, 206) else b""
    except httpx.HTTPError:
        data = b""
    size = dimensions_of(data) if data else None
    key.write_text(f"{size[0]}x{size[1]}" if size else "?")
    return size
