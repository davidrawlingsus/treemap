"""
MRI Media Diagnostic Instrumentation.
Logs scraping, saving, and rendering of images/videos for Creative MRI reports.
Writes to .cursor/mri_media_diagnostic.log (JSON-lines) for post-run analysis.
"""
import json
import os
import time
from typing import Any, Dict, List, Optional

# backend/app/services -> go up to backend parent (vizualizd) -> .cursor
_LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", ".cursor")
_LOG_PATH = os.path.join(_LOG_DIR, "mri_media_diagnostic.log")


def _log(phase: str, event: str, data: Dict[str, Any]) -> None:
    """Append a diagnostic log entry."""
    try:
        os.makedirs(_LOG_DIR, exist_ok=True)
        entry = {
            "ts": int(time.time() * 1000),
            "phase": phase,
            "event": event,
            **data,
        }
        with open(_LOG_PATH, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


def log_scrape_start(url: str, max_scrolls: int) -> None:
    _log("scrape", "start", {"url": url[:120], "max_scrolls": max_scrolls})


def log_scrape_extract(raw_count: int, ad_cards: List[Dict]) -> None:
    """Log raw extraction: per-ad media counts, sample URLs."""
    media_summary = []
    for i, r in enumerate(ad_cards[:20]):  # First 20 ads
        mi = r.get("mediaItems") or []
        videos = [m for m in mi if m.get("type") == "video"]
        images = [m for m in mi if m.get("type") == "image"]
        sample_urls = [m.get("url", "")[:80] for m in mi[:2]]
        media_summary.append({
            "idx": i,
            "library_id": r.get("libraryId"),
            "media_count": len(mi),
            "videos": len(videos),
            "images": len(images),
            "media_thumbnail_url": (r.get("mediaThumbnailUrl") or "")[:80] or None,
            "sample_urls": sample_urls,
        })
    _log("scrape", "extract", {
        "raw_count": raw_count,
        "ad_cards_with_media": sum(1 for r in ad_cards if (r.get("mediaItems") or [])),
        "total_media_items": sum(len(r.get("mediaItems") or []) for r in ad_cards),
        "media_summary": media_summary,
    })


def log_scrape_done(copy_items_count: int, items_with_media: int) -> None:
    _log("scrape", "done", {
        "copy_items_count": copy_items_count,
        "items_with_media": items_with_media,
    })


def log_import_save(ad_id: str, media_count: int, media_urls: List[str]) -> None:
    _log("import", "save_ad", {
        "ad_id": ad_id,
        "media_count": media_count,
        "media_urls_sample": [u[:80] for u in media_urls[:3]],
    })


def log_import_done(import_id: str, client_id: str, ads_count: int) -> None:
    _log("import", "done", {
        "import_id": import_id,
        "client_id": str(client_id),
        "ads_count": ads_count,
    })


def log_import_error(error: str) -> None:
    _log("import", "error", {"error": error})


def log_mri_load(import_id: str, ads_count: int, ads_media_summary: List[Dict]) -> None:
    """Log ads loaded for MRI: per-ad media_items and media_thumbnail_url."""
    _log("mri", "load_ads", {
        "import_id": str(import_id),
        "ads_count": ads_count,
        "ads_media_summary": ads_media_summary[:30],
    })


def log_mri_ad_to_dict(ad_id: str, media_items_count: int, has_thumbnail: bool) -> None:
    _log("mri", "ad_to_dict", {
        "ad_id": ad_id,
        "media_items_count": media_items_count,
        "media_thumbnail_url": has_thumbnail,
    })


def log_gemini_video_download(url: str, status: int, content_length: int, error: Optional[str]) -> None:
    _log("gemini", "video_download", {
        "url": url[:100],
        "status": status,
        "content_length": content_length,
        "error": error,
    })


def log_gemini_video_analysis(url: str, has_transcript: bool, transcript_len: int) -> None:
    """Log when Gemini returns video analysis (transcript presence)."""
    _log("gemini", "video_analysis", {
        "url": url[:100],
        "has_transcript": has_transcript,
        "transcript_len": transcript_len,
    })


def log_gemini_video_analysis_failed(url: str, reason: str) -> None:
    """Log when Gemini video analysis returns None (download succeeded but analysis failed)."""
    _log("gemini", "video_analysis_failed", {"url": url[:100], "reason": reason})


def log_gemini_image_download(url: str, status: int, content_length: int, error: Optional[str]) -> None:
    _log("gemini", "image_download", {
        "url": url[:100],
        "status": status,
        "content_length": content_length,
        "error": error,
    })


def log_report_ads_serialized(report_id: str, ads_count: int, ads_with_media: int, ads: Optional[List[Dict]] = None) -> None:
    """Log report serialization. If ads provided, also log transcript presence."""
    data: Dict[str, Any] = {
        "report_id": str(report_id),
        "ads_count": ads_count,
        "ads_with_media": ads_with_media,
    }
    if ads:
        videos_with_analysis = 0
        videos_with_transcript = 0
        for a in ads:
            for m in (a.get("media_items") or []):
                if m.get("media_type") != "video":
                    continue
                vaj = m.get("video_analysis_json")
                if vaj and isinstance(vaj, dict):
                    videos_with_analysis += 1
                    t = vaj.get("transcript") or (vaj.get("timeline_first_2s") or {}).get("transcript_excerpt")
                    if t:
                        videos_with_transcript += 1
        data["videos_with_analysis"] = videos_with_analysis
        data["videos_with_transcript"] = videos_with_transcript
    _log("mri", "report_serialized", data)


def log_report_fetched(report_id: str, ads_count: int, ads_with_media: int, sample: List[Dict]) -> None:
    """Log when a report is fetched (GET) - for diagnosing stored reports."""
    _log("mri", "report_fetched", {
        "report_id": str(report_id),
        "ads_count": ads_count,
        "ads_with_media": ads_with_media,
        "sample_ads_media": sample[:5],
    })


def log_mri_path(path: str, report_id: Optional[str] = None) -> None:
    """Log which report path is used: 'stream' or 'background'."""
    _log("mri", "path", {"path": path, "report_id": report_id or ""})


def log_mri_video_phase_start(
    path: str,
    total_videos: int,
    total_pending: int,
    gemini_configured: bool,
    import_id: Optional[str] = None,
) -> None:
    """Log when starting video analysis phase."""
    _log("mri", "video_phase_start", {
        "path": path,
        "total_videos": total_videos,
        "total_pending": total_pending,
        "gemini_configured": gemini_configured,
        "import_id": import_id or "",
    })


def log_mri_video_phase_skipped(path: str, reason: str, total_video_media: int = 0) -> None:
    """Log when video analysis phase is skipped (no pending videos or gemini not configured)."""
    _log("mri", "video_phase_skipped", {"path": path, "reason": reason, "total_video_media": total_video_media})


def log_mri_video_item_before(ad_id: str, media_id: str, url: str, idx: int, total: int) -> None:
    """Log before calling Gemini for a video."""
    _log("mri", "video_item_before", {
        "ad_id": ad_id,
        "media_id": media_id,
        "url_len": len(url),
        "url_preview": url[:120] if url else "",
        "idx": idx,
        "total": total,
    })


def log_mri_video_item_after(
    ad_id: str,
    media_id: str,
    success: bool,
    has_transcript: bool,
    transcript_len: int,
    saved_to_db: bool,
    fail_reason: Optional[str] = None,
) -> None:
    """Log after Gemini returns for a video."""
    _log("mri", "video_item_after", {
        "ad_id": ad_id,
        "media_id": media_id,
        "success": success,
        "has_transcript": has_transcript,
        "transcript_len": transcript_len,
        "saved_to_db": saved_to_db,
        "fail_reason": fail_reason or "",
    })


def log_mri_ads_built_for_pipeline(ads_count: int, path: str, sample: List[Dict]) -> None:
    """Log ads built for pipeline: first 3 ads' media_items with video_analysis_json presence."""
    _log("mri", "ads_built", {
        "path": path,
        "ads_count": ads_count,
        "sample": sample[:3],
    })
