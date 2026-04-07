"""
Ad Library Extension import API.
Accepts pre-scraped ad data from the Chrome extension.
Media URLs should already be permanent Vercel Blob URLs (uploaded by the extension).
POST /api/clients/{client_id}/ad-library-imports/from-extension
"""
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user_flexible
from app.authorization import verify_client_access
from app.database import get_db
from app.models import User, Client, AdLibraryImport, AdLibraryAd, AdLibraryMedia, AdImage
from app.schemas.ad_library_import import (
    ExtensionImportRequest,
    ExtensionImportResponse,
)
from app.services.meta_ads_library_scraper import parse_date_string

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/api/clients/{client_id}/ad-library-imports/from-extension",
    response_model=ExtensionImportResponse,
    status_code=201,
)
def import_from_extension(
    client_id: UUID,
    body: ExtensionImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_flexible),
):
    """
    Import pre-scraped ads from the Chrome extension.
    Creates AdLibraryImport + AdLibraryAd + AdLibraryMedia + AdImage records.
    Media URLs are expected to be permanent (already uploaded to Vercel Blob by the extension).
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

            # Also create AdImage record for the Media tab
            if m.url:
                content_type = "video/mp4" if m.media_type == "video" else "image/jpeg"
                started = parse_date_string(ad_data.started_running_on) if ad_data.started_running_on else None
                ad_image = AdImage(
                    client_id=client_id,
                    url=m.url,
                    filename=m.url.rsplit("/", 1)[-1] if "/" in m.url else "imported",
                    file_size=0,
                    content_type=content_type,
                    uploaded_by=current_user.id,
                    started_running_on=started,
                    library_id=ad_data.library_id,
                    source_url=body.source_url,
                )
                db.add(ad_image)

        ad_count += 1

    db.commit()

    logger.info(
        "Extension import: client=%s, ads=%d, skipped=%d, media=%d",
        client_id, ad_count, skipped_count, media_count,
    )

    return ExtensionImportResponse(
        import_id=imp.id,
        ad_count=ad_count,
        skipped_count=skipped_count,
        media_count=media_count,
    )
