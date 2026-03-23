"""add_widget_survey_tables

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-03-21

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'c3d4e5f6a7b8'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- widget_surveys ---
    op.create_table(
        "widget_surveys",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("handle", sa.String(128), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("client_id", "handle", name="uq_widget_surveys_client_handle"),
    )
    op.create_index("ix_widget_surveys_client_id", "widget_surveys", ["client_id"])
    op.create_index("ix_widget_surveys_status", "widget_surveys", ["status"])

    # --- widget_survey_versions ---
    op.create_table(
        "widget_survey_versions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("survey_id", sa.Integer(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("template_key", sa.String(64), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("settings_json", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["survey_id"], ["widget_surveys.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("survey_id", "version_number", name="uq_widget_survey_versions_number"),
    )
    op.create_index("ix_widget_survey_versions_client_id", "widget_survey_versions", ["client_id"])
    op.create_index("ix_widget_survey_versions_survey_id", "widget_survey_versions", ["survey_id"])
    op.create_index("ix_widget_survey_versions_status", "widget_survey_versions", ["status"])
    op.create_index("ix_widget_survey_versions_is_active", "widget_survey_versions", ["is_active"])

    # --- widget_survey_questions ---
    op.create_table(
        "widget_survey_questions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("survey_version_id", sa.Integer(), nullable=False),
        sa.Column("question_key", sa.String(64), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("answer_type", sa.String(32), nullable=False, server_default="single_line_text"),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("options_json", postgresql.JSONB(), nullable=True),
        sa.Column("settings_json", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["survey_version_id"], ["widget_survey_versions.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("survey_version_id", "question_key", name="uq_widget_survey_questions_key"),
    )
    op.create_index("ix_widget_survey_questions_client_id", "widget_survey_questions", ["client_id"])
    op.create_index("ix_widget_survey_questions_survey_version_id", "widget_survey_questions", ["survey_version_id"])

    # --- widget_survey_question_orders ---
    op.create_table(
        "widget_survey_question_orders",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("survey_version_id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["survey_version_id"], ["widget_survey_versions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["question_id"], ["widget_survey_questions.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("survey_version_id", "question_id", name="uq_widget_survey_q_order_question"),
        sa.UniqueConstraint("survey_version_id", "position", name="uq_widget_survey_q_order_position"),
    )
    op.create_index("ix_widget_survey_question_orders_client_id", "widget_survey_question_orders", ["client_id"])
    op.create_index("ix_widget_survey_question_orders_survey_version_id", "widget_survey_question_orders", ["survey_version_id"])
    op.create_index("ix_widget_survey_question_orders_question_id", "widget_survey_question_orders", ["question_id"])

    # --- widget_survey_display_rules ---
    op.create_table(
        "widget_survey_display_rules",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("survey_version_id", sa.Integer(), nullable=False),
        sa.Column("target_question_id", sa.Integer(), nullable=False),
        sa.Column("source_question_id", sa.Integer(), nullable=False),
        sa.Column("operator", sa.String(32), nullable=False, server_default="equals"),
        sa.Column("comparison_value", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["survey_version_id"], ["widget_survey_versions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_question_id"], ["widget_survey_questions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_question_id"], ["widget_survey_questions.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_widget_survey_display_rules_client_id", "widget_survey_display_rules", ["client_id"])
    op.create_index("ix_widget_survey_display_rules_survey_version_id", "widget_survey_display_rules", ["survey_version_id"])
    op.create_index("ix_widget_survey_display_rules_target_question_id", "widget_survey_display_rules", ["target_question_id"])
    op.create_index("ix_widget_survey_display_rules_source_question_id", "widget_survey_display_rules", ["source_question_id"])

    # --- widget_survey_responses ---
    op.create_table(
        "widget_survey_responses",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("survey_id", sa.Integer(), nullable=True),
        sa.Column("survey_version_id", sa.Integer(), nullable=True),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("site_domain", sa.String(255), nullable=True),
        sa.Column("page_url", sa.Text(), nullable=True),
        sa.Column("customer_reference", sa.String(255), nullable=True),
        sa.Column("clarity_session_id", sa.String(128), nullable=True),
        sa.Column("clarity_project_id", sa.String(64), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["survey_id"], ["widget_surveys.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["survey_version_id"], ["widget_survey_versions.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("client_id", "idempotency_key", name="uq_widget_survey_responses_idempotency"),
    )
    op.create_index("ix_widget_survey_responses_client_id", "widget_survey_responses", ["client_id"])
    op.create_index("ix_widget_survey_responses_survey_id", "widget_survey_responses", ["survey_id"])
    op.create_index("ix_widget_survey_responses_survey_version_id", "widget_survey_responses", ["survey_version_id"])
    op.create_index("ix_widget_survey_responses_site_domain", "widget_survey_responses", ["site_domain"])

    # --- widget_survey_response_answers ---
    op.create_table(
        "widget_survey_response_answers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("response_id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=True),
        sa.Column("question_key", sa.String(64), nullable=True),
        sa.Column("answer_text", sa.Text(), nullable=True),
        sa.Column("answer_json", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["response_id"], ["widget_survey_responses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["question_id"], ["widget_survey_questions.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_widget_survey_response_answers_client_id", "widget_survey_response_answers", ["client_id"])
    op.create_index("ix_widget_survey_response_answers_response_id", "widget_survey_response_answers", ["response_id"])
    op.create_index("ix_widget_survey_response_answers_question_id", "widget_survey_response_answers", ["question_id"])

    # --- widget_survey_heartbeats ---
    op.create_table(
        "widget_survey_heartbeats",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("page_url", sa.Text(), nullable=False),
        sa.Column("page_url_hash", sa.String(64), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("client_id", "page_url_hash", name="uq_widget_survey_heartbeats_client_page"),
    )
    op.create_index("ix_widget_survey_heartbeats_client_id", "widget_survey_heartbeats", ["client_id"])

    # --- widget_survey_impressions ---
    op.create_table(
        "widget_survey_impressions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("survey_version_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("impression_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["survey_version_id"], ["widget_survey_versions.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("survey_version_id", "date", name="uq_widget_survey_impressions_version_date"),
    )
    op.create_index("ix_widget_survey_impressions_survey_version_id", "widget_survey_impressions", ["survey_version_id"])


def downgrade() -> None:
    op.drop_table("widget_survey_impressions")
    op.drop_table("widget_survey_heartbeats")
    op.drop_table("widget_survey_response_answers")
    op.drop_table("widget_survey_responses")
    op.drop_table("widget_survey_display_rules")
    op.drop_table("widget_survey_question_orders")
    op.drop_table("widget_survey_questions")
    op.drop_table("widget_survey_versions")
    op.drop_table("widget_surveys")
