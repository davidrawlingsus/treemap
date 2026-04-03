"""Add screenshot_url to clients

Revision ID: a1b2c3d4e5f6
Revises: 9b866cba9214
Create Date: 2026-04-03
"""
from alembic import op
import sqlalchemy as sa

revision = 'f7e8d9c0b1a2'
down_revision = '9b866cba9214'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('clients', sa.Column('screenshot_url', sa.String(500), nullable=True))


def downgrade():
    op.drop_column('clients', 'screenshot_url')
