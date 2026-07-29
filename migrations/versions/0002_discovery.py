"""discovery & qualification: business columns + site_weaknesses

Revision ID: 0002_discovery
Revises: 0001_initial
Create Date: 2026-07-29
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.core.types import GUID

revision: str = "0002_discovery"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("businesses", sa.Column("place_id", sa.String(length=255), nullable=True))
    op.add_column("businesses", sa.Column("address", sa.String(length=400), nullable=True))
    op.add_column("businesses", sa.Column("phone", sa.String(length=40), nullable=True))
    op.add_column(
        "businesses", sa.Column("existing_site_url", sa.String(length=500), nullable=True)
    )
    op.add_column("businesses", sa.Column("has_site", sa.Boolean(), nullable=True))
    op.add_column("businesses", sa.Column("opportunity_score", sa.Integer(), nullable=True))
    # UNIQUE via index (SQLite cannot ADD COLUMN ... UNIQUE).
    op.create_index("uq_businesses_place_id", "businesses", ["place_id"], unique=True)

    op.create_table(
        "site_weaknesses",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("business_id", GUID(), sa.ForeignKey("businesses.id"), nullable=False),
        sa.Column("issue", sa.String(length=64), nullable=False),
        sa.Column(
            "severity",
            sa.Enum(
                "low", "medium", "high",
                name="weakness_severity", native_enum=False, length=8,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("evidence", sa.Text(), nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_site_weaknesses_business_id", "site_weaknesses", ["business_id"])


def downgrade() -> None:
    op.drop_index("ix_site_weaknesses_business_id", table_name="site_weaknesses")
    op.drop_table("site_weaknesses")
    op.drop_index("uq_businesses_place_id", table_name="businesses")
    op.drop_column("businesses", "opportunity_score")
    op.drop_column("businesses", "has_site")
    op.drop_column("businesses", "existing_site_url")
    op.drop_column("businesses", "phone")
    op.drop_column("businesses", "address")
    op.drop_column("businesses", "place_id")
