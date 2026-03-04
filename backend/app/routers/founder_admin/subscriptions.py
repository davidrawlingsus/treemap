"""
Subscription management routes for founder admin.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from uuid import UUID
from typing import List, Optional

from app.database import get_db
from app.models import Client, Plan, Subscription, UsageRecord, User
from app.schemas.billing import (
    PlanResponse,
    PlanUpdateRequest,
    SubscriptionCreateRequest,
    SubscriptionUpdateRequest,
    ClientSubscriptionSummary,
    SubscriptionResponse,
    UsageRecordResponse,
)
from app.auth import get_current_active_founder

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/api/founder/plans", response_model=List[PlanResponse])
def list_plans(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """List all plans."""
    plans = db.query(Plan).order_by(Plan.sort_order).all()
    return plans


@router.put("/api/founder/plans/{plan_id}", response_model=PlanResponse)
def update_plan(
    plan_id: UUID,
    body: PlanUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Update a plan's trial_limit, features, or pricing."""
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    if body.trial_limit is not None:
        plan.trial_limit = body.trial_limit
    if body.features is not None:
        plan.features = body.features
    if body.price_monthly_cents is not None:
        plan.price_monthly_cents = body.price_monthly_cents
    if body.price_annual_cents is not None:
        plan.price_annual_cents = body.price_annual_cents

    db.commit()
    db.refresh(plan)
    return plan


@router.get("/api/founder/subscriptions", response_model=List[ClientSubscriptionSummary])
def list_subscriptions(
    plan_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """List all clients with their subscription status and trial usage."""
    clients = (
        db.query(Client)
        .options(joinedload(Client.subscription).joinedload(Subscription.plan))
        .filter(Client.is_active == True)
        .order_by(func.lower(Client.name))
        .all()
    )

    usage_counts = dict(
        db.query(UsageRecord.client_id, func.count(UsageRecord.id))
        .filter(UsageRecord.action_type == "prompt_execution")
        .group_by(UsageRecord.client_id)
        .all()
    )

    results = []
    for client in clients:
        sub = client.subscription
        plan = sub.plan if sub else None

        if plan_filter and (not plan or plan.name != plan_filter):
            continue

        results.append(ClientSubscriptionSummary(
            client_id=client.id,
            client_name=client.name,
            client_slug=client.slug,
            plan_name=plan.name if plan else None,
            plan_display_name=plan.display_name if plan else None,
            subscription_status=sub.status if sub else None,
            is_manual_override=sub.is_manual_override if sub else False,
            trial_limit=plan.trial_limit if plan else 0,
            trial_uses=usage_counts.get(client.id, 0),
            subscription_id=sub.id if sub else None,
        ))

    return results


@router.post("/api/founder/subscriptions", response_model=SubscriptionResponse)
def create_subscription(
    body: SubscriptionCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Create a subscription for a client (typically as manual override)."""
    client = db.query(Client).filter(Client.id == body.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    plan = db.query(Plan).filter(Plan.id == body.plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    existing = db.query(Subscription).filter(Subscription.client_id == body.client_id).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail="Client already has a subscription. Use PUT to update it.",
        )

    subscription = Subscription(
        client_id=body.client_id,
        plan_id=body.plan_id,
        is_manual_override=body.is_manual_override,
        status=body.status,
    )
    db.add(subscription)
    db.commit()
    db.refresh(subscription)

    plan = db.query(Plan).filter(Plan.id == subscription.plan_id).first()
    return SubscriptionResponse(
        id=subscription.id,
        client_id=subscription.client_id,
        plan_id=subscription.plan_id,
        plan_name=plan.name,
        plan_display_name=plan.display_name,
        stripe_customer_id=subscription.stripe_customer_id,
        stripe_subscription_id=subscription.stripe_subscription_id,
        status=subscription.status,
        is_manual_override=subscription.is_manual_override,
        current_period_start=subscription.current_period_start,
        current_period_end=subscription.current_period_end,
        cancel_at_period_end=subscription.cancel_at_period_end,
        created_at=subscription.created_at,
        updated_at=subscription.updated_at,
    )


@router.put("/api/founder/subscriptions/{client_id}", response_model=SubscriptionResponse)
def update_subscription(
    client_id: UUID,
    body: SubscriptionUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Update a client's subscription (change plan, toggle override, change status)."""
    subscription = db.query(Subscription).filter(Subscription.client_id == client_id).first()
    if not subscription:
        raise HTTPException(status_code=404, detail="No subscription found for this client")

    if body.plan_id is not None:
        plan = db.query(Plan).filter(Plan.id == body.plan_id).first()
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
        subscription.plan_id = body.plan_id

    if body.is_manual_override is not None:
        subscription.is_manual_override = body.is_manual_override

    if body.status is not None:
        subscription.status = body.status

    db.commit()
    db.refresh(subscription)

    plan = db.query(Plan).filter(Plan.id == subscription.plan_id).first()
    return SubscriptionResponse(
        id=subscription.id,
        client_id=subscription.client_id,
        plan_id=subscription.plan_id,
        plan_name=plan.name,
        plan_display_name=plan.display_name,
        stripe_customer_id=subscription.stripe_customer_id,
        stripe_subscription_id=subscription.stripe_subscription_id,
        status=subscription.status,
        is_manual_override=subscription.is_manual_override,
        current_period_start=subscription.current_period_start,
        current_period_end=subscription.current_period_end,
        cancel_at_period_end=subscription.cancel_at_period_end,
        created_at=subscription.created_at,
        updated_at=subscription.updated_at,
    )


@router.delete("/api/founder/subscriptions/{client_id}")
def delete_subscription(
    client_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Remove a client's subscription (revert to no plan)."""
    subscription = db.query(Subscription).filter(Subscription.client_id == client_id).first()
    if not subscription:
        raise HTTPException(status_code=404, detail="No subscription found for this client")

    db.delete(subscription)
    db.commit()
    return {"detail": "Subscription removed"}


@router.get("/api/founder/subscriptions/{client_id}/usage", response_model=List[UsageRecordResponse])
def get_client_usage(
    client_id: UUID,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """View usage records for a specific client."""
    records = (
        db.query(UsageRecord)
        .filter(UsageRecord.client_id == client_id)
        .order_by(UsageRecord.created_at.desc())
        .limit(limit)
        .all()
    )

    user_ids = {r.user_id for r in records}
    users = {u.id: u for u in db.query(User).filter(User.id.in_(user_ids)).all()} if user_ids else {}

    return [
        UsageRecordResponse(
            id=r.id,
            client_id=r.client_id,
            user_id=r.user_id,
            user_email=users.get(r.user_id, None) and users[r.user_id].email,
            action_type=r.action_type,
            prompt_id=r.prompt_id,
            usage_metadata=r.usage_metadata,
            created_at=r.created_at,
        )
        for r in records
    ]


@router.delete("/api/founder/subscriptions/{client_id}/usage")
def reset_client_usage(
    client_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Reset (delete) all usage records for a client -- effectively resets their trial."""
    count = db.query(UsageRecord).filter(UsageRecord.client_id == client_id).delete()
    db.commit()
    return {"detail": f"Deleted {count} usage records"}
