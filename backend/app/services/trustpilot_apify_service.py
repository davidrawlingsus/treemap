"""
Apify integration for fetching Trustpilot reviews.
"""

import logging
from typing import Any, Dict, List, Optional
import math

from fastapi import HTTPException


logger = logging.getLogger(__name__)


def infer_trustpilot_review_url(domain: str) -> str:
    clean_domain = (domain or "").strip().lower()
    clean_domain = clean_domain.replace("https://", "").replace("http://", "")
    clean_domain = clean_domain.strip("/")
    return f"https://www.trustpilot.com/review/{clean_domain}"


def _first_non_empty(data: Dict[str, Any], keys: List[str]) -> Optional[Any]:
    for key in keys:
        value = data.get(key)
        if value not in (None, "", []):
            return value
    return None


def normalize_apify_review(item: Dict[str, Any]) -> Dict[str, Any]:
    reviewer = item.get("consumer") if isinstance(item.get("consumer"), dict) else {}
    location = item.get("location") if isinstance(item.get("location"), dict) else {}

    return {
        "review_id": _first_non_empty(item, ["id", "reviewId", "review_id"]),
        "rating": _first_non_empty(item, ["rating", "stars", "score", "reviewRatingScore"]),
        "title": _first_non_empty(item, ["title", "headline", "reviewTitle"]),
        "text": _first_non_empty(item, ["text", "content", "reviewText", "review", "reviewDescription"]),
        "published_at": _first_non_empty(
            item,
            ["publishedAtDate", "publishedAt", "date", "createdAt", "reviewDate"],
        ),
        "language": _first_non_empty(item, ["language", "lang", "reviewLanguage"]),
        "country": _first_non_empty(item, ["reviewersCountry"]) or _first_non_empty(location, ["country", "countryCode"]),
        "review_url": _first_non_empty(item, ["reviewUrl", "url"]),
        "reviewer_name": _first_non_empty(item, ["reviewer"]) or _first_non_empty(reviewer, ["displayName", "name"]),
        "source": "trustpilot_apify",
        "raw_item": item,
    }


def _build_actor_input(domain: str, max_reviews: int) -> Dict[str, Any]:
    review_url = infer_trustpilot_review_url(domain)
    # Trustpilot pages commonly expose around 20 reviews per page.
    # Avoid hard-capping at page 1 so larger max_reviews can be fetched.
    estimated_pages = max(1, math.ceil(max_reviews / 20))
    return {
        "companyWebsite": review_url,
        "contentToExtract": "companyInformationAndReviews",
        "sortBy": "recency",
        "filterByStarRating": "",
        "filterByLanguage": "all",
        "filterByVerified": True,
        "filterByCountryOfReviewers": "",
        "startFromPageNumber": 1,
        "endAtPageNumber": estimated_pages,
        "filterByDatePeriod": "any date",
        "Proxy configuration": {"useApifyProxy": False},
        # Keep desired count in payload for observability/debugging.
        "maxReviews": max_reviews,
    }


def fetch_trustpilot_reviews_by_domain(settings: Any, domain: str, max_reviews: int) -> List[Dict[str, Any]]:
    try:
        from apify_client import ApifyClient
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="apify-client package is not installed on the backend",
        )

    api_token = settings.apify_api_token
    actor_id = settings.apify_trustpilot_actor_id
    if not api_token:
        raise HTTPException(status_code=500, detail="Apify token is not configured")
    if not actor_id:
        raise HTTPException(status_code=500, detail="Apify Trustpilot actor ID is not configured")

    max_reviews_limit = settings.apify_max_reviews
    bounded_max_reviews = max(1, min(max_reviews, max_reviews_limit))
    actor_input = _build_actor_input(domain=domain, max_reviews=bounded_max_reviews)
    logger.info(
        "Running Apify Trustpilot actor: actor_id=%s domain=%s requested_max=%s bounded_max=%s",
        actor_id,
        domain,
        max_reviews,
        bounded_max_reviews,
    )
    client = ApifyClient(api_token)

    try:
        run = client.actor(actor_id).call(
            run_input=actor_input,
            wait_secs=settings.apify_timeout_seconds,
        )
    except Exception as exc:
        logger.error("Apify actor run failed for %s: %s", domain, exc)
        raise HTTPException(status_code=502, detail="Failed to run Apify Trustpilot actor")

    dataset_id = (run or {}).get("defaultDatasetId")
    if not dataset_id:
        logger.error("Apify run missing dataset ID: %s", run)
        raise HTTPException(status_code=502, detail="Apify run did not return a dataset ID")

    try:
        items = list(client.dataset(dataset_id).iterate_items())
    except Exception as exc:
        logger.error("Apify dataset fetch failed for %s: %s", domain, exc)
        raise HTTPException(status_code=502, detail="Failed to fetch Trustpilot dataset from Apify")

    if not isinstance(items, list):
        logger.error("Apify dataset response is not a list: %s", type(items))
        raise HTTPException(status_code=502, detail="Apify dataset returned invalid format")

    normalized = [normalize_apify_review(item) for item in items if isinstance(item, dict)]
    logger.info(
        "Apify Trustpilot actor completed: actor_id=%s domain=%s raw_items=%s normalized_items=%s",
        actor_id,
        domain,
        len(items),
        len(normalized),
    )
    return normalized[:bounded_max_reviews]
