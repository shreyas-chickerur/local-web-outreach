"""CAN-SPAM compliance + suppression tests (invariant #4)."""

from __future__ import annotations

import pytest

from app.core.compliance import (
    assert_real_sender_address,
    build_footer,
    is_placeholder_address,
    is_suppressed,
    suppress,
    validate_email,
    validate_footer,
    validate_subject,
)
from app.core.enums import SuppressionReason
from app.core.errors import ComplianceError

pytestmark = pytest.mark.unit

ADDR = "500 Main St, Frisco, TX 75034"


def test_build_footer_has_address_and_optout():
    footer = build_footer(sender_name="LWO", postal_address=ADDR)
    assert ADDR in footer
    assert "unsubscribe" in footer.lower()


def test_validate_footer_ok():
    validate_footer(build_footer(sender_name="X", postal_address=ADDR), postal_address=ADDR)


def test_validate_footer_missing_address_raises():
    with pytest.raises(ComplianceError):
        validate_footer("no address; reply unsubscribe", postal_address=ADDR)


def test_validate_footer_missing_optout_raises():
    with pytest.raises(ComplianceError):
        validate_footer(f"{ADDR}\nthanks", postal_address=ADDR)


@pytest.mark.parametrize("bad", ["", "BUY NOW LIMITED TIME OFFER", "Re: your invoice", "WIN!!!"])
def test_validate_subject_rejects_bad(bad):
    with pytest.raises(ComplianceError):
        validate_subject(bad)


def test_validate_subject_accepts_clean():
    validate_subject("A quick idea for Acme Diner")


def test_validate_email_full_pass():
    validate_email(subject="A quick idea for Acme",
                   footer=build_footer(sender_name="X", postal_address=ADDR),
                   postal_address=ADDR)


def test_is_suppressed_exact_and_domain(session):
    suppress(session, email="stop@a.com", reason=SuppressionReason.UNSUBSCRIBE)
    suppress(session, domain="blocked.com", reason=SuppressionReason.COMPLAINT)
    assert is_suppressed(session, "stop@a.com") is True
    assert is_suppressed(session, "STOP@A.COM") is True  # case-insensitive
    assert is_suppressed(session, "anyone@blocked.com") is True  # domain match
    assert is_suppressed(session, "someone@fine.com") is False
    assert is_suppressed(session, "") is False


# --- placeholder-address send guard (blocks non-compliant sends) ------------
@pytest.mark.parametrize(
    "addr",
    [
        "",
        "   ",
        "123 Example St, Frisco, TX 75034",  # config.py default
        "CHANGE ME — your real mailing address, e.g. 123 Main St, Frisco, TX",  # .env stub
        "your mailing address here",
        "TODO",
    ],
)
def test_placeholder_addresses_are_rejected(addr):
    assert is_placeholder_address(addr) is True
    with pytest.raises(ComplianceError):
        assert_real_sender_address(addr)


@pytest.mark.parametrize(
    "addr",
    [
        "500 Main St, Frisco, TX 75034",
        "PO Box 1234, Dallas, TX 75201",
        "1600 Pennsylvania Ave NW, Washington, DC 20500",
    ],
)
def test_real_addresses_pass(addr):
    assert is_placeholder_address(addr) is False
    assert_real_sender_address(addr)  # does not raise


@pytest.mark.parametrize("addr", [
    "SAMPLE MAILING ADDRESS",      # slipped through once — caught in a live run
    "Dummy Address",
    "fake st, frisco tx",
    "TBD",
    "N/A",
    "test address",
    "123 Main St, Frisco, TX 75034",   # our own docs' stock example
])
def test_more_placeholder_shapes_are_rejected(addr):
    assert is_placeholder_address(addr) is True
    with pytest.raises(ComplianceError):
        assert_real_sender_address(addr)
