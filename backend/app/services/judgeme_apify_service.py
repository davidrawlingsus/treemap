"""
Apify integration for fetching Judge.me reviews.

Mirrors the trustpilot_apify_service.py pattern — calls an Apify actor
with the shop domain as input, then normalizes the dataset output.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

logger = logging.getLogger(__name__)


def _first_non_empty(data: Dict[str, Any], keys: List[str]) -> Optional[Any]:
    for key in keys:
        value = data.get(key)
        if value not in (None, "", []):
            return value
    return None


def _normalize_apify_review(item: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a Judge.me Apify review to the standard format."""
    text = _first_non_empty(item, ["body", "text", "content", "reviewBody", "review"]) or ""
    title = _first_non_empty(item, ["title", "headline", "reviewTitle"]) or ""
    if not text.strip() and not title.strip():
        return {}

    reviewer = item.get("reviewer") if isinstance(item.get("reviewer"), dict) else {}
    reviewer_name = (
        _first_non_empty(item, ["reviewer_name", "author"])
        or _first_non_empty(reviewer, ["displayName", "name"])
        or "Anonymous"
    )

    return {
        "review_id": str(_first_non_empty(item, ["id", "reviewId", "review_id"]) or ""),
        "rating": _first_non_empty(item, ["rating", "stars", "score"]),
        "title": title.strip(),
        "text": text.strip(),
        "published_at": _first_non_empty(item, [
            "created_at", "publishedAt", "date", "createdAt", "reviewDate",
        ]),
        "language": _first_non_empty(item, ["language", "lang"]) or "en",
        "country": _first_non_empty(item, ["country", "countryCode"]) or "",
        "review_url": _first_non_empty(item, ["url", "reviewUrl"]) or "",
        "reviewer_name": reviewer_name,
        "source": "judge_me_apify",
        "raw_item": item,
    }


def _build_actor_input(shop_domain: str, max_reviews: int) -> Dict[str, Any]:
    """Build input for the Judge.me Apify actor."""
    return {
        "shopDomain": shop_domain,
        "maxReviews": max_reviews,
    }


def fetch_judgeme_reviews(
    shop_domain: str,
    settings: Any,
    max_reviews: int = 200,
) -> List[Dict[str, Any]]:
    """Fetch Judge.me reviews via Apify actor.

    Returns normalized review dicts matching the standard format.
    Raises HTTPException on config or actor errors.
    """
    if not shop_domain or shop_domain == "detected":
        logger.warning("[judge.me] No valid shop domain, skipping")
        return []

    try:
        from apify_client import ApifyClient
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="apify-client package is not installed on the backend",
        )

    api_token = settings.apify_api_token
    actor_id = settings.apify_judgeme_actor_id
    if not api_token:
        raise HTTPException(status_code=500, detail="Apify token is not configured")
    if not actor_id:
        logger.warning("[judge.me] Apify Judge.me actor ID not configured, skipping")
        return []

    max_reviews_limit = settings.apify_max_reviews
    bounded = max(1, min(max_reviews, max_reviews_limit))
    actor_input = _build_actor_input(shop_domain, bounded)

    logger.info(
        "Running Apify Judge.me actor: actor_id=%s shop=%s max_reviews=%d",
        actor_id, shop_domain, bounded,
    )

    client = ApifyClient(api_token)
    timeout = max(settings.apify_timeout_seconds, bounded * 2 + 60)

    try:
        run = client.actor(actor_id).call(
            run_input=actor_input,
            wait_secs=timeout,
        )
    except Exception as exc:
        logger.error("Apify Judge.me actor run failed for %s: %s", shop_domain, exc)
        raise HTTPException(status_code=502, detail="Failed to run Apify Judge.me actor")

    dataset_id = (run or {}).get("defaultDatasetId")
    if not dataset_id:
        logger.error("Apify run missing dataset ID: %s", run)
        raise HTTPException(status_code=502, detail="Apify run did not return a dataset ID")

    try:
        items = list(client.dataset(dataset_id).iterate_items())
    except Exception as exc:
        logger.error("Apify dataset fetch failed for %s: %s", shop_domain, exc)
        raise HTTPException(status_code=502, detail="Failed to fetch Judge.me dataset from Apify")

    if not isinstance(items, list):
        logger.error("Apify dataset response is not a list: %s", type(items))
        return []

    normalized = [_normalize_apify_review(item) for item in items if isinstance(item, dict)]
    normalized = [r for r in normalized if r]  # filter empty

    logger.info(
        "Apify Judge.me completed: shop=%s raw=%d normalized=%d",
        shop_domain, len(items), len(normalized),
    )
    return normalized[:max_reviews]
