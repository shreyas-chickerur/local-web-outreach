"""Sending identities: per-mailbox caps, warmup, and the deliverability kill switch.

Revision ID: 0008_sender_identities
Revises: 0007_operator_verification
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.core.types import GUID

revision = "0008_sender_identities"
down_revision = "0007_operator_verification"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if "sender_identities" in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "sender_identities",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("address", sa.String(255), nullable=False, unique=True),
        sa.Column("display_name", sa.String(120), nullable=True),
        sa.Column("domain", sa.String(255), nullable=False, index=True),
        sa.Column("daily_cap", sa.Integer(), nullable=False, server_default="20"),
        sa.Column("warmup_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("bounce_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("complaint_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("paused", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("paused_reason", sa.Text(), nullable=True),
        sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("sender_identities")
