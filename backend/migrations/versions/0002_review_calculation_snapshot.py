"""Persist the canonical Calculation Snapshot for each review.

Revision ID: 0002_calculation_snapshot
Revises: 0001_phase0_4_baseline
Create Date: 2026-08-15

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_calculation_snapshot"
down_revision: str | None = "0001_phase0_4_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "review_calculation_snapshots",
        sa.Column("review_id", sa.String(length=36), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("engine_version", sa.String(length=100), nullable=False),
        sa.Column("calculations", sa.JSON(), nullable=False),
        sa.Column("missing_information", sa.JSON(), nullable=False),
        sa.Column("errors", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["review_id"], ["review_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("review_id"),
    )


def downgrade() -> None:
    op.drop_table("review_calculation_snapshots")
