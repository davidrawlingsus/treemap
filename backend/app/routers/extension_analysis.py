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

from sqlalchemy.orm import Session

from app.auth import get_current_user_flexible, get_optional_current_user
from app.config import get_settings
from app.database import get_db
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
    max_reviews: int = Field(50, ge=1, le=100)
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
    """Extract (root_domain, full_url) from a destination URL.

    Strips www. and common marketing subdomains (lp, go, shop, get, try,
    promo, offers, info, pages, landing, click, links) so that review
    detection hits the main domain, not a landing page subdomain.
    """
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

        # Strip common marketing/landing page subdomains to get the root domain
        marketing_subdomains = {
            "lp", "go", "shop", "get", "try", "promo", "offers",
            "info", "pages", "landing", "click", "links", "track",
            "app", "start", "join", "buy", "order", "checkout",
        }
        parts = host.split(".")
        while len(parts) > 2 and parts[0] in marketing_subdomains:
            parts.pop(0)
        root_domain = ".".join(parts)

        return root_domain, f"https://{root_domain}"
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
    current_user: Optional[User] = Depends(get_optional_current_user),
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
    current_user: Optional[User] = Depends(get_optional_current_user),
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


class OpportunityRequest(BaseModel):
    ad_synthesis_text: str = Field(..., description="Ad copy synthesis text")
    signal_text: str = Field(..., description="Review signal analysis text")
    ad_copy_score: int = Field(..., ge=1, le=10)
    signal_score: int = Field(..., ge=1, le=10)
    opportunity_score: float = Field(..., description="Composite opportunity score 1-10 based on headroom and signal leverage")


