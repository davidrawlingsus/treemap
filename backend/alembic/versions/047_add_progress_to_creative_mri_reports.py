"""Add progress columns to creative_mri_reports for running report status

Revision ID: 047
Revises: 046
Create Date: 2026-02-11

"""
from alembic import op
import sqlalchemy as sa

revision = '047'
down_revision = '046'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('creative_mri_reports', sa.Column('progress_current', sa.Integer(), nullable=True))
    op.add_column('creative_mri_reports', sa.Column('progress_total', sa.Integer(), nullable=True))
    op.add_column('creative_mri_reports', sa.Column('progress_message', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('creative_mri_reports', 'progress_message')
    op.drop_column('creative_mri_reports', 'progress_total')
    op.drop_column('creative_mri_reports', 'progress_current')
