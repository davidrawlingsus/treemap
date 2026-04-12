"""
Extension analysis API — ad copy analysis, review engine detection, review signal scoring.

Called by the Chrome extension sidebar after ad extraction.
Ad analysis and review signal endpoints stream text via SSE.
"""
import json
import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.auth import get_current_user_flexible
from app.config import get_settings
from app.models import User

router = APIRouter(prefix="/api/extension", tags=["extension-analysis"])
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class AdForAnalysis(BaseModel):
    library_id: Optional[str] = None
    primary_text: str
    headline: Optional[str] = None
    description: Optional[str] = None
    cta: Optional[str] = None
    ad_format: Optional[str] = None
    started_running_on: Optional[str] = None
    ad_delivery_end_time: Optional[str] = None
    status: Optional[str] = None
    destination_url: Optional[str] = None


class AnalyzeAdsRequest(BaseModel):
    ads: List[AdForAnalysis] = Field(..., min_length=1, max_length=200)


class DetectReviewsRequest(BaseModel):
    destination_url: str = Field(..., description="Destination URL from any extracted ad")
    page_html: Optional[str] = Field(None, description="Pre-fetched HTML from extension (bypasses WAFs)")


class DetectedPlatformResponse(BaseModel):
    platform: str
    platform_display: str
    identifier: str
    confidence: str
    scrapable: bool
    scraper_notes: str
    review_url: Optional[str] = None


class DetectReviewsResponse(BaseModel):
    company_domain: str
    company_url: str
    platforms: List[DetectedPlatformResponse]


class AnalyzeReviewSignalRequest(BaseModel):
    destination_url: str = Field(..., description="Destination URL to find reviews for")
    platform: Optional[str] = Field(None, description="Specific platform to use (auto-detect if omitted)")
    max_reviews: int = Field(20, ge=1, le=50)
    page_html: Optional[str] = Field(None, description="Pre-fetched HTML from extension (bypasses WAFs)")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PLATFORM_DISPLAY = {
    "trustpilot": "Trustpilot",
    "reviews_io": "Reviews.io",
    "yotpo": "Yotpo",
    "google_reviews": "Google Reviews",
    "judge_me": "Judge.me",
    "stamped": "Stamped.io",
    "loox": "Loox",
    "okendo": "Okendo",
}

SCRAPER_NOTES = {
    "trustpilot": "Scrapable via Apify actor. Public reviews page available.",
    "reviews_io": "Free public API. No auth needed for store reviews.",
    "yotpo": "Free public widget API. App key extracted from page source.",
    "google_reviews": "Scrapable via Google Places API + Apify.",
    "judge_me": "Scrapable via Apify actor. Shop domain extracted from page.",
    "stamped": "Free public widget API. API key extracted from embed code.",
    "loox": "Free widget HTML endpoint. Widget ID + hash extracted from iframe.",
    "okendo": "Free public JSON API. Subscriber ID extracted from page.",
}

def _build_review_url(platform: str, identifier: str, domain: str) -> Optional[str]:
    """Construct a public review page URL where available."""
    if platform == "trustpilot" and domain:
        return f"https://www.trustpilot.com/review/{domain}"
    if platform == "reviews_io" and identifier:
        return f"https://www.reviews.io/company-reviews/store/{identifier}"
    if platform == "judge_me" and identifier:
        return f"https://judge.me/reviews/{identifier}"
    return None


SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",
    "Connection": "keep-alive",
}


def _extract_domain(url: str) -> tuple:
    """Extract (domain, full_url) from a destination URL."""
    try:
        parsed = urlparse(url)
        host = (parsed.netloc or "").lower().split(":")[0]
        if not host:
            parsed = urlparse(f"https://{url}")
            host = (parsed.netloc or "").lower().split(":")[0]
        if host.startswith("www."):
            host = host[4:]
        if "facebook.com" in host or "fb.com" in host:
            return "", ""
        return host, f"https://{host}"
    except Exception:
        return "", ""


def _sse_generator(text_gen):
    """Wrap a text generator into SSE data: lines."""
    for chunk in text_gen:
        # Escape newlines for SSE — send each chunk as a data line
        escaped = chunk.replace("\n", "\ndata: ")
        yield f"data: {escaped}\n\n"
    yield "data: [DONE]\n\n"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/analyze-ads")
