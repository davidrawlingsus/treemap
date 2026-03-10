"""add leadgen voc staging tables

Revision ID: 061
Revises: 060
Create Date: 2026-03-10
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "061"
down_revision = "060"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "leadgen_voc_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("work_email", sa.String(length=255), nullable=False),
        sa.Column("company_domain", sa.String(length=255), nullable=False),
        sa.Column("company_url", sa.Text(), nullable=False),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("review_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("coding_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("coding_status", sa.String(length=50), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("converted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("converted_client_uuid", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["converted_client_uuid"], ["clients.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id"),
    )
    op.create_index("ix_leadgen_voc_runs_run_id", "leadgen_voc_runs", ["run_id"], unique=True)
    op.create_index("ix_leadgen_voc_runs_company_domain", "leadgen_voc_runs", ["company_domain"], unique=False)
    op.create_index("ix_leadgen_voc_runs_created_at", "leadgen_voc_runs", ["created_at"], unique=False)

    op.create_table(
        "leadgen_voc_rows",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("respondent_id", sa.String(length=50), nullable=False),
        sa.Column("created", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_modified", sa.DateTime(timezone=True), nullable=True),
        sa.Column("client_id", sa.String(length=50), nullable=True),
        sa.Column("client_name", sa.String(length=255), nullable=True),
        sa.Column("project_id", sa.String(length=50), nullable=True),
        sa.Column("project_name", sa.String(length=255), nullable=True),
        sa.Column("total_rows", sa.Integer(), nullable=True),
        sa.Column("data_source", sa.String(length=255), nullable=True),
        sa.Column("dimension_ref", sa.String(length=50), nullable=False),
        sa.Column("dimension_name", sa.Text(), nullable=True),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("overall_sentiment", sa.String(length=50), nullable=True),
        sa.Column("topics", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("survey_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("question_text", sa.Text(), nullable=True),
        sa.Column("question_type", sa.String(length=50), nullable=True, server_default="open_text"),
        sa.Column("processed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["leadgen_voc_runs.run_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_leadgen_voc_rows_run_id", "leadgen_voc_rows", ["run_id"], unique=False)
    op.create_index("ix_leadgen_voc_rows_respondent_id", "leadgen_voc_rows", ["respondent_id"], unique=False)


def downgrade():
    op.drop_index("ix_leadgen_voc_rows_respondent_id", table_name="leadgen_voc_rows")
    op.drop_index("ix_leadgen_voc_rows_run_id", table_name="leadgen_voc_rows")
    op.drop_table("leadgen_voc_rows")

    op.drop_index("ix_leadgen_voc_runs_created_at", table_name="leadgen_voc_runs")
    op.drop_index("ix_leadgen_voc_runs_company_domain", table_name="leadgen_voc_runs")
    op.drop_index("ix_leadgen_voc_runs_run_id", table_name="leadgen_voc_runs")
    op.drop_table("leadgen_voc_runs")
