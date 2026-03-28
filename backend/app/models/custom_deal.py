"""
Custom Deal models for founder-negotiated bespoke billing agreements.

These are completely separate from the SaaS subscription models (Plan, Subscription).
Custom deals support phased billing schedules managed via Stripe Subscription Schedules.
"""
import uuid
from sqlalchemy import (
    Column, String, Integer, DateTime, Boolean, ForeignKey, Text, Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from app.database import Base


class DealStatus(str, enum.Enum):
    draft = "draft"
    page_generated = "page_generated"
    awaiting_card_setup = "awaiting_card_setup"
    card_captured = "card_captured"
    billing_schedule_active = "billing_schedule_active"
    cancelled = "cancelled"
    payment_failed = "payment_failed"
    completed = "completed"


class CustomDeal(Base):
    """A founder-negotiated bespoke deal with phased billing."""
    __tablename__ = "custom_deals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_name = Column(String(255), nullable=False)
    client_email = Column(String(255), nullable=False)
    company_name = Column(String(255), nullable=True)
    deal_title = Column(String(255), nullable=False)
    internal_notes = Column(Text, nullable=True)
    currency = Column(String(3), nullable=False, default="gbp")
    status = Column(
        SAEnum(DealStatus, name="deal_status", create_constraint=False),
        nullable=False,
        default=DealStatus.draft,
    )
    # Link to existing client record (optional — for co-branding with logo)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=True)
    # Secure unguessable token for public URL
    public_token = Column(String(64), nullable=False, unique=True)
    # Custom page copy
    cancellation_url = Column(Text, nullable=True)
    cancellation_instructions = Column(Text, nullable=True)
    page_headline = Column(String(500), nullable=True)
    page_intro = Column(Text, nullable=True)
    success_message = Column(Text, nullable=True)
    pause_cancel_text = Column(Text, nullable=True)
    no_charge_text = Column(Text, nullable=True)
    # Project start date (anchor for billing phases)
    start_date = Column(DateTime(timezone=True), nullable=True)
    # Track who created it
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    phases = relationship("CustomDealPhase", back_populates="deal", order_by="CustomDealPhase.phase_order", cascade="all, delete-orphan")
    stripe_state = relationship("CustomDealStripeState", back_populates="deal", uselist=False, cascade="all, delete-orphan")
    creator = relationship("User", foreign_keys=[created_by])
    client = relationship("Client", foreign_keys=[client_id])

    def __repr__(self):
        return f"<CustomDeal(id={self.id}, title='{self.deal_title}', status={self.status})>"


class CustomDealPhase(Base):
    """A billing phase within a custom deal (e.g. month 1: 8000, month 2: 6000, then recurring 5000)."""
    __tablename__ = "custom_deal_phases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deal_id = Column(UUID(as_uuid=True), ForeignKey("custom_deals.id", ondelete="CASCADE"), nullable=False)
    phase_order = Column(Integer, nullable=False)
    label = Column(String(255), nullable=True)  # e.g. "Project begins", "Month 2"
    amount_cents = Column(Integer, nullable=False)  # Amount in smallest currency unit
    duration_months = Column(Integer, nullable=True)  # null for indefinite recurring
    is_recurring_indefinitely = Column(Boolean, nullable=False, default=False)
    # Specific billing date override (if null, derived from deal start_date + phase offsets)
    billing_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    deal = relationship("CustomDeal", back_populates="phases")

    def __repr__(self):
        return f"<CustomDealPhase(order={self.phase_order}, amount={self.amount_cents}, recurring={self.is_recurring_indefinitely})>"


class CustomDealStripeState(Base):
    """Stripe integration state for a custom deal. Tracks checkout, payment method, and schedule."""
    __tablename__ = "custom_deal_stripe_state"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deal_id = Column(UUID(as_uuid=True), ForeignKey("custom_deals.id", ondelete="CASCADE"), nullable=False, unique=True)
    stripe_customer_id = Column(String(255), nullable=True)
    stripe_checkout_session_id = Column(String(255), nullable=True)
    stripe_setup_intent_id = Column(String(255), nullable=True)
    stripe_payment_method_id = Column(String(255), nullable=True)
    stripe_subscription_schedule_id = Column(String(255), nullable=True)
    last_webhook_event_id = Column(String(255), nullable=True)
    setup_completed_at = Column(DateTime(timezone=True), nullable=True)
    schedule_created_at = Column(DateTime(timezone=True), nullable=True)
    latest_error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    deal = relationship("CustomDeal", back_populates="stripe_state")

    def __repr__(self):
        return f"<CustomDealStripeState(deal_id={self.deal_id}, schedule={self.stripe_subscription_schedule_id})>"
