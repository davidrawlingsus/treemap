"""
Yotpo review scraper.

Fetches site-wide reviews from the public Yotpo widget API and normalizes
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

API_BASE = "https://api.yotpo.com/v1/widget"


def fetch_yotpo_reviews(
    app_key: str,
    max_reviews: int = 200,
    per_page: int = 50,
) -> List[Dict[str, Any]]:
    """Fetch site-wide reviews from Yotpo public widget API.

    Returns normalized review dicts matching the Trustpilot format.
    Returns empty list on any API error (pipeline continues with other sources).
    """
    all_reviews: List[Dict[str, Any]] = []
    page = 1

    logger.info("[yotpo] Fetching reviews for app_key=%s... (max=%d)", app_key[:12], max_reviews)

    while len(all_reviews) < max_reviews:
        url = f"{API_BASE}/{app_key}/products/yotpo_site_reviews/reviews.json"
        try:
            resp = requests.get(
                url,
                params={"per_page": per_page, "page": page},
                headers={"User-Agent": USER_AGENT},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.warning("[yotpo] API request failed (page %d): %s", page, e)
            break

        response = data.get("response", {})
        reviews = response.get("reviews", [])
        if not reviews:
            break

        for item in reviews:
            normalized = _normalize_review(item)
            if normalized:
                all_reviews.append(normalized)

        logger.info("[yotpo] Page %d: %d reviews (total: %d)", page, len(reviews), len(all_reviews))

        # Check pagination
        pagination = response.get("pagination", {})
        total = pagination.get("total", 0)
        total_pages = pagination.get("total_pages") or (total // per_page + 1 if total else 0)
        if page >= total_pages or len(all_reviews) >= max_reviews:
            break

        page += 1

    logger.info("[yotpo] Fetched %d reviews for app_key=%s...", len(all_reviews), app_key[:12])
    return all_reviews[:max_reviews]


def _normalize_review(item: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a Yotpo API review to the standard format."""
    text = (item.get("content") or item.get("body") or "").strip()
    title = (item.get("title") or "").strip()
    if not text and not title:
        return {}

    user = item.get("user", {}) or {}
    reviewer_name = (
        user.get("display_name") or user.get("social_image") or "Anonymous"
    )

    return {
        "review_id": str(item.get("id") or ""),
        "rating": item.get("score"),
        "title": title,
        "text": text,
        "published_at": item.get("created_at"),
        "language": "en",
        "country": "",
        "review_url": "",
        "reviewer_name": reviewer_name,
        "source": "yotpo",
        "raw_item": item,
    }
