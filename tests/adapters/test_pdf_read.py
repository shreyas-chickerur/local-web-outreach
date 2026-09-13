"""Reading a PDF's own text — the single biggest cause of an empty
`menu_items` list for a restaurant whose real menu lives at
`.../menu.pdf`, per Round 7's own diagnosis (`extract.py` used to
discard every PDF as "media, not a page")."""

from __future__ import annotations

import pytest

from app.adapters.pdf_read import read_pdf_text

pytestmark = pytest.mark.unit


def _pdf_bytes(text: str) -> bytes:
    """A minimal, real, parseable single-page PDF whose only content is
    `text` — built by hand rather than downloaded, so this test is
    hermetic and needs no network."""
    stream = f"BT /F1 18 Tf 20 100 Td ({text}) Tj ET".encode()
    return (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/Parent 2 0 R/Resources<</Font<</F1 4 0 R>>>>"
        b"/MediaBox[0 0 400 200]/Contents 5 0 R>>endobj\n"
        b"4 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
        b"5 0 obj<</Length " + str(len(stream)).encode() + b">>\nstream\n"
        + stream + b"\nendstream\nendobj\n"
        b"xref\n0 6\n0000000000 65535 f \n"
        b"trailer<</Size 6/Root 1 0 R>>\nstartxref\n0\n%%EOF")


def test_a_real_pdfs_own_text_is_read():
    data = _pdf_bytes(r"Brisket Plate \$18")
    text = read_pdf_text(data)
    assert text is not None
    assert "Brisket Plate" in text and "18" in text


def test_bytes_that_are_not_a_pdf_at_all_are_unreadable_not_empty():
    """A 404 page served with a `.pdf` extension (a stale link) must not
    read as "the business has no menu" — it is a fetch that produced
    garbage, and the caller needs to tell the two apart."""
    assert read_pdf_text(b"<html><body>404 not found</body></html>") is None


def test_empty_bytes_are_unreadable():
    assert read_pdf_text(b"") is None


def test_a_pdf_with_no_text_layer_is_unreadable_not_an_empty_menu():
    """A scanned/image-only PDF has a valid structure but no text object at
    all — the honest answer is `None` ("could not read this"), never a
    silent empty string treated as "no menu"."""
    data = (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/Parent 2 0 R/Resources<<>>"
        b"/MediaBox[0 0 400 200]/Contents 5 0 R>>endobj\n"
        b"5 0 obj<</Length 0>>\nstream\n\nendstream\nendobj\n"
        b"trailer<</Size 6/Root 1 0 R>>\n%%EOF")
    assert read_pdf_text(data) is None
