"""
Ad Library imports (copy only) for VOC comparison.
Import ad copy from Meta Ads Library URL and store for comparison.
POST returns 202 and runs the scrape in the background to avoid proxy timeouts.
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session, joinedload
from uuid import UUID
import logging

from app.database import get_db, SessionLocal
from app.models import User, Client, AdLibraryImport, AdLibraryAd
from app.schemas import (
    AdLibraryImportResponse,
    AdLibraryImportDetailResponse,
    AdLibraryImportListResponse,
    AdLibraryImportStartedResponse,
    AdLibraryImportFromUrlRequest,
    AdLibraryAdResponse,
)
from app.auth import get_current_active_founder
from app.services.meta_ads_library_scraper import MetaAdsLibraryScraper, AdCopyItem

router = APIRouter()
logger = logging.getLogger(__name__)


async def _run_import_background(client_id: UUID, source_url: str, max_scrolls: int) -> None:
    """Run scrape and save AdLibraryImport + ads in background. Uses its own DB session."""
    db = SessionLocal()
    try:
        scraper = MetaAdsLibraryScraper(headless=True)
        copy_items: list[AdCopyItem] = await scraper.scrape_ads_library_copy(
            source_url, max_scrolls=max_scrolls
        )
        if not copy_items:
            logger.warning("Background import: no ad copy found for %s", source_url[:80])
            return
        imp = AdLibraryImport(client_id=client_id, source_url=source_url)
        db.add(imp)
        db.flush()
        for item in copy_items:
            ad = AdLibraryAd(
                import_id=imp.id,
                primary_text=item.primary_text,
                headline=item.headline,
                description=item.description,
                library_id=item.library_id,
                started_running_on=item.started_running_on,
            )
            db.add(ad)
        db.commit()
        logger.info(
            "Background import completed: client_id=%s, import_id=%s, ads=%s",
            client_id, imp.id, len(copy_items),
        )
    except Exception as e:
        logger.exception("Background import failed: %s", e)
        db.rollback()
    finally:
        db.close()


@router.get(
    "/api/clients/{client_id}/ad-library-imports",
    response_model=AdLibraryImportListResponse,
)
def list_ad_library_imports(
    client_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """List Ad Library imports for a client (copy-only imports for VOC comparison)."""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    imports = (
        db.query(AdLibraryImport)
        .filter(AdLibraryImport.client_id == client_id)
        .options(joinedload(AdLibraryImport.ads))
        .order_by(AdLibraryImport.imported_at.desc())
        .all()
    )
    items = [
        AdLibraryImportResponse(
            id=imp.id,
            client_id=imp.client_id,
            source_url=imp.source_url,
            imported_at=imp.imported_at,
            ad_count=len(imp.ads),
        )
        for imp in imports
    ]
    return AdLibraryImportListResponse(items=items, total=len(items))


@router.get(
    "/api/clients/{client_id}/ad-library-imports/{import_id}",
    response_model=AdLibraryImportDetailResponse,
)
def get_ad_library_import(
    client_id: UUID,
    import_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Get one Ad Library import with full list of ads."""
    imp = (
        db.query(AdLibraryImport)
        .filter(
            AdLibraryImport.id == import_id,
            AdLibraryImport.client_id == client_id,
        )
        .options(joinedload(AdLibraryImport.ads))
        .first()
    )
    if not imp:
        raise HTTPException(status_code=404, detail="Import not found")
    return AdLibraryImportDetailResponse(
        id=imp.id,
        client_id=imp.client_id,
        source_url=imp.source_url,
        imported_at=imp.imported_at,
        ads=[AdLibraryAdResponse.model_validate(ad) for ad in imp.ads],
    )


@router.post(
    "/api/clients/{client_id}/ad-library-imports",
    response_model=AdLibraryImportStartedResponse,
    status_code=202,
)
async def create_ad_library_import_from_url(
    client_id: UUID,
    body: AdLibraryImportFromUrlRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Start ad copy import in the background. Returns 202 immediately to avoid proxy timeouts."""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    scraper = MetaAdsLibraryScraper(headless=True)
    if not scraper.validate_url(body.source_url):
        raise HTTPException(
            status_code=400,
            detail="Invalid Meta Ads Library URL. Must include view_all_page_id parameter.",
        )
    try:
        from playwright.async_api import async_playwright  # noqa: F401
    except ImportError:
        logger.warning("Playwright not installed; Ad Library import unavailable")
        raise HTTPException(
            status_code=503,
            detail="Ad Library import is not available on this server (Playwright/Chromium not installed).",
        ) from None
    background_tasks.add_task(
        _run_import_background,
        client_id,
        body.source_url,
        body.max_scrolls,
    )
    return AdLibraryImportStartedResponse()


@router.delete("/api/clients/{client_id}/ad-library-imports/{import_id}")
def delete_ad_library_import(
    client_id: UUID,
    import_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Delete an Ad Library import and all its ads (cascade)."""
    imp = db.query(AdLibraryImport).filter(
        AdLibraryImport.id == import_id,
        AdLibraryImport.client_id == client_id,
    ).first()
    if not imp:
        raise HTTPException(status_code=404, detail="Import not found")
    db.delete(imp)
    db.commit()
    return {"success": True}
