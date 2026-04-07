"""
Ad Library Extension import API.
Accepts pre-scraped ad data from the Chrome extension.
POST /api/clients/{client_id}/ad-library-imports/from-extension
"""
import asyncio
import logging
import os
import time
import random
import string
from uuid import UUID

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user_flexible
from app.authorization import verify_client_access
from app.database import get_db, SessionLocal
from app.models import User, Client, AdLibraryImport, AdLibraryAd, AdLibraryMedia, AdImage
from app.schemas.ad_library_import import (
    ExtensionImportRequest,
    ExtensionImportResponse,
)

router = APIRouter()
logger = logging.getLogger(__name__)


def _random_suffix(length: int = 7) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


def _ext_from_content_type(content_type: str) -> str:
    if "video" in content_type:
        return "mp4"
    if "png" in content_type:
        return "png"
    if "gif" in content_type:
        return "gif"
    if "webp" in content_type:
        return "webp"
    return "jpg"


async def _download_and_reupload(url: str, client_id: str, blob_token: str) -> str | None:
    """Download a media URL and re-upload to Vercel Blob. Returns the permanent blob URL."""
    try:
        import vercel_blob
    except ImportError:
        logger.warning("vercel_blob not installed, skipping media re-upload")
        return None

    try:
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            content = response.content
            content_type = response.headers.get("content-type", "image/jpeg")

        ext = _ext_from_content_type(content_type)
        filename = f"meta-import-{int(time.time())}-{_random_suffix()}.{ext}"
        blob_path = f"ad-images/{client_id}/{filename}"

        blob = vercel_blob.put(blob_path, content, {
            "access": "public",
            "contentType": content_type,
            "token": blob_token,
        })
        return blob.get("url") if isinstance(blob, dict) else getattr(blob, "url", str(blob))
    except Exception as e:
        logger.warning("Failed to re-upload %s: %s", url[:80], e)
        return None


async def _reupload_media_background(import_id: UUID, user_id: UUID | None = None) -> None:
    """Background task: download FB CDN media, re-upload to Vercel Blob, create AdImage records."""
    from app.services.meta_ads_library_scraper import parse_date_string

    blob_token = os.getenv("BLOB_READ_WRITE_TOKEN")
    if not blob_token:
        logger.warning("No BLOB_READ_WRITE_TOKEN, skipping media re-upload for import %s", import_id)
        return

    db = SessionLocal()
    try:
        import_obj = db.query(AdLibraryImport).filter(AdLibraryImport.id == import_id).first()
        if not import_obj:
            return
        client_id = str(import_obj.client_id)
        client_uuid = import_obj.client_id

        # Collect all URLs that need re-uploading
        ads = db.query(AdLibraryAd).filter(AdLibraryAd.import_id == import_id).all()
        media_items = (
            db.query(AdLibraryMedia)
            .join(AdLibraryAd)
            .filter(AdLibraryAd.import_id == import_id)
            .all()
        )

        # Build a map from media → parent ad for AdImage creation
        ad_by_id = {ad.id: ad for ad in ads}
        media_to_ad = {}
        for media in media_items:
            media_to_ad[media.id] = ad_by_id.get(media.ad_id)

        sem = asyncio.Semaphore(5)

        async def _reupload_field(obj, field: str):
            url = getattr(obj, field, None)
            if not url or "vercel" in url.lower():
                return
            async with sem:
                new_url = await _download_and_reupload(url, client_id, blob_token)
            if new_url:
                setattr(obj, field, new_url)
                db.add(obj)

        tasks = []
        for media in media_items:
            tasks.append(_reupload_field(media, "url"))
            tasks.append(_reupload_field(media, "poster_url"))
        for ad in ads:
            tasks.append(_reupload_field(ad, "media_thumbnail_url"))
            tasks.append(_reupload_field(ad, "page_profile_image_url"))

        await asyncio.gather(*tasks, return_exceptions=True)
        db.commit()

        # Create AdImage records for the Media tab
        ad_images_created = 0
        for media in media_items:
            if not media.url or "vercel" not in media.url.lower():
                continue  # Re-upload failed, skip
            parent_ad = media_to_ad.get(media.id)
            content_type = "video/mp4" if media.media_type == "video" else "image/jpeg"
            started = parse_date_string(parent_ad.started_running_on) if parent_ad else None
            ad_image = AdImage(
                client_id=client_uuid,
                url=media.url,
                filename=media.url.rsplit("/", 1)[-1] if "/" in media.url else "imported",
                file_size=0,
                content_type=content_type,
                uploaded_by=user_id,
                started_running_on=started,
                library_id=parent_ad.library_id if parent_ad else None,
                source_url=import_obj.source_url,
            )
            db.add(ad_image)
            ad_images_created += 1
        db.commit()

        reuploaded = sum(1 for m in media_items if m.url and "vercel" in m.url.lower())
        logger.info(
            "Extension import %s: re-uploaded %d/%d media, created %d AdImage records",
            import_id, reuploaded, len(media_items), ad_images_created,
        )
    except Exception as e:
        logger.exception("Background media re-upload failed for import %s: %s", import_id, e)
    finally:
        db.close()


