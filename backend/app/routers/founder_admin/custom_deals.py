"""
Founder admin routes for custom deal billing management.
Completely separate from SaaS subscription management.
"""
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.auth import get_current_active_founder
from app.models import User
from app.models.custom_deal import CustomDeal, CustomDealStripeState, DealStatus
from app.models.deal_page_defaults import DealPageDefaults
from app.schemas.custom_deal import (
    CustomDealCreate,
    CustomDealUpdate,
    CustomDealResponse,
    CustomDealListResponse,
)
from app.services.custom_deal_service import (
    create_deal,
    update_deal,
    regenerate_public_token,
    get_deal_public_url,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/api/founder/custom-deals", response_model=list[CustomDealListResponse])
def list_custom_deals(
    status: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """List all custom deals, optionally filtered by status."""
    query = db.query(CustomDeal).order_by(CustomDeal.created_at.desc())
    if status:
        try:
            status_enum = DealStatus(status)
            query = query.filter(CustomDeal.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    return query.all()


@router.get("/api/founder/custom-deals/{deal_id}", response_model=CustomDealResponse)
def get_custom_deal(
    deal_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Get a single custom deal with phases and Stripe state."""
    deal = (
        db.query(CustomDeal)
        .options(joinedload(CustomDeal.phases), joinedload(CustomDeal.stripe_state))
        .filter(CustomDeal.id == deal_id)
        .first()
    )
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    return deal


@router.post("/api/founder/custom-deals", response_model=CustomDealResponse)
def create_custom_deal(
    body: CustomDealCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Create a new custom deal with billing phases."""
    phases_data = [p.model_dump() for p in body.phases]
    deal = create_deal(
        db=db,
        client_name=body.client_name,
        client_email=body.client_email,
        deal_title=body.deal_title,
        currency=body.currency,
        phases_data=phases_data,
        created_by=current_user.id,
        company_name=body.company_name,
        client_id=body.client_id,
        internal_notes=body.internal_notes,
        cancellation_url=body.cancellation_url,
        cancellation_instructions=body.cancellation_instructions,
        page_headline=body.page_headline,
        page_intro=body.page_intro,
        success_message=body.success_message,
        pause_cancel_text=body.pause_cancel_text,
        no_charge_text=body.no_charge_text,
        start_date=body.start_date,
    )
    # Reload with relationships
    db.refresh(deal)
    deal = (
        db.query(CustomDeal)
        .options(joinedload(CustomDeal.phases), joinedload(CustomDeal.stripe_state))
        .filter(CustomDeal.id == deal.id)
        .first()
    )
    return deal


@router.put("/api/founder/custom-deals/{deal_id}", response_model=CustomDealResponse)
def update_custom_deal(
    deal_id: UUID,
    body: CustomDealUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Update a custom deal. Can only update deals that are not yet billing."""
    deal = (
        db.query(CustomDeal)
        .options(joinedload(CustomDeal.phases), joinedload(CustomDeal.stripe_state))
        .filter(CustomDeal.id == deal_id)
        .first()
    )
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    # Prevent editing deals that are actively billing
    if deal.status in (DealStatus.billing_schedule_active, DealStatus.completed):
        raise HTTPException(
            status_code=400,
            detail="Cannot edit a deal that is actively billing or completed"
        )

    update_data = body.model_dump(exclude_unset=True)
    phases_data = None
    if "phases" in update_data and update_data["phases"] is not None:
        phases_data = [p.model_dump() if hasattr(p, "model_dump") else p for p in body.phases]
        del update_data["phases"]

    deal = update_deal(db, deal, update_data, phases_data)
    deal = (
        db.query(CustomDeal)
        .options(joinedload(CustomDeal.phases), joinedload(CustomDeal.stripe_state))
        .filter(CustomDeal.id == deal.id)
        .first()
    )
    return deal


@router.delete("/api/founder/custom-deals/{deal_id}")
def delete_custom_deal(
    deal_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Delete a custom deal. Only allowed for draft/page_generated status."""
    deal = db.query(CustomDeal).filter(CustomDeal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    if deal.status not in (DealStatus.draft, DealStatus.page_generated):
        raise HTTPException(
            status_code=400,
            detail="Can only delete deals in draft or page_generated status"
        )

    db.delete(deal)
    db.commit()
    logger.info(f"Custom deal deleted: {deal_id}")
    return {"detail": "Deal deleted"}


@router.post("/api/founder/custom-deals/{deal_id}/regenerate-token", response_model=CustomDealResponse)
def regenerate_deal_token(
    deal_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Regenerate the public token for a deal (invalidates old URL)."""
    deal = (
        db.query(CustomDeal)
        .options(joinedload(CustomDeal.phases), joinedload(CustomDeal.stripe_state))
        .filter(CustomDeal.id == deal_id)
        .first()
    )
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    deal = regenerate_public_token(db, deal)
    return deal


@router.get("/api/founder/custom-deals/{deal_id}/public-url")
def get_deal_url(
    deal_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Get the public URL for a deal page."""
    deal = db.query(CustomDeal).filter(CustomDeal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    return {"url": get_deal_public_url(deal)}


@router.get("/api/founder/custom-deals/statuses/list")
def list_deal_statuses(
    current_user: User = Depends(get_current_active_founder),
):
    """List all possible deal statuses."""
    return [{"value": s.value, "label": s.value.replace("_", " ").title()} for s in DealStatus]


# --- Deal Page Defaults ---

@router.get("/api/founder/deal-page-defaults")
def get_deal_page_defaults(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Get the current deal page default copy."""
    row = db.query(DealPageDefaults).first()
    if not row:
        return {"pause_cancel_text": "", "no_charge_text": "", "success_message": ""}
    return {
        "pause_cancel_text": row.pause_cancel_text or "",
        "no_charge_text": row.no_charge_text or "",
        "success_message": row.success_message or "",
    }


class DealPageDefaultsUpdate(BaseModel):
    pause_cancel_text: Optional[str] = None
    no_charge_text: Optional[str] = None
    success_message: Optional[str] = None


@router.put("/api/founder/deal-page-defaults")
def save_deal_page_defaults(
    body: DealPageDefaultsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Save deal page default copy. Creates or updates the single row."""
    row = db.query(DealPageDefaults).first()
    if not row:
        row = DealPageDefaults()
        db.add(row)
    row.pause_cancel_text = body.pause_cancel_text
    row.no_charge_text = body.no_charge_text
    row.success_message = body.success_message
    db.commit()
    logger.info("Deal page defaults updated")
    return {"pause_cancel_text": row.pause_cancel_text or "", "no_charge_text": row.no_charge_text or "", "success_message": row.success_message or ""}
