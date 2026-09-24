"""The layout probe the tests share: the platform's own check, at the tests' window sizes.

The probe lives in `app.review.layout`, where the claim review runs it on every
version; the tests measure with the same code rather than a copy of it.
"""

from __future__ import annotations

from app.review.layout import chrome, link_photographs, measure

__all__ = ["WIDTHS", "chrome", "link_photographs", "measure"]

# (label, width, height): the widths a design review is read at.
WIDTHS = (("desktop", 1440, 1100), ("mobile", 390, 844), ("page", 1440, 6000))
