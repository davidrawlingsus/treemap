"""add processed column to process_voc

Revision ID: 011
Revises: 010
Create Date: 2025-01-27

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '011'
down_revision = '010'
branch_labels = None
depends_on = None


def upgrade():
    # Add processed column to process_voc table with default False
    op.add_column('process_voc', sa.Column('processed', sa.Boolean(), nullable=False, server_default='false'))
    
    # Update all existing rows to True
    op.execute("UPDATE process_voc SET processed = true")


def downgrade():
    # Remove processed column from process_voc table
    op.drop_column('process_voc', 'processed')














