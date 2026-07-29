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
