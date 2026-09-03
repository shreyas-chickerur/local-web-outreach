"""Delivering an approved email.

Three implementations behind one protocol:

* ``DryRunSender``  — writes a real RFC-822 ``.eml`` to disk and delivers
  nothing. This is the default, and it is genuinely useful: the file opens in
  any mail client, so the exact bytes a prospect would receive can be inspected
  before any credential exists.
* ``SmtpSender``    — actually delivers.
* ``FailingSender`` — used by tests to exercise the bounce path.

The sender is intentionally dumb. It does not know about suppression, approval,
compliance, or caps — every one of those is checked in ``app/stages/send.py``
BEFORE a sender is ever called, so a mistake here cannot bypass a guard.
"""

from __future__ import annotations

import smtplib
import uuid
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class SendResult:
    ok: bool
    message_id: str
    detail: str = ""


def build_message(*, sender: str, sender_name: str, recipient: str,
                  subject: str, body: str) -> EmailMessage:
    """The exact message that would go out — used by every sender."""
    msg = EmailMessage()
    msg["From"] = f"{sender_name} <{sender}>" if sender_name else sender
    msg["To"] = recipient
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid()
    # One-click unsubscribe, honoured by Gmail/Outlook UI. The body also carries
    # a plain-text opt-out; this is the machine-readable form of the same promise.
    msg["List-Unsubscribe"] = f"<mailto:{sender}?subject=unsubscribe>"
    msg.set_content(body)
    return msg


class Sender(Protocol):
    name: str

    def send(self, *, sender: str, sender_name: str, recipient: str,
             subject: str, body: str) -> SendResult: ...


class DryRunSender:
    """Writes the message to disk instead of sending it. Delivers nothing."""

    name = "dry_run"

    def __init__(self, outbox_dir: str = "./outbox") -> None:
        self._dir = Path(outbox_dir)

    def send(self, *, sender: str, sender_name: str, recipient: str,
             subject: str, body: str) -> SendResult:
        msg = build_message(sender=sender, sender_name=sender_name,
                            recipient=recipient, subject=subject, body=body)
        self._dir.mkdir(parents=True, exist_ok=True)
        safe = "".join(c if c.isalnum() or c in "-_.@" else "_" for c in recipient)
        path = self._dir / f"{safe}-{uuid.uuid4().hex[:8]}.eml"
        path.write_text(msg.as_string(), encoding="utf-8")
        return SendResult(ok=True, message_id=msg["Message-ID"], detail=str(path))


class SmtpSender:
    """Real delivery over SMTP with STARTTLS."""

    name = "smtp"

    def __init__(self, host: str, port: int = 587, user: str | None = None,
                 password: str | None = None, timeout: float = 20.0) -> None:
        self._host, self._port = host, port
        self._user, self._password = user, password
        self._timeout = timeout

    def send(self, *, sender: str, sender_name: str, recipient: str,
             subject: str, body: str) -> SendResult:
        msg = build_message(sender=sender, sender_name=sender_name,
                            recipient=recipient, subject=subject, body=body)
        try:
            with smtplib.SMTP(self._host, self._port, timeout=self._timeout) as smtp:
                smtp.starttls()
                if self._user and self._password:
                    smtp.login(self._user, self._password)
                smtp.send_message(msg)
        except (smtplib.SMTPException, OSError) as exc:
            return SendResult(ok=False, message_id=msg["Message-ID"], detail=str(exc))
        return SendResult(ok=True, message_id=msg["Message-ID"])


class FailingSender:
    """Always fails — lets tests drive the bounce/kill-switch path."""

    name = "failing"

    def __init__(self, detail: str = "550 mailbox unavailable") -> None:
        self._detail = detail

    def send(self, **kwargs) -> SendResult:  # noqa: ANN003
        return SendResult(ok=False, message_id=make_msgid(), detail=self._detail)
