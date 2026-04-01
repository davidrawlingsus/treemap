"""add lead_email_queue table

Revision ID: 9b866cba9214
Revises: c4d5e6f7a8b9
Create Date: 2026-04-01

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


revision = "9b866cba9214"
down_revision = "c4d5e6f7a8b9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lead_email_queue",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("run_id", sa.String(64), sa.ForeignKey("leadgen_voc_runs.run_id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("email_address", sa.String(255), nullable=False),
        sa.Column("subject", sa.String(500), nullable=False),
        sa.Column("preview_text", sa.String(255), nullable=True),
        sa.Column("template_data", JSONB, nullable=True),
        sa.Column("html_body", sa.Text(), nullable=True),
        sa.Column("text_body", sa.Text(), nullable=True),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("resend_email_id", sa.String(100), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("clicked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("extra_data", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_lead_email_queue_status_scheduled", "lead_email_queue", ["status", "scheduled_for"])


def downgrade() -> None:
    op.drop_index("ix_lead_email_queue_status_scheduled", table_name="lead_email_queue")
    op.drop_table("lead_email_queue")
