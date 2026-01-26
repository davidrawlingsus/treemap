"""add facebook_ads table

Revision ID: 032
Revises: 031_normalize_hero_concept_type
Create Date: 2025-01-25

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '032'
down_revision = '031'
branch_labels = None
depends_on = None


def upgrade():
    # Create facebook_ads table
    op.create_table(
        'facebook_ads',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('insight_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('primary_text', sa.Text(), nullable=False),
        sa.Column('headline', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('call_to_action', sa.String(length=50), nullable=False),
        sa.Column('destination_url', sa.Text(), nullable=True),
        sa.Column('image_hash', sa.Text(), nullable=True),
        sa.Column('voc_evidence', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='[]'),
        sa.Column('full_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='draft'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['insight_id'], ['insights.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['action_id'], ['actions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL')
    )
    
    # Create indexes
    op.create_index('ix_facebook_ads_client_id', 'facebook_ads', ['client_id'])
    op.create_index('ix_facebook_ads_status', 'facebook_ads', ['status'])
    op.create_index('ix_facebook_ads_created_at', 'facebook_ads', ['created_at'])


def downgrade():
    # Drop indexes
    op.drop_index('ix_facebook_ads_created_at', table_name='facebook_ads')
    op.drop_index('ix_facebook_ads_status', table_name='facebook_ads')
    op.drop_index('ix_facebook_ads_client_id', table_name='facebook_ads')
    
    # Drop table
    op.drop_table('facebook_ads')
