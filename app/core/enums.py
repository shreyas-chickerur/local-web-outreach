"""Enumerations shared across the spine.

Kept dependency-free so both the ORM models and the state machine can import
these without creating an import cycle.
"""

from __future__ import annotations

from enum import StrEnum


class BusinessStatus(StrEnum):
    """The single lifecycle state machine for a business row.

    Legal transitions are declared in ``app.core.state_machine.ALLOWED_TRANSITIONS``.
    """

    DISCOVERED = "DISCOVERED"
    QUALIFIED = "QUALIFIED"
    RESEARCHED = "RESEARCHED"
    SITE_DRAFTED = "SITE_DRAFTED"
    SITE_APPROVED = "SITE_APPROVED"
    EMAIL_DRAFTED = "EMAIL_DRAFTED"
    EMAIL_APPROVED = "EMAIL_APPROVED"
    SENT = "SENT"
    REPLIED = "REPLIED"
    NEGOTIATING = "NEGOTIATING"
    # terminal states
    WON = "WON"
    LOST = "LOST"
    SUPPRESSED = "SUPPRESSED"
    DISQUALIFIED = "DISQUALIFIED"


class SubjectType(StrEnum):
    """What an approval authorizes."""

    SITE = "site"
    EMAIL = "email"
    REPLY = "reply"


class Decision(StrEnum):
    """Operator decision recorded on an approval."""

    APPROVE = "approve"
    REJECT = "reject"
    EDIT = "edit"
    REQUEST_CHANGES = "request_changes"


class Actor(StrEnum):
    """Who caused an audited action."""

    SYSTEM = "system"
    HUMAN = "human"
    WORKER = "worker"


class Severity(StrEnum):
    """Severity of a detected website weakness."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class SourceType(StrEnum):
    """Where a research claim was sourced from."""

    GBP = "gbp"  # Google Business Profile
    YELP = "yelp"
    FACEBOOK = "facebook"
    EXISTING_SITE = "existing_site"
    NEWS = "news"
    DIRECTORY = "directory"
    OTHER = "other"


class ClaimStatus(StrEnum):
    """Confidence disposition of a research claim after corroboration.

    Only VERIFIED claims may ship as fact on a generated site (invariant #1).
    """

    VERIFIED = "verified"  # >= 2 independent sources agree
    UNVERIFIED = "unverified"  # single source, or below threshold
    CONFLICT = "conflict"  # sources disagree — never ships; ask the owner


class WebsiteState(StrEnum):
    """Lifecycle of a generated website. Stays a private DRAFT until approved."""

    DRAFT = "draft"  # generated; private preview only
    APPROVED = "approved"  # operator signed off (Gate 1)
    LIVE = "live"  # published after purchase
    REJECTED = "rejected"
