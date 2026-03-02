"""Add async Meta import fields to import_jobs

Revision ID: 056
Revises: 055
Create Date: 2026-02-28
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "056"
down_revision = "055_backfill_ad_image_perf"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("import_jobs", sa.Column("job_type", sa.String(length=50), nullable=False, server_default="meta_ads_library"))
    op.add_column("import_jobs", sa.Column("ad_account_id", sa.String(length=50), nullable=True))
    op.add_column("import_jobs", sa.Column("media_type", sa.String(length=20), nullable=True))
    op.add_column("import_jobs", sa.Column("progress_payload", sa.JSON(), nullable=True))
    op.add_column("import_jobs", sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("import_jobs", sa.Column("skipped_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("import_jobs", sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("import_jobs", sa.Column("rate_limited_until", sa.DateTime(timezone=True), nullable=True))

    op.create_index("ix_import_jobs_job_type", "import_jobs", ["job_type"])
    op.create_index("ix_import_jobs_ad_account_id", "import_jobs", ["ad_account_id"])

    op.alter_column("import_jobs", "job_type", server_default=None)
    op.alter_column("import_jobs", "failed_count", server_default=None)
    op.alter_column("import_jobs", "skipped_count", server_default=None)


def downgrade():
    op.drop_index("ix_import_jobs_ad_account_id", table_name="import_jobs")
    op.drop_index("ix_import_jobs_job_type", table_name="import_jobs")

    op.drop_column("import_jobs", "rate_limited_until")
    op.drop_column("import_jobs", "last_heartbeat_at")
    op.drop_column("import_jobs", "skipped_count")
    op.drop_column("import_jobs", "failed_count")
    op.drop_column("import_jobs", "progress_payload")
    op.drop_column("import_jobs", "media_type")
    op.drop_column("import_jobs", "ad_account_id")
    op.drop_column("import_jobs", "job_type")
