"""
Facebook Ads management routes for founder admin.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List
import logging

from app.database import get_db
from app.models import User, FacebookAd, Client
from app.schemas import FacebookAdCreate, FacebookAdUpdate, FacebookAdResponse, FacebookAdListResponse
from app.auth import get_current_active_founder

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/api/clients/{client_id}/facebook-ads",
    response_model=FacebookAdListResponse,
)
def list_facebook_ads(
    client_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """List all Facebook ads for a client."""
    # Verify client exists
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    ads = db.query(FacebookAd).filter(
        FacebookAd.client_id == client_id
    ).order_by(FacebookAd.created_at.desc()).all()
    
    return FacebookAdListResponse(
        items=[FacebookAdResponse.model_validate(ad) for ad in ads],
        total=len(ads)
    )


@router.post(
    "/api/clients/{client_id}/facebook-ads",
    response_model=FacebookAdResponse,
    status_code=201,
)
def create_facebook_ad(
    client_id: UUID,
    ad_data: FacebookAdCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Create a new Facebook ad."""
    # Verify client exists
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Create the ad
    ad = FacebookAd(
        client_id=client_id,
        primary_text=ad_data.primary_text,
        headline=ad_data.headline,
        description=ad_data.description,
        call_to_action=ad_data.call_to_action,
        destination_url=ad_data.destination_url,
        image_hash=ad_data.image_hash,
        voc_evidence=ad_data.voc_evidence or [],
        full_json=ad_data.full_json,
        insight_id=ad_data.insight_id,
        action_id=ad_data.action_id,
        status=ad_data.status or 'draft',
        created_by=current_user.id,
    )
    
    db.add(ad)
    db.commit()
    db.refresh(ad)
    
    logger.info(f"Created Facebook ad {ad.id} for client {client_id}")
    return FacebookAdResponse.model_validate(ad)


@router.get(
    "/api/facebook-ads/{ad_id}",
    response_model=FacebookAdResponse,
)
def get_facebook_ad(
    ad_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Get a single Facebook ad by ID."""
    ad = db.query(FacebookAd).filter(FacebookAd.id == ad_id).first()
    if not ad:
        raise HTTPException(status_code=404, detail="Facebook ad not found")
    
    return FacebookAdResponse.model_validate(ad)


@router.patch(
    "/api/facebook-ads/{ad_id}",
    response_model=FacebookAdResponse,
)
def update_facebook_ad(
    ad_id: UUID,
    ad_data: FacebookAdUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Update a Facebook ad (e.g., change status)."""
    ad = db.query(FacebookAd).filter(FacebookAd.id == ad_id).first()
    if not ad:
        raise HTTPException(status_code=404, detail="Facebook ad not found")
    
    # Update only provided fields
    update_data = ad_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(ad, field, value)
    
    db.commit()
    db.refresh(ad)
    
    logger.info(f"Updated Facebook ad {ad_id}")
    return FacebookAdResponse.model_validate(ad)


@router.delete(
    "/api/facebook-ads/{ad_id}",
    status_code=204,
)
def delete_facebook_ad(
    ad_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Delete a Facebook ad."""
    ad = db.query(FacebookAd).filter(FacebookAd.id == ad_id).first()
    if not ad:
        raise HTTPException(status_code=404, detail="Facebook ad not found")
    
    db.delete(ad)
    db.commit()
    
    logger.info(f"Deleted Facebook ad {ad_id}")
    return None