@router.post("/opportunity")
def opportunity_overlay(
    body: OpportunityRequest,
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """Stream opportunity overlay text when gap is significant."""
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise HTTPException(status_code=503, detail="Anthropic API key not configured")

    from app.services.ad_analysis_service import stream_opportunity

    text_gen = stream_opportunity(
        ad_synthesis_text=body.ad_synthesis_text,
        signal_text=body.signal_text,
        ad_copy_score=body.ad_copy_score,
        signal_score=body.signal_score,
        opportunity_score=body.opportunity_score,
        anthropic_api_key=settings.anthropic_api_key,
    )

    return StreamingResponse(
        _sse_generator(text_gen),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


@router.post("/detect-reviews", response_model=DetectReviewsResponse)
def detect_reviews(
    body: DetectReviewsRequest,
    current_user: Optional[User] = Depends(get_optional_current_user),
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
    current_user: Optional[User] = Depends(get_optional_current_user),
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
    source_line = (
        f"===SOURCE===\n"
        f"PLATFORM: {fetch_result.platform_display}\n"
        f"REVIEWS: {len(fetch_result.reviews)}\n"
        f"===END===\n"
    )

    if not fetch_result.reviews:
        def no_reviews_gen():
            yield source_line
            yield "===SUMMARY===\n"
            yield f"SIGNAL_SCORE: 1\nHIGH: 0\nMEDIUM: 0\nLOW: 0\n"
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


# ---------------------------------------------------------------------------
# Domain check — does a client exist for this domain? (no auth needed)
# ---------------------------------------------------------------------------

class CheckDomainRequest(BaseModel):
    destination_url: str = Field(..., description="Destination URL from extracted ads")


@router.post("/check-domain")
def check_domain(
    body: CheckDomainRequest,
    db: Session = Depends(get_db),
):
    """Check if any client exists for this destination URL's domain. No auth required."""
    domain, _ = _extract_domain(body.destination_url)
    if not domain:
        return {"exists": False}

    from app.models import AuthorizedDomain, Client
    from app.models.authorized_domain import AuthorizedDomainClient
    from sqlalchemy import or_

    domain_parts = domain.split(".")
    candidate_domains = []
    for i in range(len(domain_parts) - 1):
        candidate_domains.append(".".join(domain_parts[i:]))

    client = (
        db.query(Client)
        .join(AuthorizedDomainClient, AuthorizedDomainClient.client_id == Client.id)
        .join(AuthorizedDomain, AuthorizedDomain.id == AuthorizedDomainClient.domain_id)
        .filter(AuthorizedDomain.domain.in_(candidate_domains))
        .first()
    )

    if not client:
        return {"exists": False}

    return {"exists": True, "client_id": str(client.id), "client_name": client.name}


# ---------------------------------------------------------------------------
# Client matching — does this domain belong to an existing client?
# ---------------------------------------------------------------------------

class MatchClientRequest(BaseModel):
    destination_url: str = Field(..., description="Destination URL from extracted ads")


class MatchClientResponse(BaseModel):
    matched: bool
    client_id: Optional[str] = None
    client_name: Optional[str] = None


@router.post("/match-client", response_model=MatchClientResponse)
def match_client(
    body: MatchClientRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """Check if the destination URL matches an existing client for this user."""
    if not current_user:
        return MatchClientResponse(matched=False)

    domain, _ = _extract_domain(body.destination_url)
    if not domain:
        return MatchClientResponse(matched=False)

    from app.models import AuthorizedDomain, Client, Membership
    from app.models.authorized_domain import AuthorizedDomainClient

    # Find client by authorized domain where user has membership
    # Match exact domain OR subdomain (e.g. lp.example.com matches example.com)
    from sqlalchemy import or_

    # Build list of candidate domains: "lp.cellexialabs.com" → ["lp.cellexialabs.com", "cellexialabs.com"]
    domain_parts = domain.split(".")
    candidate_domains = []
    for i in range(len(domain_parts) - 1):
        candidate_domains.append(".".join(domain_parts[i:]))

    client = (
        db.query(Client)
        .join(AuthorizedDomainClient, AuthorizedDomainClient.client_id == Client.id)
        .join(AuthorizedDomain, AuthorizedDomain.id == AuthorizedDomainClient.domain_id)
        .join(Membership, Membership.client_id == Client.id)
        .filter(
            AuthorizedDomain.domain.in_(candidate_domains),
            Membership.user_id == current_user.id,
        )
        .first()
    )

    if not client:
        return MatchClientResponse(matched=False)

    return MatchClientResponse(
        matched=True,
        client_id=str(client.id),
        client_name=client.name,
    )


# ---------------------------------------------------------------------------
# Cached results — serve existing import if already analyzed
# ---------------------------------------------------------------------------

class CachedAnalysisResponse(BaseModel):
    cached: bool
    import_id: Optional[str] = None
    ad_copy_score: Optional[int] = None
    signal_score: Optional[int] = None
    opportunity_score: Optional[float] = None
    synthesis_text: Optional[str] = None
    signal_text: Optional[str] = None
    ads: Optional[List[dict]] = None


@router.get("/cached-analysis")
def get_cached_analysis(
    advertiser_url: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """Return cached analysis if this advertiser was already analyzed for this user's client."""
    if not current_user:
        return {"cached": False}

    from app.models import AdLibraryImport, AdLibraryAd, Membership

    # Find imports for this source URL where user has access
    imp = (
        db.query(AdLibraryImport)
        .join(Membership, Membership.client_id == AdLibraryImport.client_id)
        .filter(
            Membership.user_id == current_user.id,
            AdLibraryImport.source_url.contains(advertiser_url),
            AdLibraryImport.ad_copy_score.isnot(None),
        )
        .order_by(AdLibraryImport.imported_at.desc())
        .first()
    )

    if not imp:
        return {"cached": False}

    ads = (
        db.query(AdLibraryAd)
        .filter(AdLibraryAd.import_id == imp.id)
        .all()
    )

    return {
        "cached": True,
        "import_id": str(imp.id),
        "ad_copy_score": imp.ad_copy_score,
        "signal_score": imp.signal_score,
        "opportunity_score": imp.opportunity_score,
        "synthesis_text": imp.synthesis_text,
        "signal_text": imp.signal_text,
        "ads": [
            {
                "library_id": ad.library_id,
                "analysis_json": ad.analysis_json,
            }
            for ad in ads
            if ad.analysis_json
        ],
    }
