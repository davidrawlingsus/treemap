"""add question_type column to process_voc

Revision ID: 025
Revises: 024
Create Date: 2025-01-XX

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '025'
down_revision = '024'
branch_labels = None
depends_on = None


def upgrade():
    # Add question_type column to process_voc table with default 'open_text'
    op.add_column('process_voc', sa.Column('question_type', sa.String(length=50), nullable=True, server_default='open_text'))
    
    # Update all existing rows to 'open_text'
    op.execute("UPDATE process_voc SET question_type = 'open_text' WHERE question_type IS NULL")


def downgrade():
    # Remove question_type column from process_voc table
    op.drop_column('process_voc', 'question_type')
