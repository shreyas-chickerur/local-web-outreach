"""Phase 7 guard tests — the send layer's job is to refuse.

Every test here asserts something does NOT go out. That is the point: this is
the only stage that does something irreversible outside the system.
"""

from __future__ import annotations

from datetime import timedelta

import pytest

from app.adapters.email_send import DryRunSender, FailingSender
from app.core.clock import utcnow
from app.core.compliance import suppress
from app.core.enums import BusinessStatus, EmailStatus, SuppressionReason
from app.core.errors import NotFoundError, SuppressionError
from app.models.email import Email
from app.models.sender_identity import SenderIdentity
from app.stages import send as send_stage
from app.stages.send import SendBlocked, eligible_identity, send_one

pytestmark = pytest.mark.functional


@pytest.fixture(autouse=True)
def _real_address(monkeypatch):
    """Most tests need the postal-address guard satisfied to reach later guards."""
    monkeypatch.setenv("SENDER_POSTAL_ADDRESS", "500 Main St, Frisco, TX 75034")
    monkeypatch.setenv("SEND_MODE", "live")
    monkeypatch.setenv("WARMUP_DAYS_REQUIRED", "21")


def _identity(session, address="a@sending.example", cap=20, warm_days=40, paused=False):
    ident = SenderIdentity(
        address=address, domain=address.split("@")[-1], daily_cap=cap,
        warmup_started_at=utcnow() - timedelta(days=warm_days), paused=paused,
        display_name="Test Sender",
    )
    session.add(ident)
    session.flush()
    return ident


def _approved(session, make_email_drafted, **kw):
    """A business that has passed BOTH gates, ready to send."""
    from app.api import schemas, service

    biz, email = make_email_drafted(**kw)
    service.decide_email(session, biz.id, schemas.EmailDecisionIn(
        decision="approve", approver="operator",
        expected_content_hash=email.content_hash))
    session.flush()
    return biz, email


# ----------------------------- the gates hold ------------------------------ #
def test_a_fully_approved_email_sends(session, make_email_drafted, tmp_path):
    biz, _ = _approved(session, make_email_drafted)
    out = send_one(session, biz, DryRunSender(str(tmp_path)), [_identity(session)])
    assert out.ok
    assert session.get(type(biz), biz.id).status is BusinessStatus.SENT
    assert list(tmp_path.glob("*.eml")), "dry run must write a real .eml"


def test_placeholder_postal_address_blocks_the_send(
        session, make_email_drafted, tmp_path, monkeypatch):
    """CAN-SPAM needs a real address. This is absolute — there is no override."""
    monkeypatch.setenv("SENDER_POSTAL_ADDRESS", "123 Example St, Frisco, TX")
    biz, _ = _approved(session, make_email_drafted)
    with pytest.raises(SendBlocked, match="placeholder"):
        send_one(session, biz, DryRunSender(str(tmp_path)), [_identity(session)])


def test_unapproved_business_cannot_send(session, make_email_drafted, tmp_path):
    biz, _ = make_email_drafted()          # drafted, never approved
    with pytest.raises(NotFoundError):     # no APPROVED email exists to send
        send_one(session, biz, DryRunSender(str(tmp_path)), [_identity(session)])
    assert session.get(type(biz), biz.id).status is BusinessStatus.EMAIL_DRAFTED


def test_an_email_edited_after_approval_cannot_send(
        session, make_email_drafted, tmp_path):
    """The approval is bound to bytes. Change them and the approval is void."""
    biz, email = _approved(session, make_email_drafted)
    email.body = email.body + "\n\nPS: one more thing"
    session.flush()
    with pytest.raises(SendBlocked, match="changed after it was approved"):
        send_one(session, biz, DryRunSender(str(tmp_path)), [_identity(session)])


def test_suppression_is_rechecked_at_send_not_trusted_from_compose(
        session, make_email_drafted, tmp_path):
    """They may have opted out between approval and send."""
    biz, email = _approved(session, make_email_drafted)
    suppress(session, email=email.recipient, reason=SuppressionReason.UNSUBSCRIBE)
    session.flush()
    with pytest.raises(SuppressionError):
        send_one(session, biz, DryRunSender(str(tmp_path)), [_identity(session)])


def test_geo_is_rechecked_at_send(session, make_email_drafted, tmp_path):
    biz, _ = _approved(session, make_email_drafted)
    biz.geo_country = "CA"
    session.flush()
    with pytest.raises(SendBlocked, match="geo-gated"):
        send_one(session, biz, DryRunSender(str(tmp_path)), [_identity(session)])


