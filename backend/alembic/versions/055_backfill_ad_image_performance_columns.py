"""backfill missing ad_image_performance columns

Revision ID: 055_backfill_ad_image_perf
Revises: 054_add_ad_image_performance_table
Create Date: 2026-02-28 20:10:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


revision = "055_backfill_ad_image_perf"
down_revision = "054_add_ad_image_performance_table"
branch_labels = None
depends_on = None


def _has_column(columns: list[dict], name: str) -> bool:
    return any(c.get("name") == name for c in columns)


def _has_index(indexes: list[dict], name: str) -> bool:
    return any(i.get("name") == name for i in indexes)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table("ad_image_performance"):
        return

    columns = inspector.get_columns("ad_image_performance")
    indexes = inspector.get_indexes("ad_image_performance")

    if not _has_column(columns, "id"):
        op.add_column("ad_image_performance", sa.Column("id", postgresql.UUID(as_uuid=True), nullable=True))
        op.execute("UPDATE ad_image_performance SET id = gen_random_uuid() WHERE id IS NULL")
        op.alter_column("ad_image_performance", "id", nullable=False)
    if not _has_column(columns, "ad_image_id"):
        op.add_column("ad_image_performance", sa.Column("ad_image_id", postgresql.UUID(as_uuid=True), nullable=True))
    if not _has_column(columns, "client_id"):
        op.add_column("ad_image_performance", sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=True))
    if not _has_column(columns, "meta_ad_account_id"):
        op.add_column("ad_image_performance", sa.Column("meta_ad_account_id", sa.String(length=50), nullable=True))
    if not _has_column(columns, "meta_ad_id"):
        op.add_column("ad_image_performance", sa.Column("meta_ad_id", sa.String(length=64), nullable=True))
    if not _has_column(columns, "meta_creative_id"):
        op.add_column("ad_image_performance", sa.Column("meta_creative_id", sa.String(length=64), nullable=True))
    if not _has_column(columns, "media_key"):
        op.add_column("ad_image_performance", sa.Column("media_key", sa.String(length=128), nullable=True))
    if not _has_column(columns, "media_type"):
        op.add_column("ad_image_performance", sa.Column("media_type", sa.String(length=16), nullable=True))
    if not _has_column(columns, "ad_primary_text"):
        op.add_column("ad_image_performance", sa.Column("ad_primary_text", sa.Text(), nullable=True))
    if not _has_column(columns, "ad_headline"):
        op.add_column("ad_image_performance", sa.Column("ad_headline", sa.Text(), nullable=True))
    if not _has_column(columns, "ad_description"):
        op.add_column("ad_image_performance", sa.Column("ad_description", sa.Text(), nullable=True))
    if not _has_column(columns, "ad_call_to_action"):
        op.add_column("ad_image_performance", sa.Column("ad_call_to_action", sa.String(length=64), nullable=True))
    if not _has_column(columns, "destination_url"):
        op.add_column("ad_image_performance", sa.Column("destination_url", sa.Text(), nullable=True))
    if not _has_column(columns, "started_running_on"):
        op.add_column("ad_image_performance", sa.Column("started_running_on", sa.DateTime(timezone=True), nullable=True))
    if not _has_column(columns, "revenue"):
        op.add_column("ad_image_performance", sa.Column("revenue", sa.Numeric(precision=14, scale=2), nullable=True))
    if not _has_column(columns, "spend"):
        op.add_column("ad_image_performance", sa.Column("spend", sa.Numeric(precision=14, scale=2), nullable=True))
    if not _has_column(columns, "impressions"):
        op.add_column("ad_image_performance", sa.Column("impressions", sa.Integer(), nullable=True))
    if not _has_column(columns, "clicks"):
        op.add_column("ad_image_performance", sa.Column("clicks", sa.Integer(), nullable=True))
    if not _has_column(columns, "purchases"):
        op.add_column("ad_image_performance", sa.Column("purchases", sa.Integer(), nullable=True))
    if not _has_column(columns, "ctr"):
        op.add_column("ad_image_performance", sa.Column("ctr", sa.Numeric(precision=8, scale=4), nullable=True))
    if not _has_column(columns, "roas"):
        op.add_column("ad_image_performance", sa.Column("roas", sa.Numeric(precision=10, scale=4), nullable=True))
    if not _has_column(columns, "last_synced_at"):
        op.add_column("ad_image_performance", sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True))
    if not _has_column(columns, "created_at"):
        op.add_column(
            "ad_image_performance",
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        )
    if not _has_column(columns, "updated_at"):
        op.add_column("ad_image_performance", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))

    if not _has_index(indexes, "ix_ad_image_performance_client_id"):
        op.create_index("ix_ad_image_performance_client_id", "ad_image_performance", ["client_id"], unique=False)
    if not _has_index(indexes, "ix_ad_image_performance_media_key"):
        op.create_index("ix_ad_image_performance_media_key", "ad_image_performance", ["media_key"], unique=False)
    if not _has_index(indexes, "ix_ad_image_performance_revenue"):
        op.create_index("ix_ad_image_performance_revenue", "ad_image_performance", ["revenue"], unique=False)
    if not _has_index(indexes, "ix_ad_image_performance_roas"):
        op.create_index("ix_ad_image_performance_roas", "ad_image_performance", ["roas"], unique=False)
    if not _has_index(indexes, "ix_ad_image_performance_ctr"):
        op.create_index("ix_ad_image_performance_ctr", "ad_image_performance", ["ctr"], unique=False)
    if not _has_index(indexes, "ix_ad_image_performance_clicks"):
        op.create_index("ix_ad_image_performance_clicks", "ad_image_performance", ["clicks"], unique=False)
    if not _has_index(indexes, "ix_ad_image_performance_impressions"):
        op.create_index("ix_ad_image_performance_impressions", "ad_image_performance", ["impressions"], unique=False)
    if not _has_index(indexes, "ix_ad_image_performance_spend"):
        op.create_index("ix_ad_image_performance_spend", "ad_image_performance", ["spend"], unique=False)


def downgrade() -> None:
    # Intentionally no-op: this migration is schema-repair for drifted environments.
    pass
