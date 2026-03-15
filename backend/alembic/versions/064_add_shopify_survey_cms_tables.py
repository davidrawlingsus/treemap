"""add shopify survey cms tables

Revision ID: 064
Revises: 063
Create Date: 2026-03-15
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "064"
down_revision: Union[str, Sequence[str], None] = "063"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "shopify_surveys",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("shop_domain", sa.String(length=255), nullable=False),
        sa.Column("handle", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("shop_domain", "handle", name="uq_shopify_surveys_shop_handle"),
    )
    op.create_index("ix_shopify_surveys_shop_domain", "shopify_surveys", ["shop_domain"], unique=False)
    op.create_index("ix_shopify_surveys_status", "shopify_surveys", ["status"], unique=False)

    op.create_table(
        "shopify_survey_versions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("shop_domain", sa.String(length=255), nullable=False),
        sa.Column("survey_id", sa.Integer(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("template_key", sa.String(length=64), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("settings_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["survey_id"], ["shopify_surveys.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("survey_id", "version_number", name="uq_shopify_survey_versions_number"),
    )
    op.create_index("ix_shopify_survey_versions_shop_domain", "shopify_survey_versions", ["shop_domain"], unique=False)
    op.create_index("ix_shopify_survey_versions_survey_id", "shopify_survey_versions", ["survey_id"], unique=False)
    op.create_index("ix_shopify_survey_versions_status", "shopify_survey_versions", ["status"], unique=False)
    op.create_index("ix_shopify_survey_versions_is_active", "shopify_survey_versions", ["is_active"], unique=False)

    op.create_table(
        "shopify_survey_questions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("shop_domain", sa.String(length=255), nullable=False),
        sa.Column("survey_version_id", sa.Integer(), nullable=False),
        sa.Column("question_key", sa.String(length=64), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("answer_type", sa.String(length=32), nullable=False),
        sa.Column("is_required", sa.Boolean(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("options_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("settings_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["survey_version_id"], ["shopify_survey_versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("survey_version_id", "question_key", name="uq_shopify_survey_questions_key"),
    )
    op.create_index("ix_shopify_survey_questions_shop_domain", "shopify_survey_questions", ["shop_domain"], unique=False)
    op.create_index("ix_shopify_survey_questions_survey_version_id", "shopify_survey_questions", ["survey_version_id"], unique=False)

    op.create_table(
        "shopify_survey_question_orders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("shop_domain", sa.String(length=255), nullable=False),
        sa.Column("survey_version_id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["question_id"], ["shopify_survey_questions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["survey_version_id"], ["shopify_survey_versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("survey_version_id", "position", name="uq_shopify_survey_q_order_position"),
        sa.UniqueConstraint("survey_version_id", "question_id", name="uq_shopify_survey_q_order_question"),
    )
    op.create_index("ix_shopify_survey_question_orders_shop_domain", "shopify_survey_question_orders", ["shop_domain"], unique=False)
    op.create_index("ix_shopify_survey_question_orders_survey_version_id", "shopify_survey_question_orders", ["survey_version_id"], unique=False)
    op.create_index("ix_shopify_survey_question_orders_question_id", "shopify_survey_question_orders", ["question_id"], unique=False)

    op.create_table(
        "shopify_survey_display_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("shop_domain", sa.String(length=255), nullable=False),
        sa.Column("survey_version_id", sa.Integer(), nullable=False),
        sa.Column("target_question_id", sa.Integer(), nullable=False),
        sa.Column("source_question_id", sa.Integer(), nullable=False),
        sa.Column("operator", sa.String(length=32), nullable=False),
        sa.Column("comparison_value", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["source_question_id"], ["shopify_survey_questions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["survey_version_id"], ["shopify_survey_versions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_question_id"], ["shopify_survey_questions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_shopify_survey_display_rules_shop_domain", "shopify_survey_display_rules", ["shop_domain"], unique=False)
    op.create_index("ix_shopify_survey_display_rules_survey_version_id", "shopify_survey_display_rules", ["survey_version_id"], unique=False)
    op.create_index("ix_shopify_survey_display_rules_target_question_id", "shopify_survey_display_rules", ["target_question_id"], unique=False)
    op.create_index("ix_shopify_survey_display_rules_source_question_id", "shopify_survey_display_rules", ["source_question_id"], unique=False)

    op.create_table(
        "shopify_survey_responses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("shop_domain", sa.String(length=255), nullable=False),
        sa.Column("survey_id", sa.Integer(), nullable=True),
        sa.Column("survey_version_id", sa.Integer(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("shopify_order_id", sa.String(length=255), nullable=True),
        sa.Column("order_gid", sa.String(length=255), nullable=True),
        sa.Column("customer_reference", sa.String(length=255), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("extension_context_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["survey_id"], ["shopify_surveys.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["survey_version_id"], ["shopify_survey_versions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("shop_domain", "idempotency_key", name="uq_shopify_survey_responses_idempotency"),
    )
    op.create_index("ix_shopify_survey_responses_shop_domain", "shopify_survey_responses", ["shop_domain"], unique=False)
    op.create_index("ix_shopify_survey_responses_survey_id", "shopify_survey_responses", ["survey_id"], unique=False)
    op.create_index("ix_shopify_survey_responses_survey_version_id", "shopify_survey_responses", ["survey_version_id"], unique=False)
    op.create_index("ix_shopify_survey_responses_shopify_order_id", "shopify_survey_responses", ["shopify_order_id"], unique=False)

    op.create_table(
        "shopify_survey_response_answers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("shop_domain", sa.String(length=255), nullable=False),
        sa.Column("response_id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=True),
        sa.Column("question_key", sa.String(length=64), nullable=True),
        sa.Column("answer_text", sa.Text(), nullable=True),
        sa.Column("answer_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["question_id"], ["shopify_survey_questions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["response_id"], ["shopify_survey_responses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_shopify_survey_response_answers_shop_domain", "shopify_survey_response_answers", ["shop_domain"], unique=False)
    op.create_index("ix_shopify_survey_response_answers_response_id", "shopify_survey_response_answers", ["response_id"], unique=False)
    op.create_index("ix_shopify_survey_response_answers_question_id", "shopify_survey_response_answers", ["question_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_shopify_survey_response_answers_question_id", table_name="shopify_survey_response_answers")
    op.drop_index("ix_shopify_survey_response_answers_response_id", table_name="shopify_survey_response_answers")
    op.drop_index("ix_shopify_survey_response_answers_shop_domain", table_name="shopify_survey_response_answers")
    op.drop_table("shopify_survey_response_answers")

    op.drop_index("ix_shopify_survey_responses_shopify_order_id", table_name="shopify_survey_responses")
    op.drop_index("ix_shopify_survey_responses_survey_version_id", table_name="shopify_survey_responses")
    op.drop_index("ix_shopify_survey_responses_survey_id", table_name="shopify_survey_responses")
    op.drop_index("ix_shopify_survey_responses_shop_domain", table_name="shopify_survey_responses")
    op.drop_table("shopify_survey_responses")

    op.drop_index("ix_shopify_survey_display_rules_source_question_id", table_name="shopify_survey_display_rules")
    op.drop_index("ix_shopify_survey_display_rules_target_question_id", table_name="shopify_survey_display_rules")
    op.drop_index("ix_shopify_survey_display_rules_survey_version_id", table_name="shopify_survey_display_rules")
    op.drop_index("ix_shopify_survey_display_rules_shop_domain", table_name="shopify_survey_display_rules")
    op.drop_table("shopify_survey_display_rules")

    op.drop_index("ix_shopify_survey_question_orders_question_id", table_name="shopify_survey_question_orders")
    op.drop_index("ix_shopify_survey_question_orders_survey_version_id", table_name="shopify_survey_question_orders")
    op.drop_index("ix_shopify_survey_question_orders_shop_domain", table_name="shopify_survey_question_orders")
    op.drop_table("shopify_survey_question_orders")

    op.drop_index("ix_shopify_survey_questions_survey_version_id", table_name="shopify_survey_questions")
    op.drop_index("ix_shopify_survey_questions_shop_domain", table_name="shopify_survey_questions")
    op.drop_table("shopify_survey_questions")

    op.drop_index("ix_shopify_survey_versions_is_active", table_name="shopify_survey_versions")
    op.drop_index("ix_shopify_survey_versions_status", table_name="shopify_survey_versions")
    op.drop_index("ix_shopify_survey_versions_survey_id", table_name="shopify_survey_versions")
    op.drop_index("ix_shopify_survey_versions_shop_domain", table_name="shopify_survey_versions")
    op.drop_table("shopify_survey_versions")

    op.drop_index("ix_shopify_surveys_status", table_name="shopify_surveys")
    op.drop_index("ix_shopify_surveys_shop_domain", table_name="shopify_surveys")
    op.drop_table("shopify_surveys")
