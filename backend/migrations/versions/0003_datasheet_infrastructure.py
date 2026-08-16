"""Add conservative MOSFET datasheet document and parameter storage.

Revision ID: 0003_datasheet_infrastructure
Revises: 0002_calculation_snapshot
Create Date: 2026-08-16

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_datasheet_infrastructure"
down_revision: str | None = "0002_calculation_snapshot"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "datasheet_documents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("manufacturer", sa.String(length=200), nullable=True),
        sa.Column("part_number", sa.String(length=200), nullable=True),
        sa.Column("parser_status", sa.String(length=40), nullable=False),
        sa.Column("parser_message", sa.Text(), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "datasheet_parameters",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("parameter_name", sa.String(length=50), nullable=False),
        sa.Column("value_numeric", sa.Float(), nullable=True),
        sa.Column("value_text", sa.String(length=500), nullable=True),
        sa.Column("unit", sa.String(length=50), nullable=False),
        sa.Column("value_type", sa.String(length=30), nullable=False),
        sa.Column("test_condition", sa.JSON(), nullable=False),
        sa.Column("source_page", sa.Integer(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("human_verified", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["document_id"], ["datasheet_documents.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_datasheet_parameters_document_id",
        "datasheet_parameters",
        ["document_id"],
    )
    op.create_index(
        "ix_datasheet_parameters_parameter_name",
        "datasheet_parameters",
        ["parameter_name"],
    )


def downgrade() -> None:
    op.drop_index("ix_datasheet_parameters_parameter_name", table_name="datasheet_parameters")
    op.drop_index("ix_datasheet_parameters_document_id", table_name="datasheet_parameters")
    op.drop_table("datasheet_parameters")
    op.drop_table("datasheet_documents")
