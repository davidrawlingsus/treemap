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
    blob_token = os.getenv("BLOB_READ_WRITE_TOKEN")
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
        logger.error(f"Ad image upload error: {e}")
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


@router.post("/api/meta-ads-library/scrape")
async def scrape_meta_ads_library(
    url: str = Form(...),
    client_id: UUID = Query(...),
    max_scrolls: int = Query(5, description="Maximum scroll operations to load more ads"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """
    Scrape media from a Meta Ads Library page and import to client's media library.
    
    Args:
        url: Meta Ads Library URL with view_all_page_id parameter
        client_id: Client UUID to import media to
        max_scrolls: Maximum number of scroll operations (default 5)
    
    Returns:
        Object with imported count and media list
    """
    from app.services.meta_ads_library_scraper import (
        MetaAdsLibraryScraper,
        download_and_upload_media,
    )
    
    # Verify client exists
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Get blob token
    blob_token = os.getenv("BLOB_READ_WRITE_TOKEN")
    if not blob_token:
        raise HTTPException(
            status_code=500,
            detail="Blob storage not configured"
        )
    
    # Initialize scraper
    scraper = MetaAdsLibraryScraper(headless=True)
    
    # Validate URL
    if not scraper.validate_url(url):
        raise HTTPException(
            status_code=400,
            detail="Invalid Meta Ads Library URL. Must include view_all_page_id parameter."
        )
    
    try:
        # Scrape media from the page
        logger.info(f"Starting Meta Ads Library scrape for client {client_id}: {url}")
        media_items = await scraper.scrape_ads_library(url, max_scrolls=max_scrolls)
        
        if not media_items:
            return {
                "imported": 0,
                "media": [],
                "message": "No media found on this page"
            }
        
        # Download and upload each media item
        imported_media = []
        errors = []
        
        for i, item in enumerate(media_items):
            try:
                logger.info(f"Importing media {i + 1}/{len(media_items)}: {item.url[:50]}...")
                
                # Download and upload to Vercel Blob
                upload_result = await download_and_upload_media(
                    media_url=item.url,
                    client_id=str(client_id),
                    blob_token=blob_token,
                )
                
                # Save metadata to database
                image = AdImage(
                    client_id=client_id,
                    url=upload_result["url"],
                    filename=upload_result["filename"],
                    file_size=upload_result["file_size"],
                    content_type=upload_result["content_type"],
                    uploaded_by=current_user.id,
                )
                
                db.add(image)
                db.commit()
                db.refresh(image)
                
                imported_media.append({
                    "id": str(image.id),
                    "url": image.url,
                    "filename": image.filename,
                    "file_size": image.file_size,
                    "content_type": image.content_type,
                    "uploaded_at": image.uploaded_at.isoformat() if image.uploaded_at else None,
                })
                
            except Exception as e:
                logger.warning(f"Failed to import media {item.url[:50]}: {e}")
                errors.append(str(e))
        
        logger.info(f"Import complete: {len(imported_media)} media imported, {len(errors)} errors")
        
        return {
            "imported": len(imported_media),
            "media": imported_media,
            "errors": errors if errors else None,
        }
        
    except ImportError as e:
        logger.error(f"Playwright not installed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Playwright is not installed. Please run: pip install playwright && playwright install chromium"
        )
    except Exception as e:
        logger.error(f"Meta Ads Library scrape failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to scrape Meta Ads Library: {str(e)}"
        )
