"""
Ad Images management routes for founder admin.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List, Optional
import logging
import os
import time
import random
import string

from app.database import get_db
from app.models import User, AdImage, Client
from app.schemas import AdImageCreate, AdImageResponse, AdImageListResponse
from app.auth import get_current_active_founder

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/api/upload-ad-image")
async def upload_ad_image_to_blob(
    file: UploadFile = File(...),
    client_id: Optional[str] = Query(None),
):
    """
    Upload an ad image directly to Vercel Blob storage.
    This endpoint handles the actual file upload to Vercel Blob.
    Returns the blob URL for subsequent metadata storage.
    """
    logger.info(f"[BLOB UPLOAD] Endpoint hit - client_id: {client_id}, file: {file.filename if file else 'None'}")
    
    blob_token = os.getenv("BLOB_READ_WRITE_TOKEN")
    logger.info(f"[BLOB UPLOAD] Token configured: {bool(blob_token)}, token length: {len(blob_token) if blob_token else 0}")
    if not blob_token:
        logger.error("BLOB_READ_WRITE_TOKEN not found in environment variables")
        return JSONResponse(
            status_code=500,
            content={"error": "Blob storage not configured"}
        )
    
    if not file:
        return JSONResponse(
            status_code=400,
            content={"error": "No file provided"}
        )
    
    try:
        # Read file content
        content = await file.read()
        
        # Generate unique filename
        file_extension = file.filename.split('.')[-1] if '.' in file.filename else 'bin'
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=7))
        unique_filename = f"ad-images/{client_id or 'unknown'}/{int(time.time())}-{random_suffix}.{file_extension}"
        
        logger.info(f"Uploading ad image to Vercel Blob: {unique_filename}, size: {len(content)} bytes, type: {file.content_type}")
        
        # Upload to Vercel Blob using the vercel_blob library
        # API: vercel_blob.put(pathname, body, options_dict)
        import vercel_blob
        blob = vercel_blob.put(unique_filename, content, {
            "access": "public",
            "contentType": file.content_type,
            "token": blob_token,
        })
        
        blob_url = blob.get("url") if isinstance(blob, dict) else getattr(blob, 'url', str(blob))
        logger.info(f"Ad image upload successful, URL: {blob_url}")
        
        return {
            "url": blob_url,
            "filename": file.filename,
            "file_size": len(content),
            "content_type": file.content_type
        }
        
    except Exception as e:
        import traceback
        logger.error(f"[BLOB UPLOAD] Error: {e}")
        logger.error(f"[BLOB UPLOAD] Traceback: {traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e) or "Upload failed"}
        )


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
