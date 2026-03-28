"""
Public deal billing routes — deal page API, Stripe Checkout session, and webhook.

This is the public-facing side of the custom deal billing flow.
Completely separate from the SaaS billing router (/api/billing/*).
"""
import calendar
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.custom_deal import CustomDeal, DealStatus
from app.models.client import Client
from app.models.deal_page_defaults import DealPageDefaults
from app.schemas.custom_deal import (
    PublicDealPageResponse,
    PublicDealPhaseResponse,
    DealCheckoutSessionResponse,
)
from app.services.custom_deal_service import (
    create_checkout_session_for_deal,
    construct_deal_webhook_event,
    handle_checkout_session_completed,
    handle_invoice_payment_failed,
)
from app.config import get_settings

router = APIRouter(prefix="/api/deal-billing", tags=["deal-billing"])
logger = logging.getLogger(__name__)


def _get_default_text(db: Session, field: str) -> str | None:
    """Fetch a default text value from the deal_page_defaults table."""
    row = db.query(DealPageDefaults).first()
    if row:
        return getattr(row, field, None)
    return None


def _add_months(dt: datetime, months: int) -> datetime:
    """Add months to a datetime, clamping the day to the last day of the target month."""
    month = dt.month - 1 + months
    year = dt.year + month // 12
    month = month % 12 + 1
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


@router.get("/page/{public_token}", response_model=PublicDealPageResponse)
def get_deal_page(
    public_token: str,
    db: Session = Depends(get_db),
):
    """
    Public endpoint: fetch deal details for the client-facing deal page.
    No authentication required — access is controlled by the unguessable token.
    Only returns non-sensitive information needed for display.
    """
    deal = (
        db.query(CustomDeal)
        .options(joinedload(CustomDeal.phases), joinedload(CustomDeal.client))
        .filter(CustomDeal.public_token == public_token)
        .first()
    )
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    # Don't show cancelled or completed deals
    if deal.status in (DealStatus.cancelled,):
        raise HTTPException(status_code=410, detail="This deal is no longer available")

    phases = sorted(deal.phases, key=lambda p: p.phase_order)

    # Compute billing dates from start_date: phase 0 = start_date, phase 1 = +1 month, etc.
    start = deal.start_date
    month_offset = 0
    phase_responses = []
    for p in phases:
        computed_date = None
        if start:
            computed_date = p.billing_date or _add_months(start, month_offset)
            # Advance offset by phase duration (or 1 month for recurring)
            month_offset += p.duration_months or 1
        phase_responses.append(PublicDealPhaseResponse(
            label=p.label,
            amount_cents=p.amount_cents,
            is_recurring_indefinitely=p.is_recurring_indefinitely,
            billing_date=p.billing_date,
            computed_billing_date=computed_date,
            duration_months=p.duration_months,
        ))

    # Pull logo from linked client if available
    logo_url = None
    if deal.client_id and deal.client:
        logo_url = deal.client.logo_url
    return PublicDealPageResponse(
        deal_title=deal.deal_title,
        company_name=deal.company_name,
        logo_url=logo_url,
        currency=deal.currency,
        status=deal.status.value if isinstance(deal.status, DealStatus) else deal.status,
        page_headline=deal.page_headline,
        page_intro=deal.page_intro,
        cancellation_url=deal.cancellation_url,
        cancellation_instructions=deal.cancellation_instructions,
        success_message=deal.success_message or _get_default_text(db, "success_message"),
        pause_cancel_text=deal.pause_cancel_text or _get_default_text(db, "pause_cancel_text"),
        no_charge_text=deal.no_charge_text or _get_default_text(db, "no_charge_text"),
        founder_brand=deal.founder_brand or "mapthegap",
        phases=phase_responses,
    )


@router.post("/checkout/{public_token}", response_model=DealCheckoutSessionResponse)
def create_deal_checkout(
    public_token: str,
    db: Session = Depends(get_db),
):
    """
    Public endpoint: create a Stripe Checkout Session in setup mode for this deal.
    Returns a client_secret for embedded checkout on the deal page.
    No auth required — secured by unguessable token.
    """
    deal = (
        db.query(CustomDeal)
        .options(joinedload(CustomDeal.stripe_state), joinedload(CustomDeal.phases))
        .filter(CustomDeal.public_token == public_token)
        .first()
    )
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    if deal.status in (DealStatus.cancelled,):
        raise HTTPException(status_code=410, detail="This deal is no longer available")

    # If card already captured or billing active, don't create new session
    if deal.status in (DealStatus.card_captured, DealStatus.billing_schedule_active, DealStatus.completed):
        raise HTTPException(status_code=400, detail="Card has already been set up for this deal")

    settings = get_settings()
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Payment processing is not configured")

    try:
        client_secret = create_checkout_session_for_deal(db, deal)
    except Exception as e:
        logger.error(f"Failed to create checkout session for deal {deal.id}: {e}", exc_info=True)
        error_detail = f"Failed to create checkout session: {str(e)[:200]}"
        raise HTTPException(status_code=500, detail=error_detail)

    return DealCheckoutSessionResponse(client_secret=client_secret)


@router.get("/status/{public_token}")
def get_deal_status(
    public_token: str,
    db: Session = Depends(get_db),
):
    """Public endpoint: check deal status (for redirect page after setup)."""
    deal = db.query(CustomDeal).filter(CustomDeal.public_token == public_token).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    status_value = deal.status.value if isinstance(deal.status, DealStatus) else deal.status
    return {
        "status": status_value,
        "is_setup_complete": status_value in ("card_captured", "billing_schedule_active", "completed"),
    }


@router.get("/publishable-key")
def get_stripe_publishable_key():
    """Public endpoint: return the Stripe publishable key for client-side checkout."""
    settings = get_settings()
    if not settings.stripe_publishable_key:
        raise HTTPException(status_code=503, detail="Stripe is not configured")
    return {"publishable_key": settings.stripe_publishable_key}


@router.post("/webhook")
async def deal_billing_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Stripe webhook endpoint for custom deal billing events.
    Separate from the SaaS billing webhook at /api/billing/webhook.

    Handles:
    - checkout.session.completed: card setup success -> create subscription schedule
    - invoice.payment_failed: mark deal as payment_failed
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = construct_deal_webhook_event(payload, sig_header)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except Exception as e:
        logger.error(f"Deal webhook signature verification failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event["type"]
    data = event["data"]["object"]
    logger.info(f"Deal billing webhook received: {event_type}")

    if event_type == "checkout.session.completed":
        # Only process setup mode sessions for custom deals
        if data.get("mode") == "setup":
            handle_checkout_session_completed(data, db)
    elif event_type == "invoice.payment_failed":
        handle_invoice_payment_failed(data, db)
    else:
        logger.debug(f"Unhandled deal webhook event: {event_type}")

    return {"status": "ok"}
