"""remove individual metadata columns from process_voc

Revision ID: 010
Revises: 009
Create Date: 2025-11-21

This migration removes the individual metadata columns (region, response_type, 
user_type, start_date, submit_date) from the process_voc table since all 
metadata is now stored in the survey_metadata JSONB column.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '010'
down_revision = '009'
branch_labels = None
depends_on = None


def upgrade():
    """
    Remove individual metadata columns from process_voc table.
    All data has been migrated to survey_metadata JSONB column.
    """
    # Drop the individual metadata columns
    op.drop_column('process_voc', 'region')
    op.drop_column('process_voc', 'response_type')
    op.drop_column('process_voc', 'user_type')
    op.drop_column('process_voc', 'start_date')
    op.drop_column('process_voc', 'submit_date')


def downgrade():
    """
    Restore individual metadata columns.
    Note: This will create empty columns. To restore data, you would need to
    extract it from survey_metadata.metadata, which is not done automatically.
    """
    # Re-add the columns with their original types
    op.add_column('process_voc', sa.Column('region', sa.String(50), nullable=True))
    op.add_column('process_voc', sa.Column('response_type', sa.String(50), nullable=True))
    op.add_column('process_voc', sa.Column('user_type', sa.String(50), nullable=True))
    op.add_column('process_voc', sa.Column('start_date', sa.DateTime(timezone=True), nullable=True))
    op.add_column('process_voc', sa.Column('submit_date', sa.DateTime(timezone=True), nullable=True))

