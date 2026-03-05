"""
Billing routes for Stripe checkout, portal, and webhooks.
"""
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Plan, Subscription
from app.auth import get_current_user
from app.authorization import verify_client_access
from app.config import get_settings
from app.services.stripe_service import (
    create_checkout_session,
    create_portal_session,
    construct_webhook_event,
    handle_checkout_completed,
    handle_subscription_updated,
    handle_subscription_deleted,
    handle_invoice_payment_failed,
)

router = APIRouter(prefix="/api/billing", tags=["billing"])
logger = logging.getLogger(__name__)


class CheckoutRequest(BaseModel):
    client_id: UUID
    plan_name: str


class CheckoutResponse(BaseModel):
    checkout_url: str


class PortalRequest(BaseModel):
    client_id: UUID


class PortalResponse(BaseModel):
    portal_url: str


class PlanPublicResponse(BaseModel):
    name: str
    display_name: str
    price_monthly_cents: int
    features: dict
    sort_order: int


@router.post("/checkout", response_model=CheckoutResponse)
def create_checkout(
    body: CheckoutRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a Stripe Checkout Session for upgrading a client's plan."""
    verify_client_access(body.client_id, current_user, db)

    settings = get_settings()
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Stripe is not configured")

    if body.plan_name not in ("basic", "pro"):
        raise HTTPException(status_code=400, detail="Invalid plan name. Use 'basic' or 'pro'.")

    existing = db.query(Subscription).filter(Subscription.client_id == body.client_id).first()
    if existing and existing.is_manual_override:
        raise HTTPException(status_code=400, detail="This client has a manual override subscription. Contact support to change plans.")

    base_url = settings.frontend_base_url.rstrip("/")
    success_url = f"{base_url}/pricing.html?checkout=success&plan={body.plan_name}"
    cancel_url = f"{base_url}/pricing.html?checkout=canceled"

    try:
        url = create_checkout_session(
            client_id=body.client_id,
            plan_name=body.plan_name,
            user_email=current_user.email,
            success_url=success_url,
            cancel_url=cancel_url,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Stripe checkout error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create checkout session")

    return CheckoutResponse(checkout_url=url)


@router.post("/portal", response_model=PortalResponse)
def create_portal(
    body: PortalRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a Stripe Customer Portal session for managing billing."""
    verify_client_access(body.client_id, current_user, db)

    subscription = db.query(Subscription).filter(Subscription.client_id == body.client_id).first()
    if not subscription or not subscription.stripe_customer_id:
        raise HTTPException(status_code=404, detail="No Stripe subscription found for this client")

    settings = get_settings()
    base_url = settings.frontend_base_url.rstrip("/")
    return_url = f"{base_url}/index.html#/settings"

    try:
        url = create_portal_session(subscription.stripe_customer_id, return_url)
    except Exception as e:
        logger.error(f"Stripe portal error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create portal session")

    return PortalResponse(portal_url=url)


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """Receive and process Stripe webhook events."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = construct_webhook_event(payload, sig_header)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except Exception as e:
        logger.error(f"Webhook signature verification failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event["type"]
    data = event["data"]["object"]
    logger.info(f"Stripe webhook received: {event_type}")

    if event_type == "checkout.session.completed":
        handle_checkout_completed(data, db)
    elif event_type == "customer.subscription.updated":
        handle_subscription_updated(data, db)
    elif event_type == "customer.subscription.deleted":
        handle_subscription_deleted(data, db)
    elif event_type == "invoice.payment_failed":
        handle_invoice_payment_failed(data, db)
    else:
        logger.debug(f"Unhandled webhook event: {event_type}")

    return {"status": "ok"}


@router.get("/plans", response_model=list[PlanPublicResponse])
def list_plans(db: Session = Depends(get_db)):
    """List available plans with pricing (public endpoint)."""
    plans = db.query(Plan).filter(Plan.is_active == True).order_by(Plan.sort_order).all()
    return [
        PlanPublicResponse(
            name=p.name,
            display_name=p.display_name,
            price_monthly_cents=p.price_monthly_cents,
            features=p.features or {},
            sort_order=p.sort_order,
        )
        for p in plans
    ]
