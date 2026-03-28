"""
Custom deal billing service — Stripe integration for founder-negotiated deals.

Completely separate from the SaaS stripe_service.py.
Uses Stripe Checkout (setup mode) + Subscription Schedules for phased billing.

STRIPE APPROACH FOR PRODUCTS/PRICES:
We create products and prices dynamically per deal phase. Each custom deal has
bespoke amounts, so reusable price templates don't make sense. Products are named
descriptively (e.g. "Custom Deal: Acme Corp - Phase 1") for easy identification
in the Stripe dashboard. Prices use the deal's currency and phase amount.
"""
import logging
import secrets
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

import stripe
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.custom_deal import (
    CustomDeal,
    CustomDealPhase,
    CustomDealStripeState,
    DealStatus,
)

logger = logging.getLogger(__name__)


def _configure_stripe() -> None:
    settings = get_settings()
    if not settings.stripe_secret_key:
        raise RuntimeError("STRIPE_SECRET_KEY is not configured")
    stripe.api_key = settings.stripe_secret_key


def generate_public_token() -> str:
    """Generate a cryptographically secure unguessable token for deal URLs."""
    return secrets.token_urlsafe(32)


def get_deal_public_url(deal: CustomDeal) -> str:
    """Build the full public URL for a deal page."""
    settings = get_settings()
    base = (settings.deal_page_base_url or settings.frontend_base_url).rstrip("/")
    return f"{base}/deal.html?token={deal.public_token}"


def create_deal(
    db: Session,
    client_name: str,
    client_email: str,
    deal_title: str,
    currency: str,
    phases_data: list[dict],
    created_by: Optional[UUID] = None,
    company_name: Optional[str] = None,
    client_id: Optional[UUID] = None,
    internal_notes: Optional[str] = None,
    cancellation_url: Optional[str] = None,
    cancellation_instructions: Optional[str] = None,
    page_headline: Optional[str] = None,
    page_intro: Optional[str] = None,
    success_message: Optional[str] = None,
    pause_cancel_text: Optional[str] = None,
    no_charge_text: Optional[str] = None,
    start_date: Optional[datetime] = None,
) -> CustomDeal:
    """Create a new custom deal with phases and stripe state placeholder."""
    deal = CustomDeal(
        client_name=client_name,
        client_email=client_email,
        company_name=company_name,
        client_id=client_id,
        deal_title=deal_title,
        internal_notes=internal_notes,
        currency=currency.lower(),
        status=DealStatus.draft,
        public_token=generate_public_token(),
        cancellation_url=cancellation_url,
        cancellation_instructions=cancellation_instructions,
        page_headline=page_headline,
        page_intro=page_intro,
        success_message=success_message,
        pause_cancel_text=pause_cancel_text,
        no_charge_text=no_charge_text,
        start_date=start_date,
        created_by=created_by,
    )
    db.add(deal)
    db.flush()  # Get deal.id for phases

    for phase_data in phases_data:
        phase = CustomDealPhase(
            deal_id=deal.id,
            phase_order=phase_data["phase_order"],
            label=phase_data.get("label"),
            amount_cents=phase_data["amount_cents"],
            duration_months=phase_data.get("duration_months"),
            is_recurring_indefinitely=phase_data.get("is_recurring_indefinitely", False),
            billing_date=phase_data.get("billing_date"),
        )
        db.add(phase)

    # Create stripe state record
    stripe_state = CustomDealStripeState(deal_id=deal.id)
    db.add(stripe_state)

    deal.status = DealStatus.page_generated
    db.commit()
    db.refresh(deal)
    logger.info(f"Custom deal created: id={deal.id}, title='{deal.deal_title}'")
    return deal


def update_deal(
    db: Session,
    deal: CustomDeal,
    update_data: dict,
    phases_data: Optional[list[dict]] = None,
) -> CustomDeal:
    """Update a custom deal. Phases are replaced entirely if provided."""
    for key, value in update_data.items():
        if key == "phases":
            continue
        if hasattr(deal, key):
            setattr(deal, key, value)

    if phases_data is not None:
        # Delete existing phases and recreate
        for phase in deal.phases:
            db.delete(phase)
        db.flush()

        for phase_data in phases_data:
            phase = CustomDealPhase(
                deal_id=deal.id,
                phase_order=phase_data["phase_order"],
                label=phase_data.get("label"),
                amount_cents=phase_data["amount_cents"],
                duration_months=phase_data.get("duration_months"),
                is_recurring_indefinitely=phase_data.get("is_recurring_indefinitely", False),
                billing_date=phase_data.get("billing_date"),
            )
            db.add(phase)

    db.commit()
    db.refresh(deal)
    logger.info(f"Custom deal updated: id={deal.id}")
    return deal


