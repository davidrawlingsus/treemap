"""add ad_image_performance table

Revision ID: 054_add_ad_image_performance_table
Revises: 053
Create Date: 2026-02-28 18:15:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "054_add_ad_image_performance_table"
down_revision = "053"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not inspector.has_table("ad_image_performance"):
        op.create_table(
            "ad_image_performance",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("ad_image_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("meta_ad_account_id", sa.String(length=50), nullable=True),
            sa.Column("meta_ad_id", sa.String(length=64), nullable=True),
            sa.Column("meta_creative_id", sa.String(length=64), nullable=True),
            sa.Column("media_key", sa.String(length=128), nullable=True),
            sa.Column("media_type", sa.String(length=16), nullable=True),
            sa.Column("ad_primary_text", sa.Text(), nullable=True),
            sa.Column("ad_headline", sa.Text(), nullable=True),
            sa.Column("ad_description", sa.Text(), nullable=True),
            sa.Column("ad_call_to_action", sa.String(length=64), nullable=True),
            sa.Column("destination_url", sa.Text(), nullable=True),
            sa.Column("started_running_on", sa.DateTime(timezone=True), nullable=True),
            sa.Column("revenue", sa.Numeric(precision=14, scale=2), nullable=True),
            sa.Column("spend", sa.Numeric(precision=14, scale=2), nullable=True),
            sa.Column("impressions", sa.Integer(), nullable=True),
            sa.Column("clicks", sa.Integer(), nullable=True),
            sa.Column("purchases", sa.Integer(), nullable=True),
            sa.Column("ctr", sa.Numeric(precision=8, scale=4), nullable=True),
            sa.Column("roas", sa.Numeric(precision=10, scale=4), nullable=True),
            sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["ad_image_id"], ["ad_images.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("ad_image_id"),
        )
        op.create_index("ix_ad_image_performance_client_id", "ad_image_performance", ["client_id"], unique=False)
        op.create_index("ix_ad_image_performance_media_key", "ad_image_performance", ["media_key"], unique=False)
        op.create_index("ix_ad_image_performance_revenue", "ad_image_performance", ["revenue"], unique=False)
        op.create_index("ix_ad_image_performance_roas", "ad_image_performance", ["roas"], unique=False)
        op.create_index("ix_ad_image_performance_ctr", "ad_image_performance", ["ctr"], unique=False)
        op.create_index("ix_ad_image_performance_clicks", "ad_image_performance", ["clicks"], unique=False)
        op.create_index("ix_ad_image_performance_impressions", "ad_image_performance", ["impressions"], unique=False)
        op.create_index("ix_ad_image_performance_spend", "ad_image_performance", ["spend"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if inspector.has_table("ad_image_performance"):
        op.drop_index("ix_ad_image_performance_spend", table_name="ad_image_performance")
        op.drop_index("ix_ad_image_performance_impressions", table_name="ad_image_performance")
        op.drop_index("ix_ad_image_performance_clicks", table_name="ad_image_performance")
        op.drop_index("ix_ad_image_performance_ctr", table_name="ad_image_performance")
        op.drop_index("ix_ad_image_performance_roas", table_name="ad_image_performance")
        op.drop_index("ix_ad_image_performance_revenue", table_name="ad_image_performance")
        op.drop_index("ix_ad_image_performance_media_key", table_name="ad_image_performance")
        op.drop_index("ix_ad_image_performance_client_id", table_name="ad_image_performance")
        op.drop_table("ad_image_performance")
