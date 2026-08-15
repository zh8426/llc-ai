"""Create the Phase 0-4 database baseline.

Revision ID: 0001_phase0_4_baseline
Revises:
Create Date: 2026-08-15

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_phase0_4_baseline"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("topology", sa.String(length=50), nullable=False),
        sa.Column("vin_min_v", sa.Float(), nullable=True),
        sa.Column("vin_nom_v", sa.Float(), nullable=True),
        sa.Column("vin_max_v", sa.Float(), nullable=True),
        sa.Column("vout_v", sa.Float(), nullable=True),
        sa.Column("iout_a", sa.Float(), nullable=True),
        sa.Column("pout_w", sa.Float(), nullable=True),
        sa.Column("target_efficiency", sa.Float(), nullable=True),
        sa.Column("lr_h", sa.Float(), nullable=True),
        sa.Column("lm_h", sa.Float(), nullable=True),
        sa.Column("cr_f", sa.Float(), nullable=True),
        sa.Column("fsw_min_hz", sa.Float(), nullable=True),
        sa.Column("fsw_nom_hz", sa.Float(), nullable=True),
        sa.Column("fsw_max_hz", sa.Float(), nullable=True),
        sa.Column("transformer_ratio", sa.Float(), nullable=True),
        sa.Column("dead_time_s", sa.Float(), nullable=True),
        sa.Column("rectification_type", sa.String(length=50), nullable=False),
        sa.Column("controller_model", sa.String(length=200), nullable=True),
        sa.Column("controller_frequency_min_hz", sa.Float(), nullable=True),
        sa.Column("controller_frequency_max_hz", sa.Float(), nullable=True),
        sa.Column("primary_switch_manufacturer", sa.String(length=200), nullable=True),
        sa.Column("primary_switch_part_number", sa.String(length=200), nullable=True),
        sa.Column("primary_switch_vds_rating_v", sa.Float(), nullable=True),
        sa.Column("primary_switch_measured_vds_peak_v", sa.Float(), nullable=True),
        sa.Column("primary_switch_current_rating_a", sa.Float(), nullable=True),
        sa.Column("primary_switch_measured_peak_current_a", sa.Float(), nullable=True),
        sa.Column(
            "primary_switch_current_temperature_condition",
            sa.String(length=500),
            nullable=True,
        ),
        sa.Column("resonant_capacitor_voltage_rating_v", sa.Float(), nullable=True),
        sa.Column("resonant_capacitor_voltage_stress_v", sa.Float(), nullable=True),
        sa.Column("resonant_capacitor_rms_current_rating_a", sa.Float(), nullable=True),
        sa.Column("resonant_capacitor_rms_current_stress_a", sa.Float(), nullable=True),
        sa.Column("zvs_analysis_requested", sa.Boolean(), nullable=False),
        sa.Column("full_gain_review_requested", sa.Boolean(), nullable=False),
        sa.Column("output_power_relative_tolerance", sa.Float(), nullable=True),
        sa.Column("measured_vds_required_margin_ratio", sa.Float(), nullable=True),
        sa.Column("gain_review_required_parameters", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "review_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("pass_count", sa.Integer(), nullable=False),
        sa.Column("info_count", sa.Integer(), nullable=False),
        sa.Column("warning_count", sa.Integer(), nullable=False),
        sa.Column("critical_count", sa.Integer(), nullable=False),
        sa.Column("insufficient_data_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_review_runs_created_at", "review_runs", ["created_at"])
    op.create_index("ix_review_runs_project_id", "review_runs", ["project_id"])

    op.create_table(
        "review_findings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("review_id", sa.String(length=36), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("rule_id", sa.String(length=20), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("severity", sa.String(length=30), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("calculated_values", sa.JSON(), nullable=False),
        sa.Column("missing_information", sa.JSON(), nullable=False),
        sa.Column("recommended_action", sa.JSON(), nullable=False),
        sa.Column("requires_engineer_confirmation", sa.Boolean(), nullable=False),
        sa.Column("report_eligible", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["review_id"], ["review_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_review_findings_category", "review_findings", ["category"])
    op.create_index("ix_review_findings_review_id", "review_findings", ["review_id"])
    op.create_index("ix_review_findings_rule_id", "review_findings", ["rule_id"])
    op.create_index("ix_review_findings_severity", "review_findings", ["severity"])

    op.create_table(
        "review_project_snapshots",
        sa.Column("review_id", sa.String(length=36), nullable=False),
        sa.Column("project_data", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["review_id"], ["review_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("review_id"),
    )


def downgrade() -> None:
    op.drop_table("review_project_snapshots")
    op.drop_index("ix_review_findings_severity", table_name="review_findings")
    op.drop_index("ix_review_findings_rule_id", table_name="review_findings")
    op.drop_index("ix_review_findings_review_id", table_name="review_findings")
    op.drop_index("ix_review_findings_category", table_name="review_findings")
    op.drop_table("review_findings")
    op.drop_index("ix_review_runs_project_id", table_name="review_runs")
    op.drop_index("ix_review_runs_created_at", table_name="review_runs")
    op.drop_table("review_runs")
    op.drop_table("projects")
