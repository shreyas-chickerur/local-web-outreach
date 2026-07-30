"""email: businesses.contact_email + emails + suppression_list

Revision ID: 0005_email
Revises: 0004_websites
Create Date: 2026-07-29
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.core.types import GUID

revision: str = "0005_email"
down_revision: Union[str, None] = "0004_websites"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("businesses", sa.Column("contact_email", sa.String(length=255), nullable=True))

    op.create_table(
        "emails",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("business_id", GUID(), sa.ForeignKey("businesses.id"), nullable=False),
        sa.Column(
            "kind",
            sa.Enum("outreach", "reply", name="email_kind", native_enum=False, length=16,
                    create_constraint=True),
            nullable=False,
        ),
        sa.Column("recipient", sa.String(length=255), nullable=False),
        sa.Column("subject", sa.String(length=500), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("footer", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("draft", "approved", "queued", "sent", "bounced", "failed",
                    name="email_status", native_enum=False, length=16, create_constraint=True),
            nullable=False,
        ),
        sa.Column("suppression_checked", sa.Boolean(), nullable=False),
        sa.Column("inbox_used", sa.String(length=255), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_emails_business_id", "emails", ["business_id"])

    op.create_table(
        "suppression_list",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("domain", sa.String(length=255), nullable=True),
        sa.Column(
            "reason",
            sa.Enum("unsubscribe", "complaint", "bounce", "manual",
                    name="suppression_reason", native_enum=False, length=16,
                    create_constraint=True),
            nullable=False,
        ),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("uq_suppression_email", "suppression_list", ["email"], unique=True)
    op.create_index("ix_suppression_domain", "suppression_list", ["domain"])


def downgrade() -> None:
    op.drop_index("ix_suppression_domain", table_name="suppression_list")
    op.drop_index("uq_suppression_email", table_name="suppression_list")
    op.drop_table("suppression_list")
    op.drop_index("ix_emails_business_id", table_name="emails")
    op.drop_table("emails")
    op.drop_column("businesses", "contact_email")
