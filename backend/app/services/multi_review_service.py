"""
Multi-platform review orchestrator.

Detects which review platforms a company uses, fetches from each,
and returns reviews from the platform with the most results.

Signal ranking: on-site embedded widgets = brand endorsement = highest signal.
Tries free APIs first, then paid (Apify), with Trustpilot as last resort.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class FetchResult:
    platform: str
    platform_display: str
    reviews: List[Dict[str, Any]]
    error: Optional[str] = None


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

# Platforms that cost money per scrape (Apify actors)
_PAID_PLATFORMS = {"trustpilot", "google_reviews", "judge_me"}

# Free on-site widget APIs — highest signal, try these first
_FREE_ONSITE_PLATFORMS = {"reviews_io", "yotpo", "okendo", "stamped", "loox"}


def fetch_reviews_best_platform(
    settings: Any,
    company_url: str,
    company_domain: str,
    max_reviews: int = 200,
    on_status: Any = None,
) -> FetchResult:
    """Detect review platforms and fetch from the best one.

    Signal ranking (on-site widget = brand endorsement = high signal):
    1. Free on-site widgets: Reviews.io, Yotpo, Okendo, Stamped, Loox
    2. Paid on-site: Judge.me (Apify)
    3. Trustpilot — only if widget embedded on site (confidence=high)
    4. Fallback: Trustpilot by domain (always available, lowest signal)
    5. Google Reviews (rarely brand-curated, last resort)

    Short-circuits if any free platform returns ≥20 reviews.
    """
    from app.services.review_platform_detector import detect_review_platforms

    if on_status:
        on_status("detecting_platforms")

    detected = detect_review_platforms(company_url, company_domain)
    logger.info(
        "[multi-review] Detected platforms for %s: %s",
        company_domain,
        ", ".join(f"{p.platform}({p.confidence})" for p in detected),
    )

    # Sort by signal ranking:
    # 1. Free on-site widgets first
    # 2. Paid on-site (Judge.me) second
    # 3. Trustpilot (high confidence = embedded widget) third
    # 4. Trustpilot (low confidence = fallback) fourth
    # 5. Google Reviews last
    def _sort_key(p):
        if p.platform in _FREE_ONSITE_PLATFORMS:
            return 0
        if p.platform == "judge_me":
            return 1
        if p.platform == "trustpilot" and p.confidence == "high":
            return 2
        if p.platform == "trustpilot":
            return 3
        if p.platform == "google_reviews":
            return 4
        return 5

    ranked = sorted(detected, key=_sort_key)

    results: List[FetchResult] = []

    for platform in ranked:
        if on_status:
            on_status(f"scraping_{platform.platform}")

        display = PLATFORM_DISPLAY.get(platform.platform, platform.platform)
        logger.info("[multi-review] Trying %s (identifier=%s)...", display, platform.identifier[:30])

        try:
            reviews = _fetch_from_platform(platform, settings, company_domain, max_reviews)
            if reviews is None:
                continue  # platform skipped (missing config)
        except Exception as e:
            err_msg = getattr(e, "detail", None) or str(e)
            logger.warning("[multi-review] %s failed: %s", display, err_msg)
            results.append(FetchResult(platform.platform, display, [], error=str(err_msg)))
            continue

        result = FetchResult(platform.platform, display, reviews)
        results.append(result)
        logger.info("[multi-review] %s returned %d reviews", display, len(reviews))

        # Short-circuit: if a free on-site platform has enough reviews, skip the rest
        is_free = platform.platform in _FREE_ONSITE_PLATFORMS
        if is_free and len(reviews) >= 20:
            logger.info("[multi-review] %s has sufficient reviews, skipping remaining", display)
            break

    # Pick the platform with the most reviews
    if not results or all(len(r.reviews) == 0 for r in results):
        logger.warning("[multi-review] No reviews found on any platform for %s", company_domain)
        return FetchResult(platform="none", platform_display="None", reviews=[])

    best = max(results, key=lambda r: len(r.reviews))
    logger.info(
        "[multi-review] Best platform for %s: %s with %d reviews (tried: %s)",
        company_domain, best.platform_display, len(best.reviews),
        ", ".join(f"{r.platform_display}={len(r.reviews)}" for r in results),
    )
    return best


def _fetch_from_platform(
    platform: Any,
    settings: Any,
    company_domain: str,
    max_reviews: int,
) -> Optional[List[Dict[str, Any]]]:
    """Fetch reviews from a specific platform. Returns None to skip."""

    if platform.platform == "reviews_io":
        from app.services.reviews_io_service import fetch_reviews_io_reviews
        return fetch_reviews_io_reviews(platform.identifier, max_reviews)

    if platform.platform == "yotpo":
        from app.services.yotpo_service import fetch_yotpo_reviews
        return fetch_yotpo_reviews(platform.identifier, max_reviews)

    if platform.platform == "okendo":
        from app.services.okendo_service import fetch_okendo_reviews
        return fetch_okendo_reviews(platform.identifier, max_reviews)

    if platform.platform == "stamped":
        from app.services.stamped_service import fetch_stamped_reviews
        return fetch_stamped_reviews(
            store_url=f"https://{company_domain}",
            api_key=platform.identifier,
            max_reviews=max_reviews,
        )

    if platform.platform == "loox":
        from app.services.loox_service import fetch_loox_reviews
        # Identifier format: "widget_id|hash" or just "widget_id" or "detected"
        parts = platform.identifier.split("|", 1)
        widget_id = parts[0]
        hash_param = parts[1] if len(parts) > 1 else ""
        if not hash_param or widget_id == "detected":
            logger.info("[multi-review] Loox detected but missing hash param, skipping extraction")
            return None
        return fetch_loox_reviews(widget_id, hash_param, max_reviews)

    if platform.platform == "judge_me":
        from app.services.judgeme_apify_service import fetch_judgeme_reviews
        if not getattr(settings, "apify_judgeme_actor_id", None):
            logger.info("[multi-review] Skipping Judge.me — actor ID not configured")
            return None
        return fetch_judgeme_reviews(platform.identifier, settings, max_reviews)

    if platform.platform == "google_reviews":
        google_key = getattr(settings, "google_places_api_key", None)
        apify_google_actor = getattr(settings, "apify_google_reviews_actor_id", None)
        apify_token = getattr(settings, "apify_api_token", None)
        if not (google_key and apify_token and apify_google_actor):
            logger.info("[multi-review] Skipping Google Reviews — API keys not configured")
            return None
        from app.services.google_reviews_service import fetch_google_reviews_by_domain
        return fetch_google_reviews_by_domain(
            api_key=google_key,
            company_domain=platform.identifier,
            max_reviews=max_reviews,
            apify_api_token=apify_token,
            apify_google_actor_id=apify_google_actor,
            apify_timeout_seconds=getattr(settings, "apify_timeout_seconds", 300),
        )

    if platform.platform == "trustpilot":
        from app.services.trustpilot_apify_service import fetch_trustpilot_reviews_by_domain
        return fetch_trustpilot_reviews_by_domain(
            settings=settings,
            domain=platform.identifier,
            max_reviews=max_reviews,
        )

    logger.warning("[multi-review] Unknown platform: %s", platform.platform)
    return None