def analyze_ads(
    body: AnalyzeAdsRequest,
    current_user: User = Depends(get_current_user_flexible),
):
    """Stream Full Funnel ad analysis as formatted text via SSE."""
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise HTTPException(status_code=503, detail="Anthropic API key not configured")

    from app.services.ad_analysis_service import stream_ads_analysis

    ads_data = [ad.model_dump() for ad in body.ads]
    text_gen = stream_ads_analysis(ads_data, settings.anthropic_api_key)

    return StreamingResponse(
        _sse_generator(text_gen),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


class SynthesisRequest(BaseModel):
    analysis_text: str = Field(..., description="Full per-ad analysis text to synthesize")


@router.post("/synthesize")
def synthesize_ads(
    body: SynthesisRequest,
    current_user: User = Depends(get_current_user_flexible),
):
    """Stream opportunity synthesis based on completed ad analysis."""
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise HTTPException(status_code=503, detail="Anthropic API key not configured")

    from app.services.ad_analysis_service import stream_synthesis

    text_gen = stream_synthesis(body.analysis_text, settings.anthropic_api_key)

    return StreamingResponse(
        _sse_generator(text_gen),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


@router.post("/detect-reviews", response_model=DetectReviewsResponse)
def detect_reviews(
    body: DetectReviewsRequest,
    current_user: User = Depends(get_current_user_flexible),
):
    """Detect which review platform(s) a business uses from their website."""
    domain, company_url = _extract_domain(body.destination_url)
    if not domain:
        raise HTTPException(status_code=400, detail="Could not extract domain from URL")

    from app.services.review_platform_detector import detect_review_platforms

    detected = detect_review_platforms(company_url, domain, prefetched_html=body.page_html)

    platforms = []
    for p in detected:
        display = PLATFORM_DISPLAY.get(p.platform, p.platform.title())
        notes = SCRAPER_NOTES.get(p.platform, "Manual scraping may be required.")
        scrapable = p.platform in {"trustpilot", "reviews_io", "yotpo", "google_reviews", "judge_me", "okendo", "stamped", "loox"}
        review_url = _build_review_url(p.platform, p.identifier, domain)
        platforms.append(DetectedPlatformResponse(
            platform=p.platform,
            platform_display=display,
            identifier=p.identifier,
            confidence=p.confidence,
            scrapable=scrapable,
            scraper_notes=notes,
            review_url=review_url,
        ))

    return DetectReviewsResponse(
        company_domain=domain,
        company_url=company_url,
        platforms=platforms,
    )


@router.post("/analyze-review-signal")
def analyze_review_signal(
    body: AnalyzeReviewSignalRequest,
    current_user: User = Depends(get_current_user_flexible),
):
    """Stream review signal analysis as formatted text via SSE."""
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise HTTPException(status_code=503, detail="Anthropic API key not configured")

    domain, company_url = _extract_domain(body.destination_url)
    if not domain:
        raise HTTPException(status_code=400, detail="Could not extract domain from URL")

    # Fetch reviews via multi-platform orchestrator
    from app.services.multi_review_service import fetch_reviews_best_platform

    fetch_result = fetch_reviews_best_platform(
        settings=settings,
        company_url=company_url,
        company_domain=domain,
        max_reviews=body.max_reviews,
        prefetched_html=body.page_html,
    )

    # Build source preamble so the frontend knows which platform was selected
    trace_text = "\n".join(fetch_result.trace) if fetch_result.trace else ""
    source_line = (
        f"===SOURCE===\n"
        f"PLATFORM: {fetch_result.platform_display}\n"
        f"REVIEWS: {len(fetch_result.reviews)}\n"
        f"TRACE: {trace_text}\n"
        f"===END===\n"
    )

    if not fetch_result.reviews:
        def no_reviews_gen():
            yield source_line
            yield "===SUMMARY===\n"
            yield f"GRADE: F\nHIGH: 0\nMEDIUM: 0\nLOW: 0\n"
            yield f"THEMES: none\n"
            yield f"VERDICT: No reviews found for {domain}.\n"
            yield "===END==="

        return StreamingResponse(
            _sse_generator(no_reviews_gen()),
            media_type="text/event-stream",
            headers=SSE_HEADERS,
        )

    from app.services.ad_analysis_service import stream_review_signal

    def signal_with_source():
        yield source_line
        yield from stream_review_signal(
            fetch_result.reviews,
            settings.anthropic_api_key,
            max_reviews=body.max_reviews,
        )

    return StreamingResponse(
        _sse_generator(signal_with_source()),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )
