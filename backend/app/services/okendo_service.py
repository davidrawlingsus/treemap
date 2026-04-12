"""
Okendo review scraper.

Fetches reviews from the public Okendo widget API and normalizes
them to the standard review format used by the VoC pipeline.
"""

import logging
from typing import Any, Dict, List

import requests

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

API_BASE = "https://api.okendo.io/v1/stores"


def fetch_okendo_reviews(
    subscriber_id: str,
    max_reviews: int = 200,
    per_page: int = 50,
) -> List[Dict[str, Any]]:
    """Fetch reviews from Okendo public API.

    Returns normalized review dicts matching the standard format.
    Returns empty list on any API error (pipeline continues with other sources).
    """
    if not subscriber_id or subscriber_id == "detected":
        logger.warning("[okendo] No valid subscriber ID, skipping")
        return []

    all_reviews: List[Dict[str, Any]] = []
    url = f"{API_BASE}/{subscriber_id}/reviews"
    offset = 0

    logger.info("[okendo] Fetching reviews for subscriber=%s url=%s (max=%d)", subscriber_id, url, max_reviews)

    while len(all_reviews) < max_reviews:
        try:
            resp = requests.get(
                url,
                params={"limit": per_page, "offset": offset},
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "application/json",
                },
                timeout=15,
            )
            logger.info("[okendo] Response status=%d for offset=%d", resp.status_code, offset)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.warning("[okendo] API request failed (offset %d): %s", offset, e)
            break

        # Okendo may nest reviews under different keys
        reviews = data.get("reviews", [])
        if not reviews and isinstance(data, list):
            reviews = data  # response is the array directly
        if not reviews:
            logger.info("[okendo] No reviews in response at offset %d. Keys: %s", offset, list(data.keys()) if isinstance(data, dict) else type(data))
            break

        for item in reviews:
            normalized = _normalize_review(item)
            if normalized:
                all_reviews.append(normalized)

        logger.info("[okendo] Offset %d: %d reviews (total: %d)", offset, len(reviews), len(all_reviews))

        # Check if there are more pages
        has_more = data.get("has_more", False) or len(reviews) >= per_page
        if not has_more or len(all_reviews) >= max_reviews:
            break

        offset += per_page

    logger.info("[okendo] Fetched %d reviews for subscriber=%s", len(all_reviews), subscriber_id[:12])
    return all_reviews[:max_reviews]


def _normalize_review(item: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize an Okendo API review to the standard format."""
    body = (item.get("body") or item.get("text") or "").strip()
    title = (item.get("title") or "").strip()
    if not body and not title:
        return {}

    reviewer_name = item.get("reviewer", {}).get("displayName", "") if isinstance(item.get("reviewer"), dict) else ""
    reviewer_name = reviewer_name or "Anonymous"

    return {
        "review_id": str(item.get("reviewId") or item.get("id") or ""),
        "rating": item.get("rating"),
        "title": title,
        "text": body,
        "published_at": item.get("dateCreated") or item.get("createdAt"),
        "language": "en",
        "country": "",
        "review_url": "",
        "reviewer_name": reviewer_name,
        "source": "okendo",
        "raw_item": item,
    }
