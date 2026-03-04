"""
Pydantic schemas for subscription and billing management.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class PlanResponse(BaseModel):
    id: UUID
    name: str
    display_name: str
    price_monthly_cents: int
    price_annual_cents: int
    features: dict
    trial_limit: int
    sort_order: int
    is_active: bool

    class Config:
        from_attributes = True


class SubscriptionResponse(BaseModel):
    id: UUID
    client_id: UUID
    plan_id: UUID
    plan_name: str
    plan_display_name: str
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    status: str
    is_manual_override: bool
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ClientSubscriptionSummary(BaseModel):
    client_id: UUID
    client_name: str
    client_slug: str
    plan_name: Optional[str] = None
    plan_display_name: Optional[str] = None
    subscription_status: Optional[str] = None
    is_manual_override: bool = False
    trial_limit: int = 0
    trial_uses: int = 0
    subscription_id: Optional[UUID] = None

    class Config:
        from_attributes = True


class SubscriptionCreateRequest(BaseModel):
    client_id: UUID
    plan_id: UUID
    is_manual_override: bool = True
    status: str = "active"


class SubscriptionUpdateRequest(BaseModel):
    plan_id: Optional[UUID] = None
    is_manual_override: Optional[bool] = None
    status: Optional[str] = None


class PlanUpdateRequest(BaseModel):
    trial_limit: Optional[int] = None
    features: Optional[dict] = None
    price_monthly_cents: Optional[int] = None
    price_annual_cents: Optional[int] = None


class UsageRecordResponse(BaseModel):
    id: UUID
    client_id: UUID
    user_id: UUID
    user_email: Optional[str] = None
    action_type: str
    prompt_id: Optional[UUID] = None
    usage_metadata: Optional[dict] = None
    created_at: datetime

    class Config:
        from_attributes = True
