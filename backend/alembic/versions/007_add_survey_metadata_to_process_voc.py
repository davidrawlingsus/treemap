"""add survey_metadata to process_voc

Revision ID: 007
Revises: 006
Create Date: 2025-11-21

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade():
    # Add survey_metadata column to process_voc table
    op.add_column('process_voc', sa.Column('survey_metadata', postgresql.JSONB(), nullable=True))


def downgrade():
    # Remove survey_metadata column from process_voc table
    op.drop_column('process_voc', 'survey_metadata')

