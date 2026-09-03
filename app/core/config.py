"""Runtime configuration.

Phase 1 keeps this deliberately tiny (env-driven). Production target is
PostgreSQL; dev/test default to a local SQLite file so the suite runs with
zero external dependencies.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

# Load a local .env if present (never overrides already-set environment vars).
load_dotenv()

DEFAULT_SQLITE_URL = "sqlite+pysqlite:///./local_web_outreach.db"


def database_url() -> str:
    """Return the active database URL (``DATABASE_URL`` env var or SQLite default)."""
    return os.environ.get("DATABASE_URL", DEFAULT_SQLITE_URL)


def places_provider() -> str:
    """Which places data source to use for live runs (default: google)."""
    return os.environ.get("PLACES_PROVIDER", "google").lower()


def google_places_api_key() -> str | None:
    """The Google Places API key, if configured (only needed for live discovery)."""
    return os.environ.get("GOOGLE_PLACES_API_KEY")


def yelp_api_key() -> str | None:
    """The Yelp Fusion API key, if configured.

    Lives here rather than in the adapter so it is read *after* the
    ``load_dotenv()`` above — an adapter reading ``os.environ`` directly only
    sees the key when this module happens to be imported first.
    """
    return os.environ.get("YELP_API_KEY", "").strip() or None


def preview_base_url() -> str:
    """Where generated site previews are served from.

    Locally this is the console itself; in production it becomes the public host
    that prospects can open. The token in the path is what keeps it private.
    """
    return os.environ.get("PREVIEW_BASE_URL", "http://127.0.0.1:8090").rstrip("/")


def send_mode() -> str:
    """How the send layer behaves. Defaults to the safe option, always.

    ``dry_run``   — write .eml files to disk, deliver nothing (default)
    ``self_test`` — really deliver, but ONLY to addresses on the allow-list
    ``live``      — deliver to anyone who has passed both approval gates

    The default is dry_run so that forgetting to configure something can never
    result in mail reaching a real business.
    """
    mode = os.environ.get("SEND_MODE", "dry_run").strip().lower()
    return mode if mode in {"dry_run", "self_test", "live"} else "dry_run"


def send_allowlist() -> set[str]:
    """Addresses ``self_test`` mode is permitted to deliver to."""
    raw = os.environ.get("SEND_ALLOWLIST", "")
    return {a.strip().lower() for a in raw.split(",") if a.strip()}


def send_outbox_dir() -> str:
    """Where dry-run mode writes .eml files you can open in a mail client."""
    return os.environ.get("SEND_OUTBOX_DIR", "./outbox")


def daily_cap_per_inbox() -> int:
    """Hard ceiling per sending inbox per day. Deliverability, not throughput."""
    try:
        return max(1, int(os.environ.get("DAILY_CAP_PER_INBOX", "20")))
    except ValueError:
        return 20


def warmup_days_required() -> int:
    """A sending identity younger than this may not send campaign mail."""
    try:
        return max(0, int(os.environ.get("WARMUP_DAYS_REQUIRED", "21")))
    except ValueError:
        return 21


def smtp_settings() -> dict[str, str | int | None]:
    """SMTP credentials, if configured. Absent means no live sending is possible."""
    return {
        "host": os.environ.get("SMTP_HOST") or None,
        "port": int(os.environ.get("SMTP_PORT", "587") or 587),
        "user": os.environ.get("SMTP_USER") or None,
        "password": os.environ.get("SMTP_PASSWORD") or None,
    }


def sender_name() -> str:
    """Display name used in the CAN-SPAM email footer."""
    return os.environ.get("SENDER_NAME", "Local Web Outreach")


def sender_postal_address() -> str:
    """Physical postal address for the CAN-SPAM footer.

    A real mailing address is legally required for cold email — set
    SENDER_POSTAL_ADDRESS before sending. The default is an obvious placeholder.
    """
    return os.environ.get("SENDER_POSTAL_ADDRESS", "123 Example St, Frisco, TX 75034")
