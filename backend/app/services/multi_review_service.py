"""
Multi-platform review orchestrator.

Detects which review platforms a company uses, fetches from each,
and returns reviews from the platform with the most results.
Tries free APIs (Reviews.io, Yotpo) before paid (Trustpilot via Apify).
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
}


def fetch_reviews_best_platform(
    settings: Any,
    company_url: str,
    company_domain: str,
    max_reviews: int = 200,
    on_status: Any = None,
) -> FetchResult:
    """Detect review platforms and fetch from the one with the most reviews.

    Tries free APIs first (Reviews.io, Yotpo), then Trustpilot via Apify.
    Returns a FetchResult with the winning platform's reviews.

    Args:
        on_status: Optional callback(status_str) for progress updates.
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

    # Fetch from each platform, trying free APIs first
    results: List[FetchResult] = []

    # Sort: free APIs first (reviews_io, yotpo), then paid (trustpilot)
    free_first = sorted(detected, key=lambda p: 0 if p.platform != "trustpilot" else 1)

    for platform in free_first:
        if on_status:
            on_status(f"scraping_{platform.platform}")

        display = PLATFORM_DISPLAY.get(platform.platform, platform.platform)
        logger.info("[multi-review] Trying %s (identifier=%s)...", display, platform.identifier[:30])

        try:
            if platform.platform == "reviews_io":
                from app.services.reviews_io_service import fetch_reviews_io_reviews
                reviews = fetch_reviews_io_reviews(platform.identifier, max_reviews)
            elif platform.platform == "yotpo":
                from app.services.yotpo_service import fetch_yotpo_reviews
                reviews = fetch_yotpo_reviews(platform.identifier, max_reviews)
            elif platform.platform == "trustpilot":
                from app.services.trustpilot_apify_service import fetch_trustpilot_reviews_by_domain
                reviews = fetch_trustpilot_reviews_by_domain(
                    settings=settings,
                    domain=platform.identifier,
                    max_reviews=max_reviews,
                )
            else:
                continue

            result = FetchResult(
                platform=platform.platform,
                platform_display=display,
                reviews=reviews,
            )
            results.append(result)
            logger.info("[multi-review] %s returned %d reviews", display, len(reviews))

            # If a free API returned enough reviews, skip Trustpilot (saves cost)
            if platform.platform != "trustpilot" and len(reviews) >= 20:
                logger.info("[multi-review] %s has sufficient reviews, skipping remaining platforms", display)
                break

        except Exception as e:
            err_msg = getattr(e, "detail", None) or str(e)
            logger.warning("[multi-review] %s failed: %s", display, err_msg)
            results.append(FetchResult(
                platform=platform.platform,
                platform_display=display,
                reviews=[],
                error=str(err_msg),
            ))

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
