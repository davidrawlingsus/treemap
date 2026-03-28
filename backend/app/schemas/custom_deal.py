"""
Pydantic schemas for the custom deal billing flow.
Completely separate from SaaS billing schemas.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


# --- Phase schemas ---

class DealPhaseCreate(BaseModel):
    phase_order: int = Field(ge=0)
    label: Optional[str] = None
    amount_cents: int = Field(gt=0)
    duration_months: Optional[int] = Field(default=None, ge=1)
    is_recurring_indefinitely: bool = False
    billing_date: Optional[datetime] = None

    @model_validator(mode="after")
    def validate_duration_vs_recurring(self):
        if self.is_recurring_indefinitely and self.duration_months is not None:
            raise ValueError("Indefinitely recurring phases must not have duration_months set")
        if not self.is_recurring_indefinitely and self.duration_months is None:
            raise ValueError("Non-recurring phases must specify duration_months")
        return self


class DealPhaseResponse(BaseModel):
    id: UUID
    deal_id: UUID
    phase_order: int
    label: Optional[str]
    amount_cents: int
    duration_months: Optional[int]
    is_recurring_indefinitely: bool
    billing_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# --- Stripe state schema ---

class DealStripeStateResponse(BaseModel):
    stripe_customer_id: Optional[str] = None
    stripe_checkout_session_id: Optional[str] = None
    stripe_setup_intent_id: Optional[str] = None
    stripe_payment_method_id: Optional[str] = None
    stripe_subscription_schedule_id: Optional[str] = None
    last_webhook_event_id: Optional[str] = None
    setup_completed_at: Optional[datetime] = None
    schedule_created_at: Optional[datetime] = None
    latest_error: Optional[str] = None

    class Config:
        from_attributes = True


# --- Deal schemas ---

class CustomDealCreate(BaseModel):
    client_name: str = Field(min_length=1, max_length=255)
    client_email: str = Field(min_length=1, max_length=255)
    company_name: Optional[str] = None
    client_id: Optional[UUID] = None  # Link to existing client for co-branding
    deal_title: str = Field(min_length=1, max_length=255)
    internal_notes: Optional[str] = None
    currency: str = Field(default="gbp", min_length=3, max_length=3)
    cancellation_url: Optional[str] = None
    cancellation_instructions: Optional[str] = None
    page_headline: Optional[str] = None
    page_intro: Optional[str] = None
    success_message: Optional[str] = None
    pause_cancel_text: Optional[str] = None
    no_charge_text: Optional[str] = None
    founder_brand: Optional[str] = "mapthegap"
    start_date: Optional[datetime] = None
    phases: list[DealPhaseCreate] = Field(min_length=1)

    @field_validator("phases")
    @classmethod
    def validate_phases(cls, v):
        orders = [p.phase_order for p in v]
        if len(orders) != len(set(orders)):
            raise ValueError("Phase orders must be unique")
        # Exactly one phase should be recurring indefinitely (the last one)
        recurring = [p for p in v if p.is_recurring_indefinitely]
        if len(recurring) > 1:
            raise ValueError("At most one phase can be recurring indefinitely")
        if recurring:
            max_order = max(p.phase_order for p in v)
            if recurring[0].phase_order != max_order:
                raise ValueError("The recurring indefinite phase must be the last phase (highest order)")
        return v


class CustomDealUpdate(BaseModel):
    client_name: Optional[str] = None
    client_email: Optional[str] = None
    company_name: Optional[str] = None
    client_id: Optional[UUID] = None
    deal_title: Optional[str] = None
    internal_notes: Optional[str] = None
    currency: Optional[str] = None
    cancellation_url: Optional[str] = None
    cancellation_instructions: Optional[str] = None
    page_headline: Optional[str] = None
    page_intro: Optional[str] = None
    success_message: Optional[str] = None
    pause_cancel_text: Optional[str] = None
    no_charge_text: Optional[str] = None
    founder_brand: Optional[str] = None
    start_date: Optional[datetime] = None
    phases: Optional[list[DealPhaseCreate]] = None

    @field_validator("phases")
    @classmethod
    def validate_phases(cls, v):
        if v is None:
            return v
        if len(v) == 0:
            raise ValueError("At least one phase is required")
        orders = [p.phase_order for p in v]
        if len(orders) != len(set(orders)):
            raise ValueError("Phase orders must be unique")
        recurring = [p for p in v if p.is_recurring_indefinitely]
        if len(recurring) > 1:
            raise ValueError("At most one phase can be recurring indefinitely")
        if recurring:
            max_order = max(p.phase_order for p in v)
            if recurring[0].phase_order != max_order:
                raise ValueError("The recurring indefinite phase must be the last phase (highest order)")
        return v


class CustomDealResponse(BaseModel):
    id: UUID
    client_name: str
    client_email: str
    company_name: Optional[str]
    client_id: Optional[UUID] = None
    deal_title: str
    internal_notes: Optional[str]
    currency: str
    status: str
    public_token: str
    cancellation_url: Optional[str]
    cancellation_instructions: Optional[str]
    page_headline: Optional[str]
    page_intro: Optional[str]
    success_message: Optional[str]
    pause_cancel_text: Optional[str] = None
    no_charge_text: Optional[str] = None
    founder_brand: Optional[str] = None
    start_date: Optional[datetime]
    created_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime
    phases: list[DealPhaseResponse] = []
    stripe_state: Optional[DealStripeStateResponse] = None

    class Config:
        from_attributes = True


class CustomDealListResponse(BaseModel):
    id: UUID
    client_name: str
    client_email: str
    company_name: Optional[str]
    deal_title: str
    currency: str
    status: str
    public_token: str
    start_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# --- Public page schema (no sensitive data) ---

class PublicDealPhaseResponse(BaseModel):
    label: Optional[str]
    amount_cents: int
    is_recurring_indefinitely: bool
    billing_date: Optional[datetime]
    computed_billing_date: Optional[datetime] = None  # Derived from start_date + phase offset
    duration_months: Optional[int]

    class Config:
        from_attributes = True


class PublicDealPageResponse(BaseModel):
    deal_title: str
    company_name: Optional[str]
    logo_url: Optional[str] = None  # From linked client, for co-branding
    currency: str
    status: str
    page_headline: Optional[str]
    page_intro: Optional[str]
    cancellation_url: Optional[str]
    cancellation_instructions: Optional[str]
    success_message: Optional[str] = None
    pause_cancel_text: Optional[str] = None
    no_charge_text: Optional[str] = None
    founder_brand: Optional[str] = None
    phases: list[PublicDealPhaseResponse]


# --- Checkout session ---

class DealCheckoutSessionResponse(BaseModel):
    client_secret: str
