"""
Ad Images management routes.
Access: any authenticated user with access to the client (membership or founder).
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_, not_
from uuid import UUID
from typing import List, Optional
from datetime import datetime, timezone
import logging
import os
import time
import random
import string
import asyncio
import traceback

from app.database import get_db, SessionLocal
from app.models import User, AdImage, Client, ImportJob
from app.schemas import (
    AdImageCreate, AdImageResponse, AdImageListResponse,
    ImportJobCreate, ImportJobResponse, ImportJobListResponse, ImportJobStatusResponse
)
from app.auth import get_current_user
from app.authorization import verify_client_access

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== Ad Image Upload Endpoints ====================

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
    file_size: str = Form(...),
    content_type: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a new ad image (metadata only - file already uploaded to Vercel Blob)."""
    verify_client_access(client_id, current_user, db)
    try:
        file_size_int = int(file_size)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail=f"Invalid file_size: {file_size}")
    
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
    sort_by: Optional[str] = Query(
        "uploaded_at",
        description="Sort by: uploaded_at (import time), started_running_on (ad start), meta_created_time (Meta library date)",
    ),
    order: Optional[str] = Query("desc", description="Order: asc or desc"),
    limit: int = Query(60, ge=1, le=200, description="Number of items per page"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    media_type: str = Query("all", description="Filter: all, image, video"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List ad images for a client with optional pagination and media type filter."""
    verify_client_access(client_id, current_user, db)
    if sort_by == "started_running_on":
        col = AdImage.started_running_on
        nullable = True
    elif sort_by == "meta_created_time":
        col = AdImage.meta_created_time
        nullable = True
    else:
        sort_by = "uploaded_at"
        col = AdImage.uploaded_at
        nullable = False
    if order == "asc":
        order_clause = col.asc().nullsfirst() if nullable else col.asc()
    else:
        order_clause = col.desc().nullslast() if nullable else col.desc()

    base_query = (
        db.query(AdImage)
        .filter(AdImage.client_id == client_id)
    )
    if media_type == "video":
        base_query = base_query.filter(AdImage.content_type.like("video%"))
    elif media_type == "image":
        base_query = base_query.filter(
            or_(AdImage.content_type.is_(None), not_(AdImage.content_type.like("video%")))
        )

    total = base_query.count()
    images = (
        base_query
        .order_by(order_clause)
        .offset(offset)
        .limit(limit)
        .all()
    )
    return AdImageListResponse(
        items=[AdImageResponse.model_validate(img) for img in images],
        total=total,
    )


@router.delete(
    "/api/ad-images/{image_id}",
    status_code=204,
)
def delete_ad_image(
    image_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an ad image."""
    image = db.query(AdImage).filter(AdImage.id == image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="Ad image not found")
    verify_client_access(image.client_id, current_user, db)
    db.delete(image)
    db.commit()
    
    logger.info(f"Deleted ad image {image_id}")
    return None


# ==================== Meta Ads Library Import Jobs ====================

async def run_import_job(job_id: str, source_url: str, client_id: str, user_id: str, max_scrolls: int = 5):
    """
    Background task to run the Meta Ads Library import.
    This runs in a separate thread/task so the API can return immediately.
    """
    from app.services.meta_ads_library_scraper import (
        MetaAdsLibraryScraper,
        download_and_upload_media,
    )
    
    # Create a new database session for this background task
    db = SessionLocal()
    
    try:
        # Update job status to running
        job = db.query(ImportJob).filter(ImportJob.id == job_id).first()
        if not job:
            logger.error(f"Import job {job_id} not found")
            return
        
        job.status = 'running'
        job.started_at = datetime.now(timezone.utc)
        db.commit()
        
        # Get blob token
        blob_token = os.getenv("BLOB_READ_WRITE_TOKEN")
        if not blob_token:
            job.status = 'failed'
            job.error_message = "Blob storage not configured"
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
            return
        
        # Initialize scraper and run
        scraper = MetaAdsLibraryScraper(headless=True)
        
        logger.info(f"Import job {job_id}: Starting scrape of {source_url}")
        media_items = await scraper.scrape_ads_library(source_url, max_scrolls=max_scrolls)
        
        # Update total found
        job.total_found = len(media_items)
        db.commit()
        
        if not media_items:
            job.status = 'complete'
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
            logger.info(f"Import job {job_id}: No media found")
            return
        
        # Import each media item
        imported_count = 0
        errors = []
        first_failure_logged = False

        for i, item in enumerate(media_items):
            try:
                logger.info(f"Import job {job_id}: Processing {i + 1}/{len(media_items)}")
                
                # Download and upload
                upload_result = await download_and_upload_media(
                    media_item=item,
                    client_id=client_id,
                    blob_token=blob_token,
                )
                
                # Save to database
                image = AdImage(
                    client_id=client_id,
                    url=upload_result["url"],
                    filename=upload_result["filename"],
                    file_size=upload_result["file_size"],
                    content_type=upload_result["content_type"],
                    uploaded_by=user_id,
                    import_job_id=job_id,
                    started_running_on=upload_result.get("started_running_on"),
                    library_id=upload_result.get("library_id"),
                    source_url=source_url,
                )
                
                db.add(image)
                db.commit()
                
                imported_count += 1
                
                # Update progress periodically
                if imported_count % 5 == 0:
                    job.total_imported = imported_count
                    db.commit()
                
            except Exception as e:
                errors.append(str(e))
                logger.warning(f"Import job {job_id}: Failed to import item {i + 1}: {e}")
                if not first_failure_logged:
                    first_failure_logged = True
                    logger.error(
                        "Import job %s: first failure traceback:\n%s",
                        job_id,
                        traceback.format_exc(),
                    )
        
        # Final update
        job.total_imported = imported_count
        job.status = 'complete'
        job.completed_at = datetime.now(timezone.utc)
        if errors:
            job.error_message = f"{len(errors)} errors: " + "; ".join(errors[:5])
            if len(errors) > 5:
                job.error_message += f" (and {len(errors) - 5} more)"
        db.commit()
        
        logger.info(
            "Import job %s: Complete. Imported %s/%s items. Errors: %s",
            job_id, imported_count, len(media_items), len(errors),
        )
        
    except Exception as e:
        logger.error("Import job %s failed: %s\n%s", job_id, e, traceback.format_exc())
        try:
            job = db.query(ImportJob).filter(ImportJob.id == job_id).first()
            if job:
                job.status = 'failed'
                job.error_message = str(e)
                job.completed_at = datetime.now(timezone.utc)
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


@router.post("/api/meta-ads-library/import", response_model=ImportJobResponse)
async def start_meta_import(
    background_tasks: BackgroundTasks,
    url: str = Form(...),
    client_id: UUID = Query(...),
    max_scrolls: int = Query(5, description="Maximum scroll operations to load more ads"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Start a Meta Ads Library import job.
    Returns immediately with a job ID - the import runs in the background.
    """
    from app.services.meta_ads_library_scraper import MetaAdsLibraryScraper
    
    verify_client_access(client_id, current_user, db)
    # Validate URL
    scraper = MetaAdsLibraryScraper(headless=True)
    if not scraper.validate_url(url):
        raise HTTPException(
            status_code=400,
            detail="Invalid Meta Ads Library URL. Must include view_all_page_id parameter."
        )
    
    # Check for existing running job for this client
    existing_job = db.query(ImportJob).filter(
        ImportJob.client_id == client_id,
        ImportJob.status.in_(['pending', 'running'])
    ).first()
    
    if existing_job:
        raise HTTPException(
            status_code=409,
            detail=f"An import job is already in progress (job_id: {existing_job.id})"
        )
    
    # Create the job
    job = ImportJob(
        client_id=client_id,
        user_id=current_user.id,
        source_url=url,
        status='pending',
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    
    logger.info(f"Created import job {job.id} for client {client_id}")
    
    # Start the background task
    background_tasks.add_task(
        run_import_job,
        str(job.id),
        url,
        str(client_id),
        str(current_user.id),
        max_scrolls
    )
    
    return ImportJobResponse.model_validate(job)


@router.get("/api/meta-ads-library/jobs", response_model=ImportJobListResponse)
def list_import_jobs(
    client_id: UUID = Query(...),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(10, description="Maximum number of jobs to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List import jobs for a client."""
    verify_client_access(client_id, current_user, db)
    query = db.query(ImportJob).filter(ImportJob.client_id == client_id)
    
    if status:
        query = query.filter(ImportJob.status == status)
    
    jobs = query.order_by(desc(ImportJob.created_at)).limit(limit).all()
    
    return ImportJobListResponse(
        items=[ImportJobResponse.model_validate(job) for job in jobs],
        total=len(jobs)
    )


@router.get("/api/meta-ads-library/jobs/{job_id}", response_model=ImportJobStatusResponse)
def get_import_job_status(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get detailed status of an import job including recently imported images."""
    job = db.query(ImportJob).filter(ImportJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Import job not found")
    verify_client_access(job.client_id, current_user, db)
    # Get recently imported images for this job
    recent_images = db.query(AdImage).filter(
        AdImage.import_job_id == job_id
    ).order_by(desc(AdImage.uploaded_at)).limit(20).all()
    
    return ImportJobStatusResponse(
        job=ImportJobResponse.model_validate(job),
        recent_images=[AdImageResponse.model_validate(img) for img in recent_images]
    )


@router.get("/api/meta-ads-library/jobs/{job_id}/images", response_model=AdImageListResponse)
def get_import_job_images(
    job_id: UUID,
    since: Optional[datetime] = Query(None, description="Get images imported after this timestamp"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get images imported by a specific job, optionally filtered by timestamp."""
    job = db.query(ImportJob).filter(ImportJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Import job not found")
    verify_client_access(job.client_id, current_user, db)
    query = db.query(AdImage).filter(AdImage.import_job_id == job_id)
    
    if since:
        query = query.filter(AdImage.uploaded_at > since)
    
    images = query.order_by(AdImage.uploaded_at.asc()).all()
    
    return AdImageListResponse(
        items=[AdImageResponse.model_validate(img) for img in images],
        total=len(images)
    )


# ==================== Legacy Synchronous Scrape Endpoint ====================
# Kept for backward compatibility - consider deprecating

@router.post("/api/meta-ads-library/scrape")
async def scrape_meta_ads_library(
    url: str = Form(...),
    client_id: UUID = Query(...),
    max_scrolls: int = Query(5, description="Maximum scroll operations to load more ads"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    [DEPRECATED] Synchronous scrape endpoint - use /api/meta-ads-library/import instead.
    This blocks until the entire import is complete.
    """
    from app.services.meta_ads_library_scraper import (
        MetaAdsLibraryScraper,
        download_and_upload_media,
    )
    
    verify_client_access(client_id, current_user, db)
    
    blob_token = os.getenv("BLOB_READ_WRITE_TOKEN")
    if not blob_token:
        raise HTTPException(status_code=500, detail="Blob storage not configured")
    
    scraper = MetaAdsLibraryScraper(headless=True)
    
    if not scraper.validate_url(url):
        raise HTTPException(
            status_code=400,
            detail="Invalid Meta Ads Library URL. Must include view_all_page_id parameter."
        )
    
    try:
        logger.info(f"Starting Meta Ads Library scrape for client {client_id}: {url}")
        media_items = await scraper.scrape_ads_library(url, max_scrolls=max_scrolls)
        
        if not media_items:
            return {"imported": 0, "media": [], "message": "No media found on this page"}
        
        imported_media = []
        errors = []
        
        for i, item in enumerate(media_items):
            try:
                logger.info(f"Importing media {i + 1}/{len(media_items)}")
                
                upload_result = await download_and_upload_media(
                    media_item=item,
                    client_id=str(client_id),
                    blob_token=blob_token,
                )
                
                image = AdImage(
                    client_id=client_id,
                    url=upload_result["url"],
                    filename=upload_result["filename"],
                    file_size=upload_result["file_size"],
                    content_type=upload_result["content_type"],
                    uploaded_by=current_user.id,
                    started_running_on=upload_result.get("started_running_on"),
                    library_id=upload_result.get("library_id"),
                    source_url=url,
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
                    "started_running_on": image.started_running_on.isoformat() if image.started_running_on else None,
                    "library_id": image.library_id,
                })
                
            except Exception as e:
                logger.warning(f"Failed to import media: {e}")
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
        raise HTTPException(status_code=500, detail=f"Failed to scrape Meta Ads Library: {str(e)}")
