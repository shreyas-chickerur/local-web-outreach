"""A proposal an owner can open before anything is hosted.

Shreyas shows a restaurant its site before paying for hosting. The versions in
the workbench name photographs and the logo by `/photo/<lead>/<n>` and
`/logo/<lead>`, addresses that exist only while the workbench runs on his
machine: sent as they are, an owner sees broken images. This writes the
current version as one file with every one of them carried inside it, which
opens offline on a phone or a laptop and can go as an email attachment.

The review layer never appears in it: that is injected at serve time for a
`?review=` link, and a stored version carries none.
"""

from __future__ import annotations

import base64
import re
import sqlite3
from pathlib import Path

from app.adapters import logos, photos
from app.core.config import google_places_api_key
from app.store import brief_archive, leads, sites

OUT = Path("proposals")


def _inline(data: bytes, media_type: str) -> str:
    return f"data:{media_type};base64,{base64.b64encode(data).decode()}"


def export(conn: sqlite3.Connection, lead_id: int, version: int | None = None) -> Path:
    """Write the version (the newest by default) as one self-contained file."""
    brief = leads.brief_with_overrides(conn, lead_id)
    version = version or max(v["version"] for v in sites.versions(conn, lead_id))
    html = sites.html_for(conn, lead_id, version) or ""
    names = brief.get("place_photos") or []
    key = google_places_api_key() or ""

    def photo(match: re.Match) -> str:
        n = int(match.group(1))
        data = photos.fetch(key, names[n], width=1600) if n < len(names) else None
        if not data:
            raise ValueError(f"photograph {n} could not be had; the proposal would show it broken")
        return _inline(data, "image/jpeg")

    html = re.sub(rf"/photo/{lead_id}/(\d+)(?:\?w=\d+)?", photo, html)
    if f"/logo/{lead_id}" in html:
        url = (brief.get("published") or {}).get("logo")
        logo = logos.fetch(str(url)) if url else None
        if logo is None:
            raise ValueError("the page shows a logo that could not be had")
        html = html.replace(f"/logo/{lead_id}", _inline(*logo))
    if "annotate.js" in html or "?review=" in html:
        raise ValueError("this version carries review markup and must never be sent")
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{brief_archive._slug(str(brief['name']))}-v{version}.html"
    path.write_text(html)
    return path


if __name__ == "__main__":
    import sys

    from app.store import db

    with db.session() as connection:
        written = export(connection, int(sys.argv[1]),
                         int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2] else None)
    print(f"{written} ({written.stat().st_size / 1_000_000:.1f} MB), open it or attach it")
