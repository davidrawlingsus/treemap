"""Add image_analysis_json to ad_library_media for Gemini image analysis

Revision ID: 048
Revises: 047
Create Date: 2026-02-11

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '048'
down_revision = '047'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'ad_library_media',
        sa.Column('image_analysis_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade():
    op.drop_column('ad_library_media', 'image_analysis_json')
