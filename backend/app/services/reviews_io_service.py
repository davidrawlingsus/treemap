"""
Reviews.io review scraper.

Fetches merchant reviews from the public Reviews.io API and normalizes
them to the same format as the Trustpilot scraper output.
"""

import logging
from typing import Any, Dict, List

import requests

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

API_BASE = "https://api.reviews.io/merchant/reviews"


def fetch_reviews_io_reviews(
    store_id: str,
    max_reviews: int = 200,
    per_page: int = 50,
) -> List[Dict[str, Any]]:
    """Fetch reviews from Reviews.io public API.

    Returns normalized review dicts matching the Trustpilot format.
    Returns empty list on any API error (pipeline continues with other sources).
    """
    all_reviews: List[Dict[str, Any]] = []
    page = 1

    logger.info("[reviews.io] Fetching reviews for store=%s (max=%d)", store_id, max_reviews)

    while len(all_reviews) < max_reviews:
        try:
            resp = requests.get(
                API_BASE,
                params={"store": store_id, "page": page, "per_page": per_page},
                headers={"User-Agent": USER_AGENT},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.warning("[reviews.io] API request failed (page %d): %s", page, e)
            break

        reviews = data.get("reviews", [])
        if not reviews:
            break

        for item in reviews:
            normalized = _normalize_review(item)
            if normalized:
                all_reviews.append(normalized)

        logger.info("[reviews.io] Page %d: %d reviews (total: %d)", page, len(reviews), len(all_reviews))

        # Check if there are more pages
        total_pages = data.get("total_pages", 1)
        if page >= total_pages or len(all_reviews) >= max_reviews:
            break

        page += 1

    logger.info("[reviews.io] Fetched %d reviews for store=%s", len(all_reviews), store_id)
    return all_reviews[:max_reviews]


def _normalize_review(item: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a Reviews.io API review to the standard format."""
    text = (item.get("comments") or item.get("review") or "").strip()
    title = (item.get("title") or "").strip()
    if not text and not title:
        return {}

    reviewer = item.get("reviewer", {}) or {}
    reviewer_name = (
        reviewer.get("first_name", "") + " " + reviewer.get("last_name", "")
    ).strip() or reviewer.get("name", "") or "Anonymous"

    return {
        "review_id": str(item.get("review_id") or item.get("id") or ""),
        "rating": item.get("rating"),
        "title": title,
        "text": text,
        "published_at": item.get("date_created") or item.get("timeago"),
        "language": "en",
        "country": reviewer.get("country") or "",
        "review_url": item.get("review_url") or "",
        "reviewer_name": reviewer_name,
        "source": "reviews_io",
        "raw_item": item,
    }
