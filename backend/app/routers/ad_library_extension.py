"""
Ad Library Extension import API.
Accepts pre-scraped ad data from the Chrome extension.
Media URLs should already be permanent Vercel Blob URLs (uploaded by the extension).
POST /api/clients/{client_id}/ad-library-imports/from-extension
POST /api/ad-library-imports/from-extension-leadgen
"""
import asyncio
import logging
import threading
import uuid
from urllib.parse import urlparse
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user_flexible
from app.authorization import verify_client_access
from app.config import get_settings
from app.database import get_db, SessionLocal
from app.models import User, Client, AdLibraryImport, AdLibraryAd, AdLibraryMedia, AdImage
from app.schemas.ad_library_import import (
    ExtensionImportRequest,
    ExtensionImportResponse,
    ExtensionLeadgenImportRequest,
    ExtensionLeadgenImportResponse,
)
from app.services.meta_ads_library_scraper import parse_date_string

router = APIRouter()
logger = logging.getLogger(__name__)


async def _analyze_videos_background(import_id: UUID) -> None:
    """Background task: run Gemini video analysis on imported video media."""
    from app.services.gemini_video_service import GeminiVideoService

    settings = get_settings()
    gemini = GeminiVideoService(api_key=settings.gemini_api_key)
    if not gemini.is_configured():
        logger.info("Gemini not configured, skipping video analysis for import %s", import_id)
        return

    db = SessionLocal()
    try:
        media_items = (
            db.query(AdLibraryMedia)
            .join(AdLibraryAd)
            .filter(
                AdLibraryAd.import_id == import_id,
                AdLibraryMedia.media_type == "video",
                AdLibraryMedia.video_analysis_json.is_(None),
            )
            .all()
        )
        if not media_items:
            return

        # Filter to only Vercel Blob URLs (FB CDN URLs are unreachable from server)
        analyzable = [m for m in media_items if m.url and "vercel" in m.url.lower()]
        skipped = len(media_items) - len(analyzable)
        if skipped:
            logger.warning("Skipping %d videos with non-Blob URLs (FB CDN unreachable from server)", skipped)
        if not analyzable:
            logger.info("No analyzable video URLs for import %s", import_id)
            return

        logger.info("Analyzing %d videos for import %s", len(analyzable), import_id)
        for i, media in enumerate(analyzable):
            try:
                analysis = await gemini.analyze_video_url(media.url)
                if analysis:
                    media.video_analysis_json = analysis
                    db.commit()
                    transcript = (analysis.get("transcript") or "")[:60]
                    logger.info("Video %d/%d analyzed (transcript: %s...)", i + 1, len(analyzable), transcript)
            except Exception as e:
                logger.warning("Video analysis failed for media %s: %s", media.id, e)

        logger.info("Video analysis complete for import %s", import_id)
    except Exception as e:
        logger.exception("Video analysis background task failed: %s", e)
    finally:
        db.close()


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
    Creates AdLibraryImport + AdLibraryAd + AdLibraryMedia + AdImage records.
    Media URLs are expected to be permanent (already uploaded to Vercel Blob by the extension).
    Video ads are analyzed by Gemini in the background for transcripts.
    """
    try:
        result = _do_import(client_id, body, db, current_user)
        # Kick off Gemini video analysis in background
        background_tasks.add_task(_analyze_videos_background, result.import_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Extension import failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


def _do_import(client_id, body, db, current_user):
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
    imp = AdLibraryImport(
        client_id=client_id,
        source_url=body.source_url,
        synthesis_text=getattr(body, "synthesis_text", None),
        signal_text=getattr(body, "signal_text", None),
        ad_copy_score=getattr(body, "ad_copy_score", None),
        signal_score=getattr(body, "signal_score", None),
        opportunity_score=getattr(body, "opportunity_score", None),
    )
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
            analysis_json=ad_data.analysis_json,
            analysis_text=ad_data.analysis_text,
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
                raw_filename = m.url.rsplit("/", 1)[-1].split("?")[0] if "/" in m.url else "imported"
                ad_image = AdImage(
                    client_id=client_id,
                    url=m.url,
                    filename=raw_filename[:250],
                    file_size=0,
                    content_type=content_type,
                    uploaded_by=current_user.id,
                    started_running_on=started,
                    library_id=ad_data.library_id,
                    source_url=body.source_url,
                )
                db.add(ad_image)

        ad_count += 1

    # If client has no logo, use the profile image from the first imported ad
    if not client.logo_url:
        for ad_data in body.ads:
            if ad_data.page_profile_image_url:
                client.logo_url = ad_data.page_profile_image_url
                db.add(client)
                break

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


# ---------------------------------------------------------------------------
# Lead gen flow from extension
# ---------------------------------------------------------------------------

def _extract_company_info(ads):
    """Extract company name, URL, domain, and logo from ad data."""
    company_name = None
    company_url = None
    company_domain = None
    logo_url = None

    for ad in ads:
        if not company_name and ad.page_name:
            company_name = ad.page_name
        if not logo_url and ad.page_profile_image_url:
            logo_url = ad.page_profile_image_url
        if not company_url and ad.destination_url:
            try:
                parsed = urlparse(ad.destination_url)
                host = (parsed.netloc or "").lower().split(":")[0]
                if host and "facebook.com" not in host and "fb.com" not in host:
                    if host.startswith("www."):
                        host = host[4:]
                    company_domain = host
                    company_url = f"https://{host}"
            except Exception:
                pass
        if company_name and company_url and logo_url:
            break

    # Fallback: try page_url for domain
    if not company_domain:
        for ad in ads:
            if ad.page_url:
                company_name = company_name or ad.page_name or "Unknown"
                break

    return company_name or "Unknown", company_url or "", company_domain or "", logo_url


@router.post(
    "/api/ad-library-imports/from-extension-leadgen",
    response_model=ExtensionLeadgenImportResponse,
    status_code=202,
)
def import_from_extension_leadgen(
    body: ExtensionLeadgenImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_flexible),
):
    """
    Import ads from the Chrome extension and trigger the full lead gen pipeline.
    Creates a client, imports ads, then runs Gemini analysis + pipeline in background.
    """
    if not current_user.is_founder:
        raise HTTPException(status_code=403, detail="Founder access required for lead gen")

    if not body.ads:
        raise HTTPException(status_code=400, detail="No ads provided")

    company_name, company_url, company_domain, logo_url = _extract_company_info(body.ads)

    if not company_domain:
        raise HTTPException(
            status_code=400,
            detail="Could not determine company domain from ad destination URLs",
        )

    try:
        # 1. Create LeadgenVocRun
        from app.models.leadgen_voc import LeadgenVocRun

        run_id = uuid.uuid4().hex
        run = LeadgenVocRun(
            run_id=run_id,
            work_email=current_user.email,
            company_domain=company_domain,
            company_url=company_url,
            company_name=company_name,
            review_count=0,
            coding_enabled=True,
            coding_status="pending_import",
            payload={"source": "extension_leadgen"},
        )
        db.add(run)
        db.flush()

        # 2. Create client via existing helper
        from app.services.leadgen_voc_service import create_or_update_lead_client

        lead_client = create_or_update_lead_client(db, run, founder_user_id=current_user.id)
        if logo_url:
            lead_client.logo_url = logo_url
        if company_url:
            lead_client.client_url = company_url
        db.flush()

        # 3. Import ads into the new client
        result = _do_import(lead_client.id, body, db, current_user)

        db.commit()

        # 4. Launch background chain in daemon thread
        import_id = result.import_id
        _start_leadgen_background(import_id, run_id)

        logger.info(
            "Leadgen import: company=%s, domain=%s, run_id=%s, ads=%d",
            company_name, company_domain, run_id, result.ad_count,
        )

        return ExtensionLeadgenImportResponse(
            import_id=import_id,
            run_id=run_id,
            company_name=company_name,
            company_domain=company_domain,
            ad_count=result.ad_count,
            skipped_count=result.skipped_count,
            media_count=result.media_count,
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception("Leadgen extension import failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


def _start_leadgen_background(import_id: UUID, run_id: str):
    """Launch the leadgen background chain in a daemon thread."""
    def _run():
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(_leadgen_post_import_background(import_id, run_id))
        finally:
            loop.close()

    threading.Thread(target=_run, daemon=True).start()
    logger.info("Leadgen background chain started: import=%s, run=%s", import_id, run_id)


async def _leadgen_post_import_background(import_id: UUID, run_id: str):
    """
    Background chain after leadgen import:
    1. Run Gemini video analysis
    2. Package deduplicated ads + transcripts as company context
    3. Start the lead gen pipeline
    """
    from sqlalchemy.orm.attributes import flag_modified
    from app.models.leadgen_voc import LeadgenVocRun

    db = SessionLocal()
    try:
        # Step 1: Gemini video analysis (await completion)
        logger.info("[leadgen %s] Starting Gemini video analysis", run_id)
        await _analyze_videos_background(import_id)
        logger.info("[leadgen %s] Gemini analysis complete", run_id)

        # Step 2: Collect all ads for this import
        ads = (
            db.query(AdLibraryAd)
            .filter(AdLibraryAd.import_id == import_id)
            .all()
        )

        if not ads:
            logger.warning("[leadgen %s] No ads found for import %s", run_id, import_id)
            return

        # Step 3: Build deduplicated context
        context_text = _build_ad_context(ads, db)

        # Step 4: Store context in run payload
        run = db.query(LeadgenVocRun).filter(LeadgenVocRun.run_id == run_id).first()
        if not run:
            logger.error("[leadgen %s] Run not found", run_id)
            return

        payload = run.payload or {}
        payload["ad_context_text"] = context_text
        payload["import_id"] = str(import_id)
        run.payload = payload
        flag_modified(run, "payload")
        db.commit()

        logger.info("[leadgen %s] Ad context packaged (%d chars), starting pipeline", run_id, len(context_text))

        # Step 5: Start the lead gen pipeline
        from app.services.leadgen_pipeline_runner import run_full_pipeline_background
        run_full_pipeline_background(run_id)

    except Exception as e:
        logger.exception("[leadgen %s] Background chain failed: %s", run_id, e)
        try:
            run = db.query(LeadgenVocRun).filter(LeadgenVocRun.run_id == run_id).first()
            if run:
                run.coding_status = "failed"
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


def _build_ad_context(ads, db):
    """Build deduplicated company context string from imported ads + transcripts."""
    company_name = ads[0].page_name or "Unknown" if ads else "Unknown"

    # Deduplicate ads by primary_text
    seen_texts = set()
    unique_ads = []
    for ad in ads:
        text_key = (ad.primary_text or "").strip()
        if text_key and text_key not in seen_texts:
            seen_texts.add(text_key)
            unique_ads.append(ad)

    # Build ad summaries
    ad_sections = []
    for i, ad in enumerate(unique_ads, 1):
        parts = []
        if ad.headline:
            parts.append(f"Headline: {ad.headline}")
        if ad.primary_text:
            parts.append(f"Copy: {ad.primary_text[:500]}")
        if ad.cta:
            parts.append(f"CTA: {ad.cta}")
        if ad.destination_url:
            parts.append(f"URL: {ad.destination_url}")
        if parts:
            ad_sections.append(f"Ad {i}:\n" + "\n".join(parts))

    # Collect and deduplicate transcripts
    seen_transcripts = set()
    transcripts = []
    for ad in ads:
        for media in (ad.media_items or []):
            analysis = media.video_analysis_json
            if not analysis or not isinstance(analysis, dict):
                continue
            transcript = (analysis.get("transcript") or "").strip()
            if transcript and transcript not in seen_transcripts:
                seen_transcripts.add(transcript)
                transcripts.append({
                    "headline": ad.headline or "Untitled",
                    "transcript": transcript,
                })
            if len(transcripts) >= 10:
                break
        if len(transcripts) >= 10:
            break

    # Assemble context
    parts = [f"Company: {company_name}"]
    if ad_sections:
        parts.append(f"\n## Ads (from Meta Ad Library)\n")
        parts.append("\n---\n".join(ad_sections))
    if transcripts:
        parts.append(f"\n## Video Transcripts\n")
        for t in transcripts:
            parts.append(f"Ad: {t['headline']}\nTranscript: {t['transcript']}\n---")

    return "\n".join(parts)
