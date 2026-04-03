"""
Google Reviews scraper.

Fetches Google Maps reviews for a business by:
1. Finding the Google Place via Places Text Search (domain/name → place_id)
2. Scraping reviews via Apify actor (place_id → reviews)
"""

import logging
import re
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

PLACES_TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"


def fetch_google_reviews_by_domain(
    api_key: str,
    company_domain: str,
    company_name: str | None = None,
    max_reviews: int = 200,
    apify_api_token: str | None = None,
    apify_google_actor_id: str | None = None,
    apify_timeout_seconds: int = 300,
) -> List[Dict[str, Any]]:
    """Fetch Google Maps reviews for a company starting from its domain.

    Steps:
      1. Google Places Text Search with the company domain/name to find the place
      2. Apify actor to scrape all reviews for that place

    Returns normalized review dicts matching the standard format.
    Returns empty list on any API error (pipeline continues with other sources).
    """
    search_name = company_name or _domain_to_name(company_domain)

    # Step 1: Find the Google Place
    place_id = _find_place_id(api_key, search_name, company_domain)
    if not place_id:
        logger.warning("[google-reviews] Could not find Google Place for %s", company_domain)
        return []

    logger.info("[google-reviews] Found place_id for %s: %s", company_domain, place_id)

    # Step 2: Scrape reviews via Apify
    if not apify_api_token or not apify_google_actor_id:
        logger.warning("[google-reviews] Apify not configured for Google Reviews — skipping")
        return []

    reviews = _fetch_reviews_via_apify(
        apify_api_token=apify_api_token,
        actor_id=apify_google_actor_id,
        place_id=place_id,
        max_reviews=max_reviews,
        timeout_seconds=apify_timeout_seconds,
    )
    logger.info("[google-reviews] Fetched %d reviews for %s", len(reviews), company_domain)
    return reviews


# ---------------------------------------------------------------------------
# Step 1: Find place_id via Google Places Text Search
# ---------------------------------------------------------------------------


def _domain_to_name(domain: str) -> str:
    """Convert a domain like 'acme-corp.com' to 'Acme Corp'."""
    base = domain.split(".")[0]
    words = re.split(r"[-_]+", base)
    return " ".join(w.capitalize() for w in words if w)


def _find_place_id(
    api_key: str,
    company_name: str,
    company_domain: str,
) -> Optional[str]:
    """Use Google Places Text Search (New) to find a place_id for a business.

    Searches with the company name first; falls back to domain if no results.
    """
    for query in [company_name, company_domain]:
        try:
            resp = requests.post(
                PLACES_TEXT_SEARCH_URL,
                json={"textQuery": query},
                headers={
                    "X-Goog-Api-Key": api_key,
                    "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.websiteUri",
                    "Content-Type": "application/json",
                },
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.warning("[google-reviews] Places Text Search failed for %r: %s", query, e)
            continue

        places = data.get("places", [])
        if not places:
            logger.info("[google-reviews] No places found for query %r", query)
            continue

        # If we have multiple results, prefer one whose website matches the domain
        for place in places:
            website = (place.get("websiteUri") or "").lower()
            if company_domain.lower() in website:
                logger.info(
                    "[google-reviews] Matched place by website: %s (%s)",
                    place.get("displayName", {}).get("text", ""),
                    place.get("formattedAddress", ""),
                )
                return place.get("id")

        # Otherwise return the top result
        top = places[0]
        logger.info(
            "[google-reviews] Using top result: %s (%s)",
            top.get("displayName", {}).get("text", ""),
            top.get("formattedAddress", ""),
        )
        return top.get("id")

    return None


# ---------------------------------------------------------------------------
# Step 2: Scrape reviews via Apify actor
# ---------------------------------------------------------------------------


def _build_apify_actor_input(place_id: str, max_reviews: int) -> Dict[str, Any]:
    """Build the input for the compass/Google-Maps-Reviews-Scraper Apify actor."""
    return {
        "startUrls": [],
        "placeIds": [place_id],
        "maxReviews": max_reviews,
        "reviewsSort": "newest",
        "language": "en",
        "reviewsOrigin": "all",
        "personalData": True,
    }


def _fetch_reviews_via_apify(
    apify_api_token: str,
    actor_id: str,
    place_id: str,
    max_reviews: int,
    timeout_seconds: int,
) -> List[Dict[str, Any]]:
    """Run an Apify actor to scrape Google Maps reviews for a place."""
    try:
        from apify_client import ApifyClient
    except ImportError:
        logger.error("[google-reviews] apify-client package is not installed")
        return []

    actor_input = _build_apify_actor_input(place_id, max_reviews)
    logger.info(
        "[google-reviews] Running Apify actor: actor_id=%s place_id=%s max_reviews=%s",
        actor_id, place_id, max_reviews,
    )

    client = ApifyClient(apify_api_token)
    timeout = max(timeout_seconds, max_reviews * 2 + 60)

    try:
        run = client.actor(actor_id).call(
            run_input=actor_input,
            wait_secs=timeout,
        )
    except Exception as exc:
        logger.error("[google-reviews] Apify actor run failed for %s: %s", place_id, exc)
        return []

    dataset_id = (run or {}).get("defaultDatasetId")
    if not dataset_id:
        logger.error("[google-reviews] Apify run missing dataset ID: %s", run)
        return []

    try:
        items = list(client.dataset(dataset_id).iterate_items())
    except Exception as exc:
        logger.error("[google-reviews] Apify dataset fetch failed: %s", exc)
        return []

    if not isinstance(items, list):
        logger.error("[google-reviews] Apify dataset response is not a list: %s", type(items))
        return []

    normalized = [_normalize_apify_review(item) for item in items if isinstance(item, dict)]
    normalized = [r for r in normalized if r]  # filter empty
    logger.info(
        "[google-reviews] Apify actor completed: raw_items=%s normalized=%s",
        len(items), len(normalized),
    )
    return normalized


def _normalize_apify_review(item: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize an Apify Google Maps review to the standard format.

    Handles common output schemas from Google Maps review actors.
    """
    # Primary: text field; fallback: translated version
    text = (item.get("text") or item.get("textTranslated") or "").strip()
    if not text:
        return {}

    return {
        "review_id": str(item.get("reviewId") or item.get("reviewerId") or ""),
        "rating": item.get("stars") or item.get("rating"),
        "title": "",  # Google reviews don't have titles
        "text": text,
        "published_at": item.get("publishedAtDate") or item.get("publishAt") or "",
        "language": item.get("originalLanguage") or item.get("language") or "en",
        "country": item.get("countryCode") or "",
        "review_url": item.get("reviewUrl") or "",
        "reviewer_name": item.get("name") or "Anonymous",
        "source": "google_reviews",
        "raw_item": item,
    }
