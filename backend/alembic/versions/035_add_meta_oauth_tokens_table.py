"""add meta_oauth_tokens table

Revision ID: 035
Revises: 034
Create Date: 2026-01-30

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '035'
down_revision = '034'
branch_labels = None
depends_on = None


def upgrade():
    # Create meta_oauth_tokens table
    op.create_table(
        'meta_oauth_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('access_token', sa.Text(), nullable=False),
        sa.Column('token_type', sa.String(length=50), nullable=False, server_default='bearer'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('meta_user_id', sa.String(length=100), nullable=True),
        sa.Column('meta_user_name', sa.String(length=255), nullable=True),
        sa.Column('default_ad_account_id', sa.String(length=100), nullable=True),
        sa.Column('default_ad_account_name', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('client_id', name='uq_meta_oauth_tokens_client_id')
    )
    
    # Create indexes
    op.create_index('ix_meta_oauth_tokens_client_id', 'meta_oauth_tokens', ['client_id'])


def downgrade():
    # Drop indexes
    op.drop_index('ix_meta_oauth_tokens_client_id', table_name='meta_oauth_tokens')
    
    # Drop table
    op.drop_table('meta_oauth_tokens')
