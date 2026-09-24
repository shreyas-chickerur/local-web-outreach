"""How big a picture is, read from its own header bytes.

Image formats put their dimensions in the first few bytes. The crawl uses this
to tell a menu from an icon named like one: Yama's four "menus" were 230 by 136
pictures of sushi, and each was sent to a model to read.
"""

from __future__ import annotations

import struct


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


# What the vision API will accept. AVIF is not on the list, and a business that
# serves AVIF is not unusual any more.
MEDIA_TYPES: tuple[tuple[str, str], ...] = (
    ("image/jpeg", "jpeg"), ("image/png", "png"),
    ("image/gif", "gif"), ("image/webp", "webp"),
)


def dimensions_of(data: bytes) -> tuple[int, int] | None:
    """Width and height read from an image's own header bytes, or None if unrecognised."""
    for reader in (_png, _jpeg, _gif, _webp):
        size = reader(data)
        if size and all(size):
            return size
    return None
