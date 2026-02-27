"""
Facebook Ads management routes.
Access: any authenticated user with access to the client (membership or founder).
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List
import logging

from app.database import get_db
from app.models import User, FacebookAd, Client
from app.schemas import FacebookAdCreate, FacebookAdUpdate, FacebookAdResponse, FacebookAdListResponse
from app.auth import get_current_user
from app.authorization import verify_client_access
import copy

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/api/clients/{client_id}/facebook-ads",
    response_model=FacebookAdListResponse,
)
def list_facebook_ads(
    client_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all Facebook ads for a client."""
    verify_client_access(client_id, current_user, db)
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
    current_user: User = Depends(get_current_user),
):
    """Create a new Facebook ad."""
    verify_client_access(client_id, current_user, db)
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
    current_user: User = Depends(get_current_user),
):
    """Get a single Facebook ad by ID."""
    ad = db.query(FacebookAd).filter(FacebookAd.id == ad_id).first()
    if not ad:
        raise HTTPException(status_code=404, detail="Facebook ad not found")
    verify_client_access(ad.client_id, current_user, db)
    return FacebookAdResponse.model_validate(ad)


@router.patch(
    "/api/facebook-ads/{ad_id}",
    response_model=FacebookAdResponse,
)
def update_facebook_ad(
    ad_id: UUID,
    ad_data: FacebookAdUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a Facebook ad (e.g., change status or image_url)."""
    ad = db.query(FacebookAd).filter(FacebookAd.id == ad_id).first()
    if not ad:
        raise HTTPException(status_code=404, detail="Facebook ad not found")
    verify_client_access(ad.client_id, current_user, db)
    # Update only provided fields
    update_data = ad_data.model_dump(exclude_unset=True)
    
    # Handle image_url - store it in full_json
    # Use sentinel to distinguish "not provided" from "explicitly set to null (remove)"
    _sentinel = object()
    image_url = update_data.pop('image_url', _sentinel)
    
    if image_url is not _sentinel:
        full_json = copy.deepcopy(ad.full_json) if ad.full_json else {}
        if image_url is None:
            full_json.pop('image_url', None)
        else:
            full_json['image_url'] = image_url
        ad.full_json = full_json
    
    # Handle angle - store it in full_json
    angle = update_data.pop('angle', None)
    if angle is not None:
        full_json = copy.deepcopy(ad.full_json) if ad.full_json else {}
        full_json['angle'] = angle
        # Remove legacy testType key if present
        full_json.pop('testType', None)
        ad.full_json = full_json
    
    # Update other fields
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
    current_user: User = Depends(get_current_user),
):
    """Delete a Facebook ad."""
    ad = db.query(FacebookAd).filter(FacebookAd.id == ad_id).first()
    if not ad:
        raise HTTPException(status_code=404, detail="Facebook ad not found")
    verify_client_access(ad.client_id, current_user, db)
    db.delete(ad)
    db.commit()
    
    logger.info(f"Deleted Facebook ad {ad_id}")
    return None
