"""
Creative MRI report API.
POST /api/clients/{client_id}/creative-mri/report
Body: { ads?: [...], ad_library_import_id?: uuid }.
If ads omitted, load from Ad Library import (or latest for client).
Video ads are analyzed via Gemini when video_analysis_json is missing.
Use ?stream=1 to get SSE progress events + final report.
Reports are stored in DB; use GET to retrieve or poll status.
"""
import asyncio
import json
import logging
import queue
import time
from datetime import datetime, timezone
from uuid import UUID

# #region agent log
import os as _diag_os
_DEBUG_LOG_DIR = _diag_os.path.join(_diag_os.path.dirname(__file__), "..", "..", "..", "..", ".cursor")
DEBUG_LOG = _diag_os.path.join(_DEBUG_LOG_DIR, "debug.log")
def _diag(msg: str, data: dict = None, hyp: str = None):
    try:
        _diag_os.makedirs(_DEBUG_LOG_DIR, exist_ok=True)
        with open(DEBUG_LOG, "a") as f:
            f.write(json.dumps({"location": "creative_mri.py", "message": msg, "data": data or {}, "timestamp": int(time.time() * 1000), "hypothesisId": hyp}) + "\n")
    except Exception:
        pass
# #endregion

from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session, joinedload

from app.config import get_settings
from app.database import get_db, SessionLocal
from app.models import User, Client, AdLibraryImport, AdLibraryAd, CreativeMRIReport
from app.auth import get_current_active_founder
from app.services.creative_mri.llm import get_creative_mri_prompts
from app.services.creative_mri.pipeline import run_creative_mri_pipeline
from app.services.creative_mri.synthesize import run_synthesize
from app.services.gemini_video_service import GeminiVideoService
from app.schemas.creative_mri import (
    CreativeMRIReportResponse,
    CreativeMRIReportListResponse,
    CreativeMRIReportListItem,
    CreativeMRIReportHistoryResponse,
    CreativeMRIReportHistoryItem,
)

router = APIRouter()
logger = logging.getLogger(__name__)


def _format_sse(data: dict) -> str:
    """Format a dict as SSE data line."""
    return f"data: {json.dumps(data)}\n\n"


def _ad_to_dict(ad: AdLibraryAd) -> dict:
    """Convert AdLibraryAd to flat dict for pipeline."""
    d = {
        "id": str(ad.id),
        "library_id": ad.library_id,
        "headline": ad.headline or "",
        "primary_text": ad.primary_text or "",
        "description": ad.description or "",
        "cta": ad.cta,
        "destination_url": ad.destination_url,
        "ad_format": ad.ad_format,
        "started_running_on": ad.started_running_on,
        "ad_delivery_start_time": ad.ad_delivery_start_time,
        "ad_delivery_end_time": ad.ad_delivery_end_time,
        "media_thumbnail_url": ad.media_thumbnail_url,
        "ads_using_creative_count": ad.ads_using_creative_count,
    }
    if ad.media_items:
        d["media_items"] = [
            {
                "media_type": m.media_type,
                "url": m.url,
                "poster_url": m.poster_url,
                "duration_seconds": m.duration_seconds,
                "video_analysis_json": m.video_analysis_json,
            }
            for m in ad.media_items
        ]
    return d


async def _ensure_video_analysis(
    ad: AdLibraryAd, gemini: GeminiVideoService, db: Session
) -> None:
    """For each video media item missing video_analysis_json, call Gemini and save."""
    if not gemini.is_configured():
        return
    for m in ad.media_items or []:
        if m.media_type != "video" or not m.url or m.video_analysis_json:
            continue
        try:
            analysis = await gemini.analyze_video_url(m.url)
            if analysis:
                m.video_analysis_json = analysis
                db.add(m)
                db.commit()
                logger.info("Stored Gemini video analysis for ad %s media %s", ad.id, m.id)
        except Exception as e:
            logger.warning("Gemini video analysis failed for %s: %s", m.url[:60], e)


def _count_pending_videos(library_ads: list) -> int:
    """Count video media items that need Gemini analysis."""
    n = 0
    for ad in library_ads:
        for m in ad.media_items or []:
            if m.media_type == "video" and m.url and not m.video_analysis_json:
                n += 1
    return n


