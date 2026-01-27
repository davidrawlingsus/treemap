"""
Ad Images management routes for founder admin.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List
import logging

from app.database import get_db
from app.models import User, AdImage, Client
from app.schemas import AdImageCreate, AdImageResponse, AdImageListResponse
from app.auth import get_current_active_founder

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/api/clients/{client_id}/ad-images",
    response_model=AdImageResponse,
    status_code=201,
)
async def upload_ad_image(
    client_id: UUID,
    url: str = Form(...),
    filename: str = Form(...),
    file_size: str = Form(...),  # Accept as string from FormData, convert to int
    content_type: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Upload a new ad image (metadata only - file already uploaded to Vercel Blob)."""
    # Verify client exists
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Convert file_size from string to int (FormData sends strings)
    try:
        file_size_int = int(file_size)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail=f"Invalid file_size: {file_size}")
    
    # Create the image record
    image = AdImage(
        client_id=client_id,
        url=url,
        filename=filename,
        file_size=file_size_int,
        content_type=content_type,
        uploaded_by=current_user.id,
    )
    
    db.add(image)
    db.commit()
    db.refresh(image)
    
    logger.info(f"Created ad image {image.id} for client {client_id}")
    return AdImageResponse.model_validate(image)


@router.get(
    "/api/clients/{client_id}/ad-images",
    response_model=AdImageListResponse,
)
def list_ad_images(
    client_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """List all ad images for a client."""
    # Verify client exists
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    images = db.query(AdImage).filter(
        AdImage.client_id == client_id
    ).order_by(AdImage.uploaded_at.desc()).all()
    
    return AdImageListResponse(
        items=[AdImageResponse.model_validate(img) for img in images],
        total=len(images)
    )


@router.delete(
    "/api/ad-images/{image_id}",
    status_code=204,
)
def delete_ad_image(
    image_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Delete an ad image."""
    image = db.query(AdImage).filter(AdImage.id == image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="Ad image not found")
    
    db.delete(image)
    db.commit()
    
    logger.info(f"Deleted ad image {image_id}")
    return None
