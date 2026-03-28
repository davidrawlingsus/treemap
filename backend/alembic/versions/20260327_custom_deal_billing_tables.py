"""Add custom deal billing tables (custom_deals, custom_deal_phases, custom_deal_stripe_state)

Revision ID: d8e9f0a1b2c3
Revises: 2007d0bd6fd5
Create Date: 2026-03-27

This migration creates the tables for the custom deal billing flow,
which is separate from the SaaS subscription billing system.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = 'd8e9f0a1b2c3'
down_revision = '2007d0bd6fd5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'custom_deals',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('client_name', sa.String(255), nullable=False),
        sa.Column('client_email', sa.String(255), nullable=False),
        sa.Column('company_name', sa.String(255), nullable=True),
        sa.Column('deal_title', sa.String(255), nullable=False),
        sa.Column('internal_notes', sa.Text, nullable=True),
        sa.Column('currency', sa.String(3), nullable=False, server_default='gbp'),
        sa.Column('status', sa.String(50), nullable=False, server_default='draft'),
        sa.Column('public_token', sa.String(64), nullable=False, unique=True),
        sa.Column('cancellation_url', sa.Text, nullable=True),
        sa.Column('cancellation_instructions', sa.Text, nullable=True),
        sa.Column('page_headline', sa.String(500), nullable=True),
        sa.Column('page_intro', sa.Text, nullable=True),
        sa.Column('success_message', sa.Text, nullable=True),
        sa.Column('start_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_custom_deals_public_token', 'custom_deals', ['public_token'], unique=True)
    op.create_index('ix_custom_deals_status', 'custom_deals', ['status'])

    op.create_table(
        'custom_deal_phases',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('deal_id', UUID(as_uuid=True), sa.ForeignKey('custom_deals.id', ondelete='CASCADE'), nullable=False),
        sa.Column('phase_order', sa.Integer, nullable=False),
        sa.Column('label', sa.String(255), nullable=True),
        sa.Column('amount_cents', sa.Integer, nullable=False),
        sa.Column('duration_months', sa.Integer, nullable=True),
        sa.Column('is_recurring_indefinitely', sa.Boolean, nullable=False, server_default=sa.text('false')),
        sa.Column('billing_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_custom_deal_phases_deal_id', 'custom_deal_phases', ['deal_id'])

    op.create_table(
        'custom_deal_stripe_state',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('deal_id', UUID(as_uuid=True), sa.ForeignKey('custom_deals.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('stripe_customer_id', sa.String(255), nullable=True),
        sa.Column('stripe_checkout_session_id', sa.String(255), nullable=True),
        sa.Column('stripe_setup_intent_id', sa.String(255), nullable=True),
        sa.Column('stripe_payment_method_id', sa.String(255), nullable=True),
        sa.Column('stripe_subscription_schedule_id', sa.String(255), nullable=True),
        sa.Column('last_webhook_event_id', sa.String(255), nullable=True),
        sa.Column('setup_completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('schedule_created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('latest_error', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('custom_deal_stripe_state')
    op.drop_table('custom_deal_phases')
    op.drop_index('ix_custom_deals_status', table_name='custom_deals')
    op.drop_index('ix_custom_deals_public_token', table_name='custom_deals')
    op.drop_table('custom_deals')