async def _run_report_stream(
    request: Request,
    client_id: UUID,
    body: dict,
    db: Session,
):
    """Async generator yielding SSE progress events and final report. Persists report to DB."""
    # #region agent log
    _diag("stream_start", {"client_id": str(client_id)}, "H1")
    # #endregion
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        yield _format_sse({"error": "Client not found"})
        return

    ads_input = body.get("ads")
    ad_library_import_id = body.get("ad_library_import_id")
    ads = None
    import_id = None

    if ads_input is not None:
        yield _format_sse({"stage": "loading", "current": 1, "total": 1, "message": "Preparing ads..."})
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
                yield _format_sse({"error": "No Ad Library import found. Import from URL first."})
                return
            import_id = latest.id

        yield _format_sse({"stage": "loading", "current": 0, "total": 1, "message": "Loading ads..."})

        library_ads = (
            db.query(AdLibraryAd)
            .filter(AdLibraryAd.import_id == import_id)
            .options(joinedload(AdLibraryAd.media_items))
            .all()
        )
        total_videos = _count_pending_videos(library_ads)

        if total_videos > 0:
            settings = get_settings()
            gemini = GeminiVideoService(api_key=settings.gemini_api_key)
            if gemini.is_configured():
                done = 0
                for ad in library_ads:
                    for m in ad.media_items or []:
                        if m.media_type != "video" or not m.url or m.video_analysis_json:
                            continue
                        try:
                            analysis = await gemini.analyze_video_url(m.url)
                            if analysis:
                                m.video_analysis_json = analysis
                                db.add(m)
                                db.commit()
                            done += 1
                            yield _format_sse({"stage": "video", "current": done, "total": total_videos, "message": f"Analyzing videos {done}/{total_videos}"})
                        except Exception as e:
                            logger.warning("Gemini video analysis failed for %s: %s", m.url[:60], e)
                            done += 1
                            yield _format_sse({"stage": "video", "current": done, "total": total_videos, "message": f"Analyzing videos {done}/{total_videos}"})
            else:
                yield _format_sse({"stage": "video", "current": 0, "total": 0, "message": "Skipping video analysis (Gemini not configured)"})

        ads = [_ad_to_dict(ad) for ad in library_ads]
        if not ads:
            yield _format_sse({"error": "No ads in this import."})
            return

    llm_service = getattr(request.app.state, "llm_service", None)
    if not llm_service:
        yield _format_sse({"error": "LLM service not configured. Set ANTHROPIC_API_KEY."})
        return

    # Create report row for persistence
    report_row = CreativeMRIReport(
        client_id=client_id,
        ad_library_import_id=import_id,
        status="running",
    )
    db.add(report_row)
    db.commit()
    db.refresh(report_row)
    report_id = report_row.id
    # #region agent log
    _diag("report_created", {"report_id": str(report_id), "ad_count": len(ads)}, "H1")
    # #endregion

    def _persist_progress(current: int, total: int, message: str) -> None:
        report_row.progress_current = current
        report_row.progress_total = total
        report_row.progress_message = message
        db.commit()

    yield _format_sse({"stage": "llm", "current": 0, "total": len(ads), "message": "Starting ad copy analysis..."})
    _persist_progress(0, len(ads), "Starting ad copy analysis...")

    system_message, model = get_creative_mri_prompts(db)

    progress_queue = queue.Queue()
    report_ref = []
    pipeline_error = []

    def progress_cb(stage: str, current: int, total: int, message: str):
        progress_queue.put({"stage": stage, "current": current, "total": total, "message": message})

    def run_pipeline():
        # #region agent log
        _diag("pipeline_thread_start", {"report_id": str(report_id)}, "H4")
        # #endregion
        try:
            result = run_creative_mri_pipeline(
                ads,
                llm_service,
                progress_callback=progress_cb,
                system_message=system_message,
                model=model,
            )
            # #region agent log
            _diag("pipeline_thread_done", {"report_id": str(report_id)}, "H4")
            # #endregion
            progress_queue.put({"report": result})
        except Exception as e:
            # #region agent log
            _diag("pipeline_thread_error", {"report_id": str(report_id), "error": str(e)}, "H4")
            # #endregion
            pipeline_error.append(e)
        progress_queue.put(None)

    loop = asyncio.get_event_loop()
    task = loop.run_in_executor(None, run_pipeline)

    while True:
        try:
            ev = progress_queue.get(timeout=0.1)
            if ev is None:
                break
            if "report" in ev:
                report_ref.append(ev["report"])
                continue
            yield _format_sse(ev)
            curr = ev.get("current")
            total = ev.get("total")
            msg = ev.get("message")
            if curr is not None and total is not None and msg is not None:
                _persist_progress(curr, total, msg)
        except queue.Empty:
            await asyncio.sleep(0.05)

    await task
    # #region agent log
    _diag("stream_after_await_task", {"report_id": str(report_id)}, "H1")
    # #endregion

    if pipeline_error:
        report_row.status = "failed"
        report_row.error_message = str(pipeline_error[0])
        db.commit()
        yield _format_sse({"error": report_row.error_message})
    elif report_ref:
        report = report_ref[0]
        # #region agent log
        _diag("synthesize_start", {"report_id": str(report_id)}, "H4")
        # #endregion
        yield _format_sse({"stage": "synthesize", "current": 0, "total": 1, "message": "Synthesizing executive summary..."})
        _persist_progress(0, 1, "Synthesizing executive summary...")

        from app.services.creative_mri.synthesize import (
            get_synthesized_summary_prompt,
            build_synthesize_payload,
            _call_synthesize_llm,
        )
        prompt_tuple = get_synthesized_summary_prompt(db)
        if prompt_tuple:
            system_message, model = prompt_tuple

            def run_synth():
                return _call_synthesize_llm(report, llm_service, system_message, model)

            synth_result = await asyncio.get_event_loop().run_in_executor(None, run_synth)
        else:
            synth_result = None
        if synth_result:
            report["synthesized_summary"] = synth_result

        report_row.report_json = report
        report_row.status = "complete"
        report_row.completed_at = datetime.now(timezone.utc)
        db.commit()
        # #region agent log
        _diag("stream_done", {"report_id": str(report_id)}, "H1")
        # #endregion
        yield _format_sse({"stage": "done", "report_id": str(report_id), "report": report})