def regenerate_public_token(db: Session, deal: CustomDeal) -> CustomDeal:
    """Regenerate the public token (invalidates old URL)."""
    deal.public_token = generate_public_token()
    db.commit()
    db.refresh(deal)
    logger.info(f"Deal {deal.id} public token regenerated")
    return deal


def create_checkout_session_for_deal(db: Session, deal: CustomDeal) -> str:
    """
    Create a Stripe Checkout Session in setup mode for a custom deal.
    Returns the client_secret for embedded checkout.

    This does NOT create a subscription. It only saves the card.
    The subscription schedule is created later via webhook after successful setup.
    """
    _configure_stripe()
    settings = get_settings()

    # Create or retrieve Stripe customer
    stripe_state = deal.stripe_state
    if stripe_state and stripe_state.stripe_customer_id:
        customer_id = stripe_state.stripe_customer_id
    else:
        customer = stripe.Customer.create(
            email=deal.client_email,
            name=deal.client_name,
            metadata={
                "custom_deal_id": str(deal.id),
                "company_name": deal.company_name or "",
                "source": "custom_deal_billing",
            },
        )
        customer_id = customer.id
        if not stripe_state:
            stripe_state = CustomDealStripeState(deal_id=deal.id)
            db.add(stripe_state)
        stripe_state.stripe_customer_id = customer_id
        db.commit()

    base_url = (settings.deal_page_base_url or settings.frontend_base_url).rstrip("/")

    # Embedded checkout in setup mode — card is saved, nothing charged
    session = stripe.checkout.Session.create(
        mode="setup",
        customer=customer_id,
        currency=deal.currency,
        ui_mode="embedded_page",
        return_url=f"{base_url}/deal.html?token={deal.public_token}&setup=complete",
        metadata={
            "custom_deal_id": str(deal.id),
            "source": "custom_deal_billing",
        },
    )

    stripe_state.stripe_checkout_session_id = session.id
    deal.status = DealStatus.awaiting_card_setup
    db.commit()

    logger.info(f"Checkout session created for deal {deal.id}: session={session.id}")
    return session.client_secret


def handle_checkout_session_completed(session_data: dict, db: Session) -> None:
    """
    Handle checkout.session.completed webhook for custom deal setup.
    This is the critical path: attach payment method, set default, create schedule.

    Idempotency: checks if schedule already created before proceeding.
    """
    # Only process our custom deal sessions
    metadata = session_data.get("metadata", {})
    if metadata.get("source") != "custom_deal_billing":
        return

    deal_id_str = metadata.get("custom_deal_id")
    if not deal_id_str:
        logger.warning("Custom deal checkout session missing deal_id in metadata")
        return

    deal_id = UUID(deal_id_str)
    deal = db.query(CustomDeal).filter(CustomDeal.id == deal_id).first()
    if not deal:
        logger.error(f"Custom deal not found: {deal_id}")
        return

    stripe_state = deal.stripe_state
    if not stripe_state:
        logger.error(f"No stripe state for deal {deal_id}")
        return

    event_id = session_data.get("id", "")

    # Idempotency: skip if schedule already created
    if stripe_state.stripe_subscription_schedule_id:
        logger.info(f"Deal {deal_id}: schedule already exists, skipping duplicate webhook")
        return

    _configure_stripe()

    # Get the setup intent from the session
    setup_intent_id = session_data.get("setup_intent")
    if not setup_intent_id:
        logger.error(f"Deal {deal_id}: no setup_intent in checkout session")
        stripe_state.latest_error = "No setup_intent in checkout session"
        db.commit()
        return

    try:
        setup_intent = stripe.SetupIntent.retrieve(setup_intent_id)
        payment_method_id = setup_intent.payment_method

        if not payment_method_id:
            logger.error(f"Deal {deal_id}: no payment_method on setup intent")
            stripe_state.latest_error = "No payment method on setup intent"
            db.commit()
            return

        customer_id = stripe_state.stripe_customer_id or session_data.get("customer")

        # Set as default payment method for invoicing
        stripe.Customer.modify(
            customer_id,
            invoice_settings={"default_payment_method": payment_method_id},
        )

        # Update stripe state
        stripe_state.stripe_setup_intent_id = setup_intent_id
        stripe_state.stripe_payment_method_id = payment_method_id
        stripe_state.stripe_customer_id = customer_id
        stripe_state.setup_completed_at = datetime.now(timezone.utc)
        stripe_state.last_webhook_event_id = event_id
        deal.status = DealStatus.card_captured
        db.commit()

        logger.info(f"Deal {deal_id}: card captured, payment_method={payment_method_id}")

        # Now create the subscription schedule
        _create_subscription_schedule(db, deal)

    except stripe.StripeError as e:
        logger.error(f"Deal {deal_id}: Stripe error during webhook processing: {e}")
        stripe_state.latest_error = str(e)[:500]
        deal.status = DealStatus.payment_failed
        db.commit()
    except Exception as e:
        logger.error(f"Deal {deal_id}: unexpected error during webhook processing: {e}", exc_info=True)
        stripe_state.latest_error = str(e)[:500]
        db.commit()


