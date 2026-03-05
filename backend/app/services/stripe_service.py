"""
Stripe integration service for checkout, portal, and webhook handling.
"""
import logging
from uuid import UUID

import stripe
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Plan, Subscription

logger = logging.getLogger(__name__)


def _configure_stripe():
    settings = get_settings()
    if not settings.stripe_secret_key:
        raise RuntimeError("STRIPE_SECRET_KEY is not configured")
    stripe.api_key = settings.stripe_secret_key


def get_price_id_for_plan(plan_name: str) -> str:
    settings = get_settings()
    mapping = {
        "basic": settings.stripe_basic_price_id,
        "pro": settings.stripe_pro_price_id,
    }
    price_id = mapping.get(plan_name)
    if not price_id:
        raise ValueError(f"No Stripe price ID configured for plan '{plan_name}'")
    return price_id


def create_checkout_session(
    client_id: UUID,
    plan_name: str,
    user_email: str,
    success_url: str,
    cancel_url: str,
) -> str:
    """Create a Stripe Checkout Session and return the URL."""
    _configure_stripe()
    price_id = get_price_id_for_plan(plan_name)

    session = stripe.checkout.Session.create(
        mode="subscription",
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        customer_email=user_email,
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "client_id": str(client_id),
            "plan_name": plan_name,
        },
        subscription_data={
            "metadata": {
                "client_id": str(client_id),
                "plan_name": plan_name,
            },
        },
    )
    logger.info(f"Checkout session created: {session.id} for client {client_id} plan {plan_name}")
    return session.url


def create_portal_session(stripe_customer_id: str, return_url: str) -> str:
    """Create a Stripe Customer Portal session and return the URL."""
    _configure_stripe()
    session = stripe.billing_portal.Session.create(
        customer=stripe_customer_id,
        return_url=return_url,
    )
    return session.url


def construct_webhook_event(payload: bytes, sig_header: str) -> stripe.Event:
    """Verify and construct a Stripe webhook event."""
    settings = get_settings()
    if not settings.stripe_webhook_secret:
        raise RuntimeError("STRIPE_WEBHOOK_SECRET is not configured")
    return stripe.Webhook.construct_event(
        payload, sig_header, settings.stripe_webhook_secret
    )


def handle_checkout_completed(session_data: dict, db: Session):
    """Process checkout.session.completed: create or update subscription."""
    client_id_str = session_data.get("metadata", {}).get("client_id")
    plan_name = session_data.get("metadata", {}).get("plan_name")
    stripe_customer_id = session_data.get("customer")
    stripe_subscription_id = session_data.get("subscription")

    if not client_id_str or not plan_name:
        logger.warning("Checkout session missing client_id or plan_name metadata")
        return

    client_id = UUID(client_id_str)
    plan = db.query(Plan).filter(Plan.name == plan_name).first()
    if not plan:
        logger.error(f"Plan '{plan_name}' not found in database")
        return

    existing = db.query(Subscription).filter(Subscription.client_id == client_id).first()

    if existing:
        if existing.is_manual_override:
            logger.info(f"Skipping checkout for client {client_id}: has manual override")
            return
        existing.plan_id = plan.id
        existing.stripe_customer_id = stripe_customer_id
        existing.stripe_subscription_id = stripe_subscription_id
        existing.status = "active"
        existing.is_manual_override = False
    else:
        sub = Subscription(
            client_id=client_id,
            plan_id=plan.id,
            stripe_customer_id=stripe_customer_id,
            stripe_subscription_id=stripe_subscription_id,
            status="active",
            is_manual_override=False,
        )
        db.add(sub)

    db.commit()
    logger.info(f"Subscription activated for client {client_id} on plan {plan_name}")


def handle_subscription_updated(subscription_data: dict, db: Session):
    """Process customer.subscription.updated: plan changes, renewals."""
    stripe_sub_id = subscription_data.get("id")
    status = subscription_data.get("status")

    existing = db.query(Subscription).filter(
        Subscription.stripe_subscription_id == stripe_sub_id
    ).first()

    if not existing:
        logger.warning(f"No subscription found for stripe_subscription_id={stripe_sub_id}")
        return

    if existing.is_manual_override:
        logger.info(f"Skipping update for manual override subscription {existing.id}")
        return

    if status:
        existing.status = status

    period = subscription_data.get("current_period_start")
    period_end = subscription_data.get("current_period_end")
    if period:
        from datetime import datetime, timezone
        existing.current_period_start = datetime.fromtimestamp(period, tz=timezone.utc)
    if period_end:
        from datetime import datetime, timezone
        existing.current_period_end = datetime.fromtimestamp(period_end, tz=timezone.utc)

    existing.cancel_at_period_end = subscription_data.get("cancel_at_period_end", False)

    items = subscription_data.get("items", {}).get("data", [])
    if items:
        new_price_id = items[0].get("price", {}).get("id")
        if new_price_id:
            settings = get_settings()
            price_to_plan = {
                settings.stripe_basic_price_id: "basic",
                settings.stripe_pro_price_id: "pro",
            }
            new_plan_name = price_to_plan.get(new_price_id)
            if new_plan_name:
                new_plan = db.query(Plan).filter(Plan.name == new_plan_name).first()
                if new_plan and new_plan.id != existing.plan_id:
                    existing.plan_id = new_plan.id
                    logger.info(f"Plan changed to {new_plan_name} for subscription {existing.id}")

    db.commit()
    logger.info(f"Subscription {stripe_sub_id} updated: status={status}")


def handle_subscription_deleted(subscription_data: dict, db: Session):
    """Process customer.subscription.deleted: cancellation."""
    stripe_sub_id = subscription_data.get("id")
    existing = db.query(Subscription).filter(
        Subscription.stripe_subscription_id == stripe_sub_id
    ).first()

    if not existing:
        return

    if existing.is_manual_override:
        logger.info(f"Skipping deletion for manual override subscription {existing.id}")
        return

    existing.status = "canceled"
    db.commit()
    logger.info(f"Subscription {stripe_sub_id} canceled")


def handle_invoice_payment_failed(invoice_data: dict, db: Session):
    """Process invoice.payment_failed: mark as past_due."""
    stripe_sub_id = invoice_data.get("subscription")
    if not stripe_sub_id:
        return

    existing = db.query(Subscription).filter(
        Subscription.stripe_subscription_id == stripe_sub_id
    ).first()

    if not existing or existing.is_manual_override:
        return

    existing.status = "past_due"
    db.commit()
    logger.warning(f"Subscription {stripe_sub_id} marked as past_due due to payment failure")