def _run_and_save_report_sync(report_id: UUID, ads: list, app) -> None:
    """Background task: run pipeline and save result to report row."""
    # #region agent log
    _diag("bg_task_start", {"report_id": str(report_id), "ad_count": len(ads)}, "H2")
    # #endregion
    llm_service = getattr(app.state, "llm_service", None) if app else None
    db = SessionLocal()
    try:
        report_row = db.query(CreativeMRIReport).filter(CreativeMRIReport.id == report_id).first()
        if not report_row:
            logger.warning("Report %s not found in background task", report_id)
            return
        try:
            if not llm_service:
                report_row.status = "failed"
                report_row.error_message = "LLM service not configured"
                db.commit()
                return
            system_message, model = get_creative_mri_prompts(db)

            def progress_cb(stage: str, current: int, total: int, message: str) -> None:
                report_row.progress_current = current
                report_row.progress_total = total
                report_row.progress_message = message
                db.commit()

            report_row.progress_current = 0
            report_row.progress_total = len(ads)
            report_row.progress_message = "Starting ad copy analysis..."
            db.commit()

            result = run_creative_mri_pipeline(
                ads,
                llm_service,
                progress_callback=progress_cb,
                system_message=system_message,
                model=model,
            )
            # #region agent log
            _diag("bg_task_pipeline_done", {"report_id": str(report_id)}, "H2")
            # #endregion
            synth_result = run_synthesize(result, llm_service, db)
            if synth_result:
                result["synthesized_summary"] = synth_result
            report_row.report_json = result
            report_row.status = "complete"
            report_row.completed_at = datetime.now(timezone.utc)
            db.commit()
            # #region agent log
            _diag("bg_task_complete", {"report_id": str(report_id)}, "H2")
            # #endregion
        except Exception as e:
            # #region agent log
            _diag("bg_task_error", {"report_id": str(report_id), "error": str(e)}, "H2")
            # #endregion
            logger.exception("Creative MRI pipeline failed for report %s", report_id)
            report_row.status = "failed"
            report_row.error_message = str(e)
            db.commit()
    finally:
        db.close()


