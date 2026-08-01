"""CAN-SPAM compliance + suppression (invariant #4).

Every outreach email must carry a physical postal address and a working opt-out,
and must not use a deceptive subject. Recipients who opted out / complained /
bounced live on the suppression list and are never contacted again.
"""

from __future__ import annotations

import re

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.errors import ComplianceError
from app.models.suppression import SuppressionEntry

_OPT_OUT_MARKERS = ("unsubscribe", "opt out", "opt-out", "reply stop")


def build_footer(*, sender_name: str, postal_address: str) -> str:
    """A CAN-SPAM-compliant footer: sender identity + physical postal address +
    a one-step opt-out."""
    return (
        "\n\n—\n"
        f"{sender_name}\n"
        f"{postal_address}\n"
        "You're receiving this one-time note because your business is listed publicly. "
        "Reply UNSUBSCRIBE and we won't contact you again."
    )


# A sender address that still contains any of these is not a real address — it's
# the config default or the .env template stub. Chosen to never match a genuine
# street address.
_PLACEHOLDER_ADDRESS_MARKERS = (
    "example",
    "change me",
    "your real mailing address",
    "your mailing address",
    "placeholder",
    "todo",
)


def is_placeholder_address(postal_address: str) -> bool:
    """True if the sender's postal address is empty or an obvious placeholder."""
    a = (postal_address or "").strip().lower()
    if not a:
        return True
    return any(m in a for m in _PLACEHOLDER_ADDRESS_MARKERS)


def assert_real_sender_address(postal_address: str) -> None:
    """Hard send-time guard (invariant #4): refuse to send while the sender's
    postal address is empty or a placeholder. Every commercial email legally needs
    a real physical address (CAN-SPAM), so the Phase 7 send path MUST call this
    before dispatch. Raises ``ComplianceError``."""
    if is_placeholder_address(postal_address):
        raise ComplianceError(
            "SENDER_POSTAL_ADDRESS is empty or a placeholder — set a real physical "
            "mailing address before sending (CAN-SPAM requires it in every email)."
        )


def validate_subject(subject: str) -> None:
    """Reject empty, shouting, or deceptive subjects."""
    s = (subject or "").strip()
    if not s:
        raise ComplianceError("subject is empty")
    if len(s) > 200:
        raise ComplianceError("subject is too long")
    letters = [c for c in s if c.isalpha()]
    if len(letters) >= 8 and s == s.upper():
        raise ComplianceError("subject is all-caps (spammy/deceptive)")
    if "!!!" in s:
        raise ComplianceError("subject uses excessive punctuation")
    if re.match(r"\s*(re|fwd)\s*:", s, re.IGNORECASE):
        raise ComplianceError("subject fakes a reply/forward thread (deceptive)")


def validate_footer(footer: str, *, postal_address: str) -> None:
    """Reject a footer missing the physical address or an opt-out mechanism."""
    if postal_address not in (footer or ""):
        raise ComplianceError("footer is missing the physical postal address")
    if not any(m in footer.lower() for m in _OPT_OUT_MARKERS):
        raise ComplianceError("footer is missing an opt-out mechanism")


def validate_email(*, subject: str, footer: str, postal_address: str) -> None:
    """Full CAN-SPAM gate for an outreach email. Raises ``ComplianceError``."""
    validate_subject(subject)
    validate_footer(footer, postal_address=postal_address)


def _domain_of(email: str) -> str:
    return email.split("@")[-1].strip().lower()


def is_suppressed(session: Session, email: str) -> bool:
    """True if this exact address, or its domain, is on the suppression list."""
    addr = (email or "").strip().lower()
    if not addr:
        return False
    domain = _domain_of(addr)
    hit = session.execute(
        select(SuppressionEntry).where(
            or_(SuppressionEntry.email == addr, SuppressionEntry.domain == domain)
        ).limit(1)
    ).scalars().first()
    return hit is not None


def suppress(
    session: Session, *, email: str | None = None, domain: str | None = None, reason
) -> SuppressionEntry:  # noqa: ANN001 - reason is SuppressionReason
    """Add a recipient (or whole domain) to the suppression list."""
    entry = SuppressionEntry(
        email=email.strip().lower() if email else None,
        domain=domain.strip().lower() if domain else None,
        reason=reason,
    )
    session.add(entry)
    session.flush()
    return entry