@router.post("/api/admin/backfill-ad-images")
async def backfill_ad_images(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_flexible),
):
    """One-off: create AdImage records from existing AdLibraryMedia with Vercel URLs."""
    from app.services.meta_ads_library_scraper import parse_date_string
    from sqlalchemy.orm import joinedload

    if not current_user.is_founder:
        raise HTTPException(status_code=403, detail="Founders only")

    media_items = (
        db.query(AdLibraryMedia)
        .join(AdLibraryAd)
        .join(AdLibraryImport)
        .options(joinedload(AdLibraryMedia.ad).joinedload(AdLibraryAd.import_run))
        .filter(AdLibraryMedia.url.ilike("%vercel%"))
        .all()
    )

    existing_urls = set(
        row[0] for row in db.query(AdImage.url).filter(AdImage.url.ilike("%vercel%")).all()
    )

    created = 0
    for media in media_items:
        if media.url in existing_urls:
            continue
        ad = media.ad
        if not ad:
            continue
        imp = getattr(ad, "import_run", None)
        client_id = imp.client_id if imp else None
        if not client_id:
            continue

        content_type = "video/mp4" if media.media_type == "video" else "image/jpeg"
        started = parse_date_string(ad.started_running_on) if ad.started_running_on else None

        ad_image = AdImage(
            client_id=client_id,
            url=media.url,
            filename=media.url.rsplit("/", 1)[-1] if "/" in media.url else "imported",
            file_size=0,
            content_type=content_type,
            started_running_on=started,
            library_id=ad.library_id,
            source_url=imp.source_url if imp else None,
        )
        db.add(ad_image)
        created += 1

    db.commit()
    return {"created": created, "total_media_with_vercel": len(media_items), "already_existed": len(existing_urls)}


@router.post(
    "/api/clients/{client_id}/ad-library-imports/from-extension",
    response_model=ExtensionImportResponse,
    status_code=201,
)
async def import_from_extension(
    client_id: UUID,
    body: ExtensionImportRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_flexible),
):
    """
    Import pre-scraped ads from the Chrome extension.
    Creates AdLibraryImport + AdLibraryAd + AdLibraryMedia records.
    Media URLs are re-uploaded to Vercel Blob in the background.
    """
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    verify_client_access(client_id, current_user, db)

    if not body.ads:
        raise HTTPException(status_code=400, detail="No ads provided")

    # Deduplicate against existing ads for this client
    existing_library_ids = set(
        row[0]
        for row in db.query(AdLibraryAd.library_id)
        .join(AdLibraryImport)
        .filter(
            AdLibraryImport.client_id == client_id,
            AdLibraryAd.library_id.isnot(None),
        )
        .all()
        if row[0]
    )

    # Create import record
    imp = AdLibraryImport(client_id=client_id, source_url=body.source_url)
    db.add(imp)
    db.flush()

    ad_count = 0
    skipped_count = 0
    media_count = 0

    for ad_data in body.ads:
        if ad_data.library_id and ad_data.library_id in existing_library_ids:
            skipped_count += 1
            continue

        ad = AdLibraryAd(
            import_id=imp.id,
            primary_text=ad_data.primary_text,
            headline=ad_data.headline,
            description=ad_data.description,
            library_id=ad_data.library_id,
            started_running_on=ad_data.started_running_on,
            ad_delivery_start_time=ad_data.ad_delivery_start_time,
            ad_delivery_end_time=ad_data.ad_delivery_end_time,
            ad_format=ad_data.ad_format,
            cta=ad_data.cta,
            destination_url=ad_data.destination_url,
            media_thumbnail_url=ad_data.media_thumbnail_url,
            status=ad_data.status,
            platforms=ad_data.platforms,
            ads_using_creative_count=ad_data.ads_using_creative_count,
            page_name=ad_data.page_name,
            page_url=ad_data.page_url,
            page_profile_image_url=ad_data.page_profile_image_url,
        )
        db.add(ad)
        db.flush()

        for m in ad_data.media_items:
            media = AdLibraryMedia(
                ad_id=ad.id,
                media_type=m.media_type,
                url=m.url,
                poster_url=m.poster_url,
                duration_seconds=m.duration_seconds,
                sort_order=m.sort_order,
            )
            db.add(media)
            media_count += 1

        ad_count += 1

    db.commit()

    # Kick off background media re-upload + AdImage creation
    background_tasks.add_task(asyncio.run, _reupload_media_background(imp.id, current_user.id))

    return ExtensionImportResponse(
        import_id=imp.id,
        ad_count=ad_count,
        skipped_count=skipped_count,
        media_count=media_count,
    )
