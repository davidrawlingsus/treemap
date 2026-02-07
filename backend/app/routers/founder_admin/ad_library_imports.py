"""
Ad Library imports (copy only) for VOC comparison.
Import ad copy from Meta Ads Library URL and store for comparison.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from uuid import UUID
import logging

from app.database import get_db
from app.models import User, Client, AdLibraryImport, AdLibraryAd
from app.schemas import (
    AdLibraryImportResponse,
    AdLibraryImportDetailResponse,
    AdLibraryImportListResponse,
    AdLibraryImportFromUrlRequest,
    AdLibraryAdResponse,
)
from app.auth import get_current_active_founder
from app.services.meta_ads_library_scraper import MetaAdsLibraryScraper, AdCopyItem

router = APIRouter()
logger = logging.getLogger(__name__)


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
    response_model=AdLibraryImportDetailResponse,
    status_code=201,
)
async def create_ad_library_import_from_url(
    client_id: UUID,
    body: AdLibraryImportFromUrlRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Scrape ad copy from a Meta Ads Library URL and store for VOC comparison."""
    # #region agent log
    _log_path = "/Users/davidrawlings/Code/Marketable Project Folder/vizualizd/.cursor/debug.log"
    try:
        import json
        _e = {"hypothesisId": "H1-H4", "location": "ad_library_imports.py:create_ad_library_import_from_url", "message": "POST ad-library-imports entry", "data": {"client_id": str(client_id), "source_url": body.source_url[:200] if body.source_url else None, "source_url_len": len(body.source_url) if body.source_url else 0, "max_scrolls": body.max_scrolls}, "timestamp": __import__("time").time() * 1000}
        open(_log_path, "a").write(json.dumps(_e) + "\n")
    except Exception:
        pass
    # #endregion
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    scraper = MetaAdsLibraryScraper(headless=True)
    # #region agent log
    _valid = scraper.validate_url(body.source_url)
    try:
        import json as _json
        _parsed = __import__("urllib.parse").urlparse(body.source_url)
        _q = __import__("urllib.parse").parse_qs(_parsed.query)
        _e2 = {"hypothesisId": "H1,H3,H4", "location": "ad_library_imports.py:validate_url_result", "message": "validate_url result", "data": {"validate_url": _valid, "netloc": _parsed.netloc, "path": (_parsed.path or "")[:80], "has_view_all_page_id": "view_all_page_id" in _q}, "timestamp": __import__("time").time() * 1000}
        open(_log_path, "a").write(_json.dumps(_e2) + "\n")
    except Exception:
        pass
    # #endregion
    if not _valid:
        raise HTTPException(
            status_code=400,
            detail="Invalid Meta Ads Library URL. Must include view_all_page_id parameter.",
        )
    # Fail fast with 503 (so our app returns the response and CORS headers) if Playwright
    # isn't available. Avoids proxy timeout 502 with no CORS when scrape runs in constrained env.
    try:
        from playwright.async_api import async_playwright  # noqa: F401
    except ImportError:
        logger.warning("Playwright not installed; Ad Library import unavailable")
        raise HTTPException(
            status_code=503,
            detail="Ad Library import is not available on this server (Playwright/Chromium not installed).",
        ) from None
    try:
        copy_items: list[AdCopyItem] = await scraper.scrape_ads_library_copy(
            body.source_url, max_scrolls=body.max_scrolls
        )
    except Exception as e:
        logger.exception("Ad Library copy scrape failed")
        raise HTTPException(status_code=502, detail=f"Scrape failed: {e}") from e
    if not copy_items:
        raise HTTPException(
            status_code=422,
            detail="No ad copy found on this page. Try increasing max_scrolls or check the URL.",
        )
    imp = AdLibraryImport(client_id=client_id, source_url=body.source_url)
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
    db.refresh(imp)
    imp = (
        db.query(AdLibraryImport)
        .filter(AdLibraryImport.id == imp.id)
        .options(joinedload(AdLibraryImport.ads))
        .first()
    )
    return AdLibraryImportDetailResponse(
        id=imp.id,
        client_id=imp.client_id,
        source_url=imp.source_url,
        imported_at=imp.imported_at,
        ads=[AdLibraryAdResponse.model_validate(ad) for ad in imp.ads],
    )


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
