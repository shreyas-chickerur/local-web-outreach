"""A PDF's own text, so a menu or price list published as a PDF is content
this project can read, not a link it discards.

`extract.py` used to treat every PDF as "media, not a page" and drop it
outright — the single biggest cause of a thin brief for any restaurant
whose menu lives at `.../menu.pdf` rather than `.../menu/`. A PDF is not
markup, so it needs its own reader; `pypdf` is pure Python (no poppler, no
system library, no C extension), which matches the rest of this project's
own dependency-light stance.

A scanned or image-only PDF has no text layer at all — `pypdf` correctly
returns nothing for one, and that is reported here as `None` ("unreadable"),
never silently treated as "no menu". Optical character recognition would be
the honest next step for that case; it is out of scope for a small,
dependency-light reader and is not attempted — see `read_pdf_text`'s
docstring for exactly what this does and does not claim.
"""

from __future__ import annotations

import io

from pypdf import PdfReader
from pypdf.errors import PdfReadError


def read_pdf_text(data: bytes, max_pages: int = 40) -> str | None:
    """The PDF's own text, page by page, or `None` when there is none to
    read.

    `None` covers two different failures a caller must not conflate: the
    bytes are not a valid PDF at all (a broken link, an HTML error page
    served with a `.pdf` extension), and a genuinely valid PDF whose pages
    are scanned images with no extractable text layer. Both are
    "unreadable, not empty" — a caller should record that a PDF exists and
    could not be read, never treat either case as evidence the business
    has no menu.
    """
    if not data:
        return None
    try:
        reader = PdfReader(io.BytesIO(data))
        pages = [(page.extract_text() or "") for page in reader.pages[:max_pages]]
    except (PdfReadError, ValueError, KeyError, OSError):
        return None
    text = "\n".join(pages).strip()
    return text or None