def _create_subscription_schedule(db: Session, deal: CustomDeal) -> None:
    """
    Create a Stripe Subscription Schedule with phased billing for this deal.

    Each phase gets a dynamically-created product and price. Phases map to
    Stripe subscription schedule phases with specific iteration counts.

    The final phase (if recurring indefinitely) uses no end_date, letting
    Stripe continue billing until cancelled.
    """
    _configure_stripe()
    stripe_state = deal.stripe_state

    # Idempotency guard
    if stripe_state.stripe_subscription_schedule_id:
        logger.info(f"Deal {deal.id}: subscription schedule already exists")
        return

    customer_id = stripe_state.stripe_customer_id
    phases = sorted(deal.phases, key=lambda p: p.phase_order)

    if not phases:
        logger.error(f"Deal {deal.id}: no phases defined")
        stripe_state.latest_error = "No billing phases defined"
        db.commit()
        return

    # Build Stripe schedule phases
    stripe_phases = []
    for phase in phases:
        # Create a product for this phase
        product = stripe.Product.create(
            name=f"Custom Deal: {deal.company_name or deal.client_name} - {phase.label or f'Phase {phase.phase_order + 1}'}",
            metadata={
                "custom_deal_id": str(deal.id),
                "phase_order": str(phase.phase_order),
                "source": "custom_deal_billing",
            },
        )

        # Create a price (recurring monthly) for this phase
        price = stripe.Price.create(
            product=product.id,
            unit_amount=phase.amount_cents,
            currency=deal.currency,
            recurring={"interval": "month"},
        )

        phase_config = {
            "items": [{"price": price.id, "quantity": 1}],
            "proration_behavior": "none",
        }

        if phase.is_recurring_indefinitely:
            # No iterations = continues indefinitely
            pass
        else:
            # Fixed-duration phase: iterations = duration_months
            phase_config["iterations"] = phase.duration_months or 1

        stripe_phases.append(phase_config)

    try:
        # Determine start date: use deal start_date or start now
        if deal.start_date and deal.start_date > datetime.now(timezone.utc):
            start_date = int(deal.start_date.timestamp())
        else:
            start_date = "now"

        schedule = stripe.SubscriptionSchedule.create(
            customer=customer_id,
            start_date=start_date,
            end_behavior="cancel" if not any(p.is_recurring_indefinitely for p in phases) else "release",
            phases=stripe_phases,
            metadata={
                "custom_deal_id": str(deal.id),
                "source": "custom_deal_billing",
            },
        )

        stripe_state.stripe_subscription_schedule_id = schedule.id
        stripe_state.schedule_created_at = datetime.now(timezone.utc)
        stripe_state.latest_error = None
        deal.status = DealStatus.billing_schedule_active
        db.commit()

        logger.info(f"Deal {deal.id}: subscription schedule created: {schedule.id}")

    except stripe.StripeError as e:
        logger.error(f"Deal {deal.id}: failed to create subscription schedule: {e}")
        stripe_state.latest_error = f"Schedule creation failed: {str(e)[:400]}"
        deal.status = DealStatus.payment_failed
        db.commit()
        raise


def handle_invoice_payment_failed(invoice_data: dict, db: Session) -> None:
    """Handle invoice.payment_failed for custom deal subscriptions."""
    subscription_id = invoice_data.get("subscription")
    if not subscription_id:
        return

    # Check if this belongs to a custom deal by looking at subscription schedule
    # Find deals where the schedule's subscription matches
    stripe_state = db.query(CustomDealStripeState).filter(
        CustomDealStripeState.stripe_subscription_schedule_id.isnot(None)
    ).all()

    for state in stripe_state:
        try:
            _configure_stripe()
            schedule = stripe.SubscriptionSchedule.retrieve(state.stripe_subscription_schedule_id)
            if schedule.subscription == subscription_id:
                deal = state.deal
                deal.status = DealStatus.payment_failed
                state.latest_error = f"Payment failed for invoice {invoice_data.get('id', 'unknown')}"
                db.commit()
                logger.warning(f"Deal {deal.id}: payment failed")
                return
        except Exception:
            continue


def construct_deal_webhook_event(payload: bytes, sig_header: str) -> stripe.Event:
    """Verify and construct a Stripe webhook event for custom deal billing."""
    settings = get_settings()
    # Use deal-specific webhook secret if set, otherwise fall back to main secret
    webhook_secret = settings.stripe_deal_webhook_secret or settings.stripe_webhook_secret
    if not webhook_secret:
        raise RuntimeError("No webhook secret configured for deal billing")
    return stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
