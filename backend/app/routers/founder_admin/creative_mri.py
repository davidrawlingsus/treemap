"""
Creative MRI report API.
POST /api/clients/{client_id}/creative-mri/report
Body: { ads?: [...], ad_library_import_id?: uuid }.
If ads omitted, load from Ad Library import (or latest for client).
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from uuid import UUID

from app.database import get_db
from app.models import User, Client, AdLibraryImport, AdLibraryAd
from app.auth import get_current_active_founder
from app.services.creative_mri.pipeline import run_creative_mri_pipeline

router = APIRouter()


def _ad_to_dict(ad: AdLibraryAd) -> dict:
    """Convert AdLibraryAd to flat dict for pipeline."""
    return {
        "id": str(ad.id),
        "headline": ad.headline or "",
        "primary_text": ad.primary_text or "",
        "description": ad.description or "",
        "cta": ad.cta,
        "destination_url": ad.destination_url,
        "ad_format": ad.ad_format,
        "ad_delivery_start_time": ad.ad_delivery_start_time,
        "ad_delivery_end_time": ad.ad_delivery_end_time,
        "media_thumbnail_url": ad.media_thumbnail_url,
    }


@router.post("/api/clients/{client_id}/creative-mri/report")
def run_creative_mri_report(
    client_id: UUID,
    body: dict,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """
    Run Creative MRI report: copy-based effectiveness diagnostics.
    Body: { "ads": [...] } or { "ad_library_import_id": "uuid" }.
    If ads omitted, load ads from ad_library_import_id or latest Ad Library import for client.
    """
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    ads_input = body.get("ads")
    ad_library_import_id = body.get("ad_library_import_id")

    if ads_input is not None:
        ads = [a if isinstance(a, dict) else {"id": str(i), "headline": "", "primary_text": str(a)} for i, a in enumerate(ads_input)]
    else:
        import_id = ad_library_import_id
        if not import_id:
            latest = (
                db.query(AdLibraryImport)
                .filter(AdLibraryImport.client_id == client_id)
                .order_by(AdLibraryImport.imported_at.desc())
                .first()
            )
            if not latest:
                raise HTTPException(
                    status_code=400,
                    detail="No Ad Library import found. Import from URL first or pass ad_library_import_id or ads in body.",
                )
            import_id = latest.id
        library_ads = db.query(AdLibraryAd).filter(AdLibraryAd.import_id == import_id).all()
        ads = [_ad_to_dict(ad) for ad in library_ads]
        if not ads:
            raise HTTPException(status_code=400, detail="No ads in this import.")

    llm_service = getattr(request.app.state, "llm_service", None)
    if not llm_service:
        raise HTTPException(status_code=503, detail="LLM service not configured. Set ANTHROPIC_API_KEY.")

    report = run_creative_mri_pipeline(ads, llm_service)
    return report
