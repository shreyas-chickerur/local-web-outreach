"""Spine-level exceptions.

These are the load-bearing failures the guard tests assert on. If you find
yourself catching-and-ignoring one of these, the behavior is wrong, not the
exception.
"""

from __future__ import annotations


class SpineError(Exception):
    """Base class for all spine invariant violations."""


class TransitionError(SpineError):
    """Raised when a business is advanced along an illegal state transition."""


class ApprovalRequiredError(SpineError):
    """Raised when a gated transition is attempted without a valid approval.

    Enforces invariant #2: no side-effect without a signed approval.
    """


class AppendOnlyError(SpineError):
    """Raised when code attempts to UPDATE or DELETE an append-only row.

    Enforces invariant #3: the audit ledger and approvals are immutable.
    """


class ResearchIntegrityError(SpineError):
    """Raised when a research claim would persist without a source_url.

    Enforces invariant #1: no fact ships without provenance.
    """


class RefusalError(SpineError):
    """Raised when the LLM declines a request (stop_reason == 'refusal')."""


class SiteIntegrityError(SpineError):
    """Raised when generated site content asserts a fact not backed by a VERIFIED
    claim, or fabricates social proof (reviews/testimonials).

    Enforces invariant #1 on the generated site itself.
    """


class StaleContentError(SpineError):
    """Raised when an approval names a content hash that no longer matches the
    current draft — the operator reviewed a version that has since changed.

    Enforces invariant #2: approval binds to the exact reviewed content.
    """


class NotFoundError(SpineError):
    """Raised when a requested resource does not exist."""
