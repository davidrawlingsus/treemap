"""change application column to JSONB array

Revision ID: 023
Revises: 022
Create Date: 2025-01-XX

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = '023'
down_revision = '022'
branch_labels = None
depends_on = None


def upgrade():
    # Step 1: Add a temporary column for JSONB array
    op.add_column('insights', sa.Column('application_jsonb', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    
    # Step 2: Migrate existing data: convert comma-separated text to JSONB array
    # Split comma-separated values, trim whitespace, filter empty strings, convert to JSONB array
    op.execute("""
        UPDATE insights
        SET application_jsonb = CASE
            WHEN application IS NULL OR application = '' THEN NULL
            ELSE (
                SELECT jsonb_agg(trimmed_value)
                FROM (
                    SELECT trim(unnest(string_to_array(application, ','))) AS trimmed_value
                ) AS split_values
                WHERE trimmed_value != ''
            )::jsonb
        END
    """)
    
    # Step 3: Drop the old text column
    op.drop_column('insights', 'application')
    
    # Step 4: Rename the new column to application
    op.alter_column('insights', 'application_jsonb', new_column_name='application')
    
    # Step 5: Create GIN index for efficient JSONB array queries
    op.execute('CREATE INDEX ix_insights_application ON insights USING GIN (application)')


def downgrade():
    # Drop the GIN index
    op.drop_index('ix_insights_application', table_name='insights')
    
    # Rename column back
    op.alter_column('insights', 'application', new_column_name='application_jsonb')
    
    # Add back text column
    op.add_column('insights', sa.Column('application', sa.Text(), nullable=True))
    
    # Convert JSONB array back to comma-separated text
    op.execute("""
        UPDATE insights
        SET application = CASE
            WHEN application_jsonb IS NULL THEN NULL
            ELSE array_to_string(
                ARRAY(SELECT jsonb_array_elements_text(application_jsonb)),
                ', '
            )
        END
    """)
    
    # Drop the JSONB column
    op.drop_column('insights', 'application_jsonb')
