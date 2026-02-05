"""add saved_emails table

Revision ID: 036
Revises: 035_add_meta_oauth_tokens_table
Create Date: 2026-02-04

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '036'
down_revision = '035'
branch_labels = None
depends_on = None


def upgrade():
    # Create saved_emails table
    op.create_table(
        'saved_emails',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('action_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('email_type', sa.String(length=100), nullable=True),
        sa.Column('subject_line', sa.String(length=255), nullable=False),
        sa.Column('preview_text', sa.String(length=255), nullable=True),
        sa.Column('from_name', sa.String(length=100), nullable=True),
        sa.Column('headline', sa.String(length=255), nullable=True),
        sa.Column('body_text', sa.Text(), nullable=False),
        sa.Column('discount_code', sa.String(length=50), nullable=True),
        sa.Column('social_proof', sa.Text(), nullable=True),
        sa.Column('cta_text', sa.String(length=100), nullable=True),
        sa.Column('cta_url', sa.Text(), nullable=True),
        sa.Column('sequence_position', sa.Integer(), nullable=True),
        sa.Column('send_delay_hours', sa.Integer(), nullable=True),
        sa.Column('voc_evidence', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='[]'),
        sa.Column('strategic_intent', sa.Text(), nullable=True),
        sa.Column('full_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='draft'),
        sa.Column('klaviyo_campaign_id', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['action_id'], ['actions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL')
    )
    
    # Create indexes
    op.create_index('ix_saved_emails_client_id', 'saved_emails', ['client_id'])
    op.create_index('ix_saved_emails_email_type', 'saved_emails', ['email_type'])
    op.create_index('ix_saved_emails_status', 'saved_emails', ['status'])
    op.create_index('ix_saved_emails_created_at', 'saved_emails', ['created_at'])


def downgrade():
    # Drop indexes
    op.drop_index('ix_saved_emails_created_at', table_name='saved_emails')
    op.drop_index('ix_saved_emails_status', table_name='saved_emails')
    op.drop_index('ix_saved_emails_email_type', table_name='saved_emails')
    op.drop_index('ix_saved_emails_client_id', table_name='saved_emails')
    
    # Drop table
    op.drop_table('saved_emails')
