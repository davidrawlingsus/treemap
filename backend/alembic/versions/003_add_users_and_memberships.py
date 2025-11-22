"""add users and memberships tables

Revision ID: 003
Revises: 002
Create Date: 2025-11-04

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade():
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('is_founder', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('email_verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create unique constraint on email
    op.create_unique_constraint('users_email_key', 'users', ['email'])
    
    # Create indexes for users
    op.create_index('idx_users_email', 'users', ['email'])
    op.create_index('idx_users_is_active', 'users', ['is_active'])
    op.create_index('idx_users_is_founder', 'users', ['is_founder'])
    
    # Add founder_user_id to clients table
    op.add_column('clients', sa.Column('founder_user_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        'clients_founder_user_id_fkey',
        'clients', 'users',
        ['founder_user_id'], ['id']
    )
    
    # Create memberships table
    op.create_table(
        'memberships',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False, server_default="'viewer'::character varying"),
        sa.Column('status', sa.String(length=50), nullable=False, server_default="'active'::character varying"),
        sa.Column('invited_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('invited_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('joined_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id']),
        sa.ForeignKeyConstraint(['invited_by'], ['users.id']),
        sa.UniqueConstraint('user_id', 'client_id', name='memberships_user_client_unique')
    )
    
    # Create indexes for memberships
    op.create_index('idx_memberships_user_id', 'memberships', ['user_id'])
    op.create_index('idx_memberships_client_id', 'memberships', ['client_id'])
    op.create_index('idx_memberships_role', 'memberships', ['role'])
    op.create_index('idx_memberships_status', 'memberships', ['status'])
    op.create_index('idx_memberships_user_status', 'memberships', ['user_id', 'status'])


def downgrade():
    # Drop memberships table
    op.drop_index('idx_memberships_user_status', table_name='memberships')
    op.drop_index('idx_memberships_status', table_name='memberships')
    op.drop_index('idx_memberships_role', table_name='memberships')
    op.drop_index('idx_memberships_client_id', table_name='memberships')
    op.drop_index('idx_memberships_user_id', table_name='memberships')
    op.drop_table('memberships')
    
    # Remove founder_user_id from clients
    op.drop_constraint('clients_founder_user_id_fkey', 'clients', type_='foreignkey')
    op.drop_column('clients', 'founder_user_id')
    
    # Drop users table
    op.drop_index('idx_users_is_founder', table_name='users')
    op.drop_index('idx_users_is_active', table_name='users')
    op.drop_index('idx_users_email', table_name='users')
    op.drop_constraint('users_email_key', 'users', type_='unique')
    op.drop_table('users')










