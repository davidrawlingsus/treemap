"""
Stamped.io review scraper.

Fetches reviews from the public Stamped widget API and normalizes
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

API_BASE = "https://stamped.io/api/widget/reviews"


def fetch_stamped_reviews(
    store_url: str,
    api_key: str,
    max_reviews: int = 200,
    per_page: int = 50,
) -> List[Dict[str, Any]]:
    """Fetch reviews from Stamped.io public widget API.

    Returns normalized review dicts matching the standard format.
    Returns empty list on any API error (pipeline continues with other sources).
    """
    if not api_key or api_key == "detected":
        logger.warning("[stamped] No valid API key, skipping")
        return []

    all_reviews: List[Dict[str, Any]] = []
    page = 1

    logger.info("[stamped] Fetching reviews for store=%s (max=%d)", store_url, max_reviews)

    while len(all_reviews) < max_reviews:
        try:
            resp = requests.get(
                API_BASE,
                params={
                    "storeUrl": store_url,
                    "apiKey": api_key,
                    "page": page,
                    "per_page": per_page,
                },
                headers={"User-Agent": USER_AGENT},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.warning("[stamped] API request failed (page %d): %s", page, e)
            break

        reviews = data.get("data", []) if isinstance(data, dict) else data if isinstance(data, list) else []
        if not reviews:
            break

        for item in reviews:
            normalized = _normalize_review(item)
            if normalized:
                all_reviews.append(normalized)

        logger.info("[stamped] Page %d: %d reviews (total: %d)", page, len(reviews), len(all_reviews))

        if len(reviews) < per_page or len(all_reviews) >= max_reviews:
            break

        page += 1

    logger.info("[stamped] Fetched %d reviews for store=%s", len(all_reviews), store_url)
    return all_reviews[:max_reviews]


def _normalize_review(item: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a Stamped.io API review to the standard format."""
    body = (item.get("body") or item.get("reviewMessage") or "").strip()
    title = (item.get("title") or item.get("reviewTitle") or "").strip()
    if not body and not title:
        return {}

    author = item.get("author", {}) if isinstance(item.get("author"), dict) else {}
    reviewer_name = (
        author.get("firstName", "") + " " + author.get("lastName", "")
    ).strip() or author.get("name", "") or item.get("author", "") or "Anonymous"

    return {
        "review_id": str(item.get("id") or item.get("reviewId") or ""),
        "rating": item.get("reviewRating") or item.get("rating"),
        "title": title,
        "text": body,
        "published_at": item.get("reviewDate") or item.get("createdAt"),
        "language": "en",
        "country": "",
        "review_url": "",
        "reviewer_name": reviewer_name if isinstance(reviewer_name, str) else "Anonymous",
        "source": "stamped",
        "raw_item": item,
    }