# ------------------------------ send modes --------------------------------- #
def test_self_test_mode_refuses_anyone_not_on_the_allowlist(
        session, make_email_drafted, tmp_path, monkeypatch):
    monkeypatch.setenv("SEND_MODE", "self_test")
    monkeypatch.setenv("SEND_ALLOWLIST", "me@mine.example")
    biz, _ = _approved(session, make_email_drafted, contact_email="stranger@acme.example")
    with pytest.raises(SendBlocked, match="not on SEND_ALLOWLIST"):
        send_one(session, biz, DryRunSender(str(tmp_path)), [_identity(session)])


def test_self_test_mode_allows_an_allowlisted_recipient(
        session, make_email_drafted, tmp_path, monkeypatch):
    monkeypatch.setenv("SEND_MODE", "self_test")
    monkeypatch.setenv("SEND_ALLOWLIST", "me@mine.example")
    biz, _ = _approved(session, make_email_drafted, contact_email="me@mine.example")
    assert send_one(session, biz, DryRunSender(str(tmp_path)), [_identity(session)]).ok


def test_self_test_with_an_empty_allowlist_sends_nothing(
        session, make_email_drafted, tmp_path, monkeypatch):
    monkeypatch.setenv("SEND_MODE", "self_test")
    monkeypatch.delenv("SEND_ALLOWLIST", raising=False)
    biz, _ = _approved(session, make_email_drafted)
    with pytest.raises(SendBlocked, match="empty SEND_ALLOWLIST"):
        send_one(session, biz, DryRunSender(str(tmp_path)), [_identity(session)])


def test_dry_run_is_the_default_mode(monkeypatch):
    monkeypatch.delenv("SEND_MODE", raising=False)
    from app.core import config
    assert config.send_mode() == "dry_run"
    monkeypatch.setenv("SEND_MODE", "nonsense")
    assert config.send_mode() == "dry_run"      # unknown value fails safe


# --------------------------- identity selection ----------------------------- #
def test_no_identity_configured_blocks(session):
    with pytest.raises(SendBlocked, match="no sending identity"):
        eligible_identity(session, [])


def test_a_paused_identity_is_never_used(session):
    ident = _identity(session, paused=True)
    ident.paused_reason = "bounce rate"
    with pytest.raises(SendBlocked, match="paused"):
        eligible_identity(session, [ident])


def test_an_identity_still_in_warmup_cannot_send(session):
    young = _identity(session, address="new@sending.example", warm_days=3)
    with pytest.raises(SendBlocked, match="warmup"):
        eligible_identity(session, [young])


def test_an_identity_that_never_started_warmup_cannot_send(session):
    ident = _identity(session)
    ident.warmup_started_at = None
    with pytest.raises(SendBlocked, match="warmup never started"):
        eligible_identity(session, [ident])


def test_the_daily_cap_is_enforced(session, make_email_drafted, tmp_path):
    ident = _identity(session, cap=1)
    biz, _ = _approved(session, make_email_drafted, place_id="s1", contact_email="a@x.example")
    assert send_one(session, biz, DryRunSender(str(tmp_path)), [ident]).ok

    biz2, _ = _approved(session, make_email_drafted, place_id="s2",
                        contact_email="b@x.example")
    with pytest.raises(SendBlocked, match="daily cap"):
        send_one(session, biz2, DryRunSender(str(tmp_path)), [ident])


def test_sends_spread_across_identities(session, make_email_drafted, tmp_path):
    """Least-used first, so a restart cannot bunch every send onto one mailbox."""
    a = _identity(session, address="a@sending.example")
    b = _identity(session, address="b@sending.example")
    used = []
    for n in range(4):
        biz, _ = _approved(session, make_email_drafted, place_id=f"r{n}",
                           contact_email=f"r{n}@x.example")
        out = send_one(session, biz, DryRunSender(str(tmp_path)), [a, b])
        assert out.ok
        used.append(session.query(Email).filter_by(business_id=biz.id).one().inbox_used)
    assert used.count(a.address) == 2 and used.count(b.address) == 2


# ---------------------------- the kill switch ------------------------------- #
def test_bounces_pause_the_identity_automatically(session, make_email_drafted, tmp_path):
    """Automatic, because by the time a person notices, the domain is burnt."""
    ident = _identity(session, cap=500)
    ident.sent_count = 100
    ident.bounce_count = 2          # 2% — at the threshold, not over
    session.flush()

    biz, _ = _approved(session, make_email_drafted)
    out = send_one(session, biz, FailingSender(), [ident])
    assert not out.ok
    session.expire_all()
    ident = session.get(SenderIdentity, ident.id)
    assert ident.paused, "3/101 bounces is over 2% and must trip the switch"
    assert "bounce rate" in ident.paused_reason


