"""Add plans, subscriptions, and usage_records tables

Revision ID: 058
Revises: 057
Create Date: 2026-03-03
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid


revision = "058"
down_revision = "057"
branch_labels = None
depends_on = None

BASIC_PLAN_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
PRO_PLAN_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
ENTERPRISE_PLAN_ID = uuid.UUID("00000000-0000-0000-0000-000000000003")


def upgrade():
    op.create_table(
        "plans",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(50), nullable=False, unique=True),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("stripe_price_id_monthly", sa.String(255), nullable=True),
        sa.Column("stripe_price_id_annual", sa.String(255), nullable=True),
        sa.Column("price_monthly_cents", sa.Integer, nullable=False, server_default="0"),
        sa.Column("price_annual_cents", sa.Integer, nullable=False, server_default="0"),
        sa.Column("features", JSONB, nullable=False, server_default="{}"),
        sa.Column("trial_limit", sa.Integer, nullable=False, server_default="0"),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "subscriptions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("plan_id", UUID(as_uuid=True), sa.ForeignKey("plans.id"), nullable=False),
        sa.Column("stripe_customer_id", sa.String(255), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(255), nullable=True, unique=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("metadata", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "usage_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("clients.id"), nullable=False, index=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("action_type", sa.String(50), nullable=False, index=True),
        sa.Column("prompt_id", UUID(as_uuid=True), nullable=True),
        sa.Column("metadata", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    plans = sa.table(
        "plans",
        sa.column("id", UUID(as_uuid=True)),
        sa.column("name", sa.String),
        sa.column("display_name", sa.String),
        sa.column("price_monthly_cents", sa.Integer),
        sa.column("price_annual_cents", sa.Integer),
        sa.column("features", JSONB),
        sa.column("trial_limit", sa.Integer),
        sa.column("sort_order", sa.Integer),
        sa.column("is_active", sa.Boolean),
    )
    op.bulk_insert(plans, [
        {
            "id": BASIC_PLAN_ID,
            "name": "basic",
            "display_name": "Basic",
            "price_monthly_cents": 0,
            "price_annual_cents": 0,
            "features": {
                "visualizations": True,
                "verbatims": True,
                "manual_insights": True,
                "history": True,
                "add_data": True,
                "context_menu_prompts": True,
                "ads": True,
                "emails": True,
                "media": True,
                "settings": False,
                "product_context": False,
            },
            "trial_limit": 5,
            "sort_order": 0,
            "is_active": True,
        },
        {
            "id": PRO_PLAN_ID,
            "name": "pro",
            "display_name": "Pro",
            "price_monthly_cents": 0,
            "price_annual_cents": 0,
            "features": {
                "visualizations": True,
                "verbatims": True,
                "manual_insights": True,
                "history": True,
                "add_data": True,
                "context_menu_prompts": True,
                "ads": True,
                "emails": True,
                "media": True,
                "settings": True,
                "product_context": True,
            },
            "trial_limit": 0,
            "sort_order": 1,
            "is_active": True,
        },
        {
            "id": ENTERPRISE_PLAN_ID,
            "name": "enterprise",
            "display_name": "Enterprise",
            "price_monthly_cents": 0,
            "price_annual_cents": 0,
            "features": {
                "visualizations": True,
                "verbatims": True,
                "manual_insights": True,
                "history": True,
                "add_data": True,
                "context_menu_prompts": True,
                "ads": True,
                "emails": True,
                "media": True,
                "settings": True,
                "product_context": True,
            },
            "trial_limit": 0,
            "sort_order": 2,
            "is_active": True,
        },
    ])


def downgrade():
    op.drop_table("usage_records")
    op.drop_table("subscriptions")
    op.drop_table("plans")
