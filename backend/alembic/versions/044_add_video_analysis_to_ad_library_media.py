"""Add video_analysis_json to ad_library_media for Gemini output

Revision ID: 044
Revises: 043
Create Date: 2026-02-11

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '044'
down_revision = '043'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'ad_library_media',
        sa.Column('video_analysis_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade():
    op.drop_column('ad_library_media', 'video_analysis_json')
