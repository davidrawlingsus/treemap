"""
Extension analysis API — ad copy analysis, review engine detection, review signal scoring.

Called by the Chrome extension popup after ad extraction.
"""
import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
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
    ads: List[AdForAnalysis] = Field(..., min_length=1, max_length=50)


class AnalyzeAdsResponse(BaseModel):
    results: List[Dict[str, Any]]


class DetectReviewsRequest(BaseModel):
    destination_url: str = Field(..., description="Destination URL from any extracted ad")


class DetectedPlatformResponse(BaseModel):
    platform: str
    platform_display: str
    identifier: str
    confidence: str
    scrapable: bool
    scraper_notes: str


class DetectReviewsResponse(BaseModel):
    company_domain: str
    company_url: str
    platforms: List[DetectedPlatformResponse]


class AnalyzeReviewSignalRequest(BaseModel):
    destination_url: str = Field(..., description="Destination URL to find reviews for")
    platform: Optional[str] = Field(None, description="Specific platform to use (auto-detect if omitted)")
    max_reviews: int = Field(20, ge=1, le=50)


class AnalyzeReviewSignalResponse(BaseModel):
    platform_used: str
    platform_display: str
    review_count: int
    signal_results: List[Dict[str, Any]]


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
    "trustpilot": "Scrapable via Apify actor. Public API available.",
    "reviews_io": "Free public API. No auth needed for store reviews.",
    "yotpo": "Public widget API. App key extractable from page source.",
    "google_reviews": "Scrapable via Google Places API + Apify.",
    "judge_me": "Public widget API at judge.me/reviews/{shop}.json. Easily scrapable.",
    "stamped": "Public widget API. Store hash extractable from embed code.",
    "loox": "Widget API available. Requires store identifier from embed.",
    "okendo": "Widget API available via subscriber ID.",
}


def _extract_domain(url: str) -> tuple:
    """Extract (domain, full_url) from a destination URL."""
    try:
        parsed = urlparse(url)
        host = (parsed.netloc or "").lower().split(":")[0]
        if not host:
            # Try adding scheme
            parsed = urlparse(f"https://{url}")
            host = (parsed.netloc or "").lower().split(":")[0]
        if host.startswith("www."):
            host = host[4:]
        # Skip FB tracking redirects
        if "facebook.com" in host or "fb.com" in host:
            return "", ""
        return host, f"https://{host}"
    except Exception:
        return "", ""


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/analyze-ads", response_model=AnalyzeAdsResponse)
def analyze_ads(
    body: AnalyzeAdsRequest,
    current_user: User = Depends(get_current_user_flexible),
):
    """Analyze extracted ad copy through the Full Funnel rubric.

    Returns per-ad scores for hook, mind-movie, specificity, emotional charge,
    VoC density, funnel stage, latency, and an overall grade.
    """
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise HTTPException(status_code=503, detail="Anthropic API key not configured")

    from app.services.ad_analysis_service import analyze_ads_full_funnel

    ads_data = [ad.model_dump() for ad in body.ads]
    results = analyze_ads_full_funnel(ads_data, settings.anthropic_api_key)

    return AnalyzeAdsResponse(results=results)


@router.post("/detect-reviews", response_model=DetectReviewsResponse)
def detect_reviews(
    body: DetectReviewsRequest,
    current_user: User = Depends(get_current_user_flexible),
):
    """Detect which review platform(s) a business uses from their website.

    Fetches the destination URL's homepage HTML and checks for known
    review widget signatures (Trustpilot, Yotpo, Reviews.io, Judge.me, etc.).
    Reports whether each platform can be scraped programmatically.
    """
    domain, company_url = _extract_domain(body.destination_url)
    if not domain:
        raise HTTPException(status_code=400, detail="Could not extract domain from URL")

    from app.services.review_platform_detector import detect_review_platforms

    detected = detect_review_platforms(company_url, domain)

    platforms = []
    for p in detected:
        display = PLATFORM_DISPLAY.get(p.platform, p.platform.title())
        notes = SCRAPER_NOTES.get(p.platform, "Manual scraping may be required.")
        scrapable = p.platform in {"trustpilot", "reviews_io", "yotpo", "google_reviews", "judge_me"}
        platforms.append(DetectedPlatformResponse(
            platform=p.platform,
            platform_display=display,
            identifier=p.identifier,
            confidence=p.confidence,
            scrapable=scrapable,
            scraper_notes=notes,
        ))

    return DetectReviewsResponse(
        company_domain=domain,
        company_url=company_url,
        platforms=platforms,
    )


@router.post("/analyze-review-signal", response_model=AnalyzeReviewSignalResponse)
def analyze_review_signal(
    body: AnalyzeReviewSignalRequest,
    current_user: User = Depends(get_current_user_flexible),
):
    """Fetch reviews from detected platform and analyze them for signal quality.

    High-signal reviews are full of emotion, transformation arcs, and specific detail.
    Low-signal reviews are generic praise ("fast shipping", "great CS").
    """
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
    )

    if not fetch_result.reviews:
        return AnalyzeReviewSignalResponse(
            platform_used=fetch_result.platform,
            platform_display=fetch_result.platform_display,
            review_count=0,
            signal_results=[{
                "summary": True,
                "total_reviews": 0,
                "high_signal_count": 0,
                "medium_signal_count": 0,
                "low_signal_count": 0,
                "overall_signal_grade": "F",
                "top_themes": [],
                "verdict": f"No reviews found for {domain}."
            }],
        )

    # Analyze signal quality
    from app.services.ad_analysis_service import analyze_review_signal as _analyze

    signal_results = _analyze(
        fetch_result.reviews,
        settings.anthropic_api_key,
        max_reviews=body.max_reviews,
    )

    return AnalyzeReviewSignalResponse(
        platform_used=fetch_result.platform,
        platform_display=fetch_result.platform_display,
        review_count=len(fetch_result.reviews),
        signal_results=signal_results,
    )
