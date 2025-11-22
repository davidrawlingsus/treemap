"""add question_text to process_voc

Revision ID: 008
Revises: 007
Create Date: 2025-11-21

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade():
    # Add question_text column to process_voc table
    op.add_column('process_voc', sa.Column('question_text', sa.Text(), nullable=True))


def downgrade():
    # Remove question_text column from process_voc table
    op.drop_column('process_voc', 'question_text')

