"""Add structured fault case storage for Phase 8.

Revision ID: 0004_fault_cases
Revises: 0003_datasheet_infrastructure
Create Date: 2026-08-16

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_fault_cases"
down_revision: str | None = "0003_datasheet_infrastructure"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "fault_cases",
        sa.Column("case_id", sa.String(length=36), nullable=False),
        sa.Column("topology", sa.String(length=50), nullable=False),
        sa.Column("power_w", sa.Float(), nullable=True),
        sa.Column("vin_v", sa.Float(), nullable=True),
        sa.Column("vout_v", sa.Float(), nullable=True),
        sa.Column("load_description", sa.String(length=300), nullable=True),
        sa.Column("symptom", sa.String(length=100), nullable=False),
        sa.Column("observed_features", sa.JSON(), nullable=False),
        sa.Column("root_cause", sa.Text(), nullable=False),
        sa.Column("verification_steps", sa.JSON(), nullable=False),
        sa.Column("fix", sa.JSON(), nullable=False),
        sa.Column("waveform_before", sa.Text(), nullable=True),
        sa.Column("waveform_after", sa.Text(), nullable=True),
        sa.Column("engineer_verified", sa.Boolean(), nullable=False),
        sa.Column("verification_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("case_id"),
    )
    op.create_index("ix_fault_cases_symptom", "fault_cases", ["symptom"])
    op.create_index(
        "ix_fault_cases_engineer_verified", "fault_cases", ["engineer_verified"]
    )
    op.create_index("ix_fault_cases_created_at", "fault_cases", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_fault_cases_created_at", table_name="fault_cases")
    op.drop_index("ix_fault_cases_engineer_verified", table_name="fault_cases")
    op.drop_index("ix_fault_cases_symptom", table_name="fault_cases")
    op.drop_table("fault_cases")