@router.post("/api/clients/{client_id}/creative-mri/report")
async def run_creative_mri_report(
    client_id: UUID,
    body: dict,
    request: Request,
    background_tasks: BackgroundTasks,
    stream: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """
    Run Creative MRI report: copy-based effectiveness diagnostics.
    Body: { "ads": [...] } or { "ad_library_import_id": "uuid" }.
    If ads omitted, load ads from ad_library_import_id or latest Ad Library import for client.
    Use ?stream=1 for SSE progress events. Reports are stored; use GET to retrieve.
    """
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    ads_input = body.get("ads")
    ad_library_import_id = body.get("ad_library_import_id")
    import_id = None

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
        library_ads = (
            db.query(AdLibraryAd)
            .filter(AdLibraryAd.import_id == import_id)
            .options(joinedload(AdLibraryAd.media_items))
            .all()
        )
        settings = get_settings()
        gemini = GeminiVideoService(api_key=settings.gemini_api_key)
        for ad in library_ads:
            await _ensure_video_analysis(ad, gemini, db)
        ads = [_ad_to_dict(ad) for ad in library_ads]
        if not ads:
            raise HTTPException(status_code=400, detail="No ads in this import.")

    if stream:
        # #region agent log
        _diag("post_using_stream", {"client_id": str(client_id)}, "H1")
        # #endregion
        return StreamingResponse(
            _run_report_stream(request, client_id, body, db),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
        )

    # Non-stream: create report row, run in background, return 202
    llm_service = getattr(request.app.state, "llm_service", None)
    if not llm_service:
        raise HTTPException(status_code=503, detail="LLM service not configured. Set ANTHROPIC_API_KEY.")

    report_row = CreativeMRIReport(
        client_id=client_id,
        ad_library_import_id=import_id,
        status="running",
    )
    db.add(report_row)
    db.commit()
    db.refresh(report_row)

    # #region agent log
    _diag("post_using_background", {"report_id": str(report_row.id), "client_id": str(client_id)}, "H2")
    # #endregion
    background_tasks.add_task(_run_and_save_report_sync, report_row.id, ads, request.app)
    return JSONResponse(status_code=202, content={"report_id": str(report_row.id)})


@router.get(
    "/api/clients/{client_id}/creative-mri/reports/{report_id}",
    response_model=CreativeMRIReportResponse,
)
def get_creative_mri_report(
    client_id: UUID,
    report_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Get a stored Creative MRI report. Returns full report only when status=complete."""
    report = (
        db.query(CreativeMRIReport)
        .filter(
            CreativeMRIReport.id == report_id,
            CreativeMRIReport.client_id == client_id,
        )
        .first()
    )
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return CreativeMRIReportResponse(
        id=report.id,
        client_id=report.client_id,
        ad_library_import_id=report.ad_library_import_id,
        status=report.status,
        report=report.report_json if report.status == "complete" else None,
        error_message=report.error_message,
        progress_current=report.progress_current,
        progress_total=report.progress_total,
        progress_message=report.progress_message,
        created_at=report.created_at,
        completed_at=report.completed_at,
    )


@router.get(
    "/api/clients/{client_id}/creative-mri/reports",
    response_model=CreativeMRIReportListResponse,
)
def list_creative_mri_reports(
    client_id: UUID,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """List stored reports for a client, ordered by created_at desc."""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    reports = (
        db.query(CreativeMRIReport)
        .filter(CreativeMRIReport.client_id == client_id)
        .order_by(CreativeMRIReport.created_at.desc())
        .limit(limit)
        .all()
    )
    items = [
        CreativeMRIReportListItem(
            id=r.id,
            client_id=r.client_id,
            ad_library_import_id=r.ad_library_import_id,
            status=r.status,
            created_at=r.created_at,
            completed_at=r.completed_at,
        )
        for r in reports
    ]
    return CreativeMRIReportListResponse(items=items)


@router.get(
    "/api/creative-mri/reports",
    response_model=CreativeMRIReportHistoryResponse,
)
def list_all_creative_mri_reports(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """List all stored Creative MRI reports across clients (for History tab), ordered by created_at desc."""
    reports = (
        db.query(CreativeMRIReport)
        .options(joinedload(CreativeMRIReport.client))
        .order_by(CreativeMRIReport.created_at.desc())
        .limit(limit)
        .all()
    )
    items = []
    for r in reports:
        client_name = r.client.name if r.client else "—"
        ad_count = None
        if r.status == "complete" and r.report_json and isinstance(r.report_json, dict):
            meta = r.report_json.get("meta") or {}
            ad_count = meta.get("total_ads")
        items.append(
            CreativeMRIReportHistoryItem(
                id=r.id,
                client_id=r.client_id,
                client_name=client_name,
                status=r.status,
                ad_count=ad_count,
                created_at=r.created_at,
                completed_at=r.completed_at,
            )
        )
    return CreativeMRIReportHistoryResponse(items=items)