def test_a_healthy_identity_is_not_paused(session, make_email_drafted, tmp_path):
    ident = _identity(session)
    ident.sent_count = 500
    ident.bounce_count = 1
    session.flush()
    biz, _ = _approved(session, make_email_drafted)
    send_one(session, biz, DryRunSender(str(tmp_path)), [ident])
    assert not session.get(SenderIdentity, ident.id).paused


def test_rates_are_ignored_on_a_tiny_sample(session):
    """1 bounce out of 3 is 33% but means nothing — don't pause on noise."""
    ident = SenderIdentity(address="t@x.example", domain="x.example",
                           sent_count=3, bounce_count=1)
    send_stage._pause_if_degraded(None, ident)   # noqa: SLF001
    assert not ident.paused


def test_a_failed_send_marks_the_email_failed_not_sent(
        session, make_email_drafted):
    biz, _ = _approved(session, make_email_drafted)
    send_one(session, biz, FailingSender(), [_identity(session)])
    session.expire_all()
    assert session.query(Email).filter_by(business_id=biz.id).one().status \
        is EmailStatus.FAILED
    assert session.get(type(biz), biz.id).status is BusinessStatus.EMAIL_APPROVED


def test_an_email_composed_with_a_placeholder_address_cannot_send(
        session, make_email_drafted, tmp_path, monkeypatch):
    """The config can be fixed after composing — but the recipient gets the
    BYTES, and those still carry the placeholder until the email is re-drafted."""
    biz, email = _approved(session, make_email_drafted)
    email.footer = "\n—\nShreyas\nCHANGE ME — your real mailing address\nReply UNSUBSCRIBE"
    session.flush()
    monkeypatch.setenv("SENDER_POSTAL_ADDRESS", "500 Main St, Frisco, TX 75034")
    with pytest.raises(SendBlocked, match="composed while the postal address"):
        send_one(session, biz, DryRunSender(str(tmp_path)), [_identity(session)])


def test_warmup_survives_a_naive_timestamp_from_the_database(session):
    """SQLite drops timezones, so a stored 'aware' datetime reads back naive and
    comparing it against utcnow() raises. Caught only by a real round-trip."""
    from datetime import datetime, timedelta

    ident = _identity(session)
    ident.warmup_started_at = datetime.now() - timedelta(days=60)   # naive on purpose
    session.flush()
    assert eligible_identity(session, [ident]) is ident


# ------------------------------ redirect ------------------------------------ #
def test_redirect_delivers_to_the_operator_and_records_the_real_recipient(
        session, make_email_drafted, tmp_path, monkeypatch):
    monkeypatch.setenv("SEND_MODE", "self_test")
    monkeypatch.setenv("SEND_ALLOWLIST", "me@mine.example")
    biz, email = _approved(session, make_email_drafted,
                           contact_email="owner@business.example")
    out = send_one(session, biz, DryRunSender(str(tmp_path)), [_identity(session)],
                   redirect_to="me@mine.example")
    assert out.ok and out.recipient == "me@mine.example"

    written = list(tmp_path.glob("*.eml"))[0].read_text()
    assert "To: me@mine.example" in written
    assert "[TEST " in written and "owner@business.example" in written

    from app.models.audit import AuditEvent
    event = session.query(AuditEvent).filter_by(action="send:delivered").one()
    assert event.after["intended_recipient"] == "owner@business.example"
    assert event.after["delivered_to"] == "me@mine.example"


def test_redirect_is_refused_in_live_mode(session, make_email_drafted, tmp_path,
                                          monkeypatch):
    """A redirect is a testing tool. In live mode it could only hide a mistake."""
    monkeypatch.setenv("SEND_MODE", "live")
    biz, _ = _approved(session, make_email_drafted)
    with pytest.raises(SendBlocked, match="not permitted in live mode"):
        send_one(session, biz, DryRunSender(str(tmp_path)), [_identity(session)],
                 redirect_to="me@mine.example")


def test_redirect_cannot_smuggle_past_suppression(
        session, make_email_drafted, tmp_path, monkeypatch):
    """Suppression is checked against the ORIGINAL recipient, not the redirect."""
    monkeypatch.setenv("SEND_MODE", "self_test")
    monkeypatch.setenv("SEND_ALLOWLIST", "me@mine.example")
    biz, email = _approved(session, make_email_drafted)
    suppress(session, email=email.recipient, reason=SuppressionReason.UNSUBSCRIBE)
    session.flush()
    with pytest.raises(SuppressionError):
        send_one(session, biz, DryRunSender(str(tmp_path)), [_identity(session)],
                 redirect_to="me@mine.example")
