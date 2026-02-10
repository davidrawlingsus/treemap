"""
VOC vs Ads comparison API.
POST /api/clients/{client_id}/voc-ads-comparison
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from uuid import UUID

from app.database import get_db
from app.models import User, Client, FacebookAd, AdLibraryImport, AdLibraryAd
from app.schemas import VocAdsComparisonRequest
from app.auth import get_current_active_founder
from app.services.voc_summary_service import build_voc_summary_dict
from app.services.voc_ads_comparison_service import run_comparison

router = APIRouter()


@router.post("/api/clients/{client_id}/voc-ads-comparison")
def run_voc_ads_comparison(
    client_id: UUID,
    body: VocAdsComparisonRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """
    Run VOC vs Ads comparison: keyword overlap for resonance and overlooked themes.
    ad_source: in_app (facebook_ads), ad_library (stored import), or both.
    When ad_source is ad_library or both, ad_library_import_id can be omitted to use latest import.
    """
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    ad_source = (body.ad_source or "").strip().lower()
    if ad_source not in ("in_app", "ad_library", "both"):
        raise HTTPException(
            status_code=400,
            detail="ad_source must be in_app, ad_library, or both",
        )

    # Load VOC summary (dimension_refs takes precedence over dimension_ref)
    voc_summary = build_voc_summary_dict(
        db,
        client_uuid=client_id,
        data_source=body.data_source,
        project_name=body.project_name,
        dimension_ref=body.dimension_ref if not body.dimension_refs else None,
        dimension_refs=body.dimension_refs,
    )

    # Load ads
    ads: list[dict] = []

    if ad_source in ("in_app", "both"):
        in_app_ads = (
            db.query(FacebookAd)
            .filter(FacebookAd.client_id == client_id)
            .order_by(FacebookAd.created_at.desc())
            .all()
        )
        for ad in in_app_ads:
            ads.append({
                "id": str(ad.id),
                "primary_text": ad.primary_text or "",
                "headline": ad.headline or "",
                "description": ad.description or "",
            })

    if ad_source in ("ad_library", "both"):
        import_id = body.ad_library_import_id
        if not import_id:
            latest = (
                db.query(AdLibraryImport)
                .filter(AdLibraryImport.client_id == client_id)
                .order_by(AdLibraryImport.imported_at.desc())
                .first()
            )
            if not latest and ad_source == "ad_library":
                raise HTTPException(
                    status_code=400,
                    detail="No Ad Library import found. Import from URL first or pass ad_library_import_id.",
                )
            import_id = latest.id if latest else None
        if import_id:
            library_ads = (
                db.query(AdLibraryAd)
                .filter(AdLibraryAd.import_id == import_id)
                .all()
            )
            for ad in library_ads:
                ads.append({
                    "id": str(ad.id),
                    "primary_text": ad.primary_text or "",
                    "headline": ad.headline or "",
                    "description": ad.description or "",
                    "ad_delivery_start_time": ad.ad_delivery_start_time,
                    "ad_delivery_end_time": ad.ad_delivery_end_time,
                    "ad_format": ad.ad_format,
                    "cta": ad.cta,
                    "destination_url": ad.destination_url,
                    "media_thumbnail_url": ad.media_thumbnail_url,
                })
        elif ad_source == "both" and not ads:
            raise HTTPException(
                status_code=400,
                detail="No ads to compare. Add in-app ads or import from Ad Library.",
            )

    if not ads:
        raise HTTPException(
            status_code=400,
            detail="No ads to compare. Add in-app ads or import from Ad Library.",
        )

    result = run_comparison(voc_summary, ads)
    return result
