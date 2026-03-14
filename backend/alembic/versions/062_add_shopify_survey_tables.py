"""add shopify survey tables

Revision ID: 062
Revises: 061
Create Date: 2026-03-13
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "062"
down_revision = "061"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "shopify_store_connections",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("shop_domain", sa.String(length=255), nullable=False),
        sa.Column("client_uuid", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="active"),
        sa.Column("installed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("uninstalled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["client_uuid"], ["clients.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("shop_domain"),
    )
    op.create_index("ix_shopify_store_connections_shop_domain", "shopify_store_connections", ["shop_domain"], unique=True)
    op.create_index("ix_shopify_store_connections_client_uuid", "shopify_store_connections", ["client_uuid"], unique=False)

    op.create_table(
        "shopify_survey_responses_raw",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("shop_domain", sa.String(length=255), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("shopify_order_id", sa.String(length=255), nullable=True),
        sa.Column("order_gid", sa.String(length=255), nullable=True),
        sa.Column("customer_reference", sa.String(length=255), nullable=True),
        sa.Column("survey_version", sa.String(length=50), nullable=False, server_default="v1"),
        sa.Column("answers_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("extension_context_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("client_uuid", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["client_uuid"], ["clients.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "shop_domain",
            "shopify_order_id",
            "survey_version",
            name="uq_shopify_survey_responses_shop_order_version",
        ),
        sa.UniqueConstraint(
            "shop_domain",
            "idempotency_key",
            name="uq_shopify_survey_responses_shop_idempotency",
        ),
    )
    op.create_index(
        "ix_shopify_survey_responses_raw_shop_domain",
        "shopify_survey_responses_raw",
        ["shop_domain"],
        unique=False,
    )
    op.create_index(
        "ix_shopify_survey_responses_raw_client_uuid",
        "shopify_survey_responses_raw",
        ["client_uuid"],
        unique=False,
    )
    op.create_index(
        "ix_shopify_survey_responses_raw_shopify_order_id",
        "shopify_survey_responses_raw",
        ["shopify_order_id"],
        unique=False,
    )
    op.create_index(
        "ix_shopify_survey_responses_raw_submitted_at",
        "shopify_survey_responses_raw",
        ["submitted_at"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_shopify_survey_responses_raw_submitted_at", table_name="shopify_survey_responses_raw")
    op.drop_index("ix_shopify_survey_responses_raw_shopify_order_id", table_name="shopify_survey_responses_raw")
    op.drop_index("ix_shopify_survey_responses_raw_client_uuid", table_name="shopify_survey_responses_raw")
    op.drop_index("ix_shopify_survey_responses_raw_shop_domain", table_name="shopify_survey_responses_raw")
    op.drop_table("shopify_survey_responses_raw")

    op.drop_index("ix_shopify_store_connections_client_uuid", table_name="shopify_store_connections")
    op.drop_index("ix_shopify_store_connections_shop_domain", table_name="shopify_store_connections")
    op.drop_table("shopify_store_connections")
