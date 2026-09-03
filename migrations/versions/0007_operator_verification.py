"""Operator-verified claims: a human may vouch for a fact, and is named for it.

Revision ID: 0007_operator_verification
Revises: 0006_ratings

The awkward part is the status CHECK constraint. ``claim_status`` is a
non-native enum, so the allowed values live in a CHECK that must be widened to
admit ``operator_verified``. SQLite cannot ALTER a CHECK in place, so the table
is recreated in batch mode with the old constraint dropped and a new one added.
Existing rows are preserved — this is expected to run against populated
databases.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0007_operator_verification"
down_revision = "0006_ratings"
branch_labels = None
depends_on = None

_COLUMNS = (
    ("verified_by", sa.String(120)),
    ("verified_at", sa.DateTime(timezone=True)),
    ("verified_note", sa.Text()),
)
_NEW = ("verified", "unverified", "conflict", "operator_verified")
_OLD = ("verified", "unverified", "conflict")


def _rewrite_status_check(allowed: tuple[str, ...], length: int) -> None:
    quoted = ", ".join(f"'{v}'" for v in allowed)
    with op.batch_alter_table("research_claims", recreate="always") as batch:
        try:
            batch.drop_constraint("claim_status", type_="check")
        except Exception:  # noqa: BLE001 - constraint name varies by backend/age
            pass
        batch.alter_column("status", existing_type=sa.String(16),
                           type_=sa.String(length), existing_nullable=False)
        batch.create_check_constraint("claim_status", f"status IN ({quoted})")


def upgrade() -> None:
    existing = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("research_claims")}
    for name, type_ in _COLUMNS:
        if name not in existing:
            op.add_column("research_claims", sa.Column(name, type_, nullable=True))
    _rewrite_status_check(_NEW, 24)


def downgrade() -> None:
    # Any operator-verified claim reverts to unverified — the vouching is gone,
    # so the claim must not keep shipping as fact.
    op.execute("UPDATE research_claims SET status='unverified' "
               "WHERE status='operator_verified'")
    _rewrite_status_check(_OLD, 16)
    for name, _ in reversed(_COLUMNS):
        op.drop_column("research_claims", name)
