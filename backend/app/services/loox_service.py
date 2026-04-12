"""
Loox review scraper.

Fetches reviews from the Loox widget HTML endpoint and parses them
into the standard review format used by the VoC pipeline.

Note: Loox returns HTML, not JSON. We parse with BeautifulSoup.
The widget_id and hash are extracted during platform detection from
the on-page iframe src: loox.io/widget/{WIDGET_ID}/reviews?h={HASH}
"""

import logging
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

WIDGET_BASE = "https://loox.io/widget"


def fetch_loox_reviews(
    widget_id: str,
    hash_param: str,
    max_reviews: int = 200,
    per_page: int = 10,
) -> List[Dict[str, Any]]:
    """Fetch reviews from Loox widget HTML endpoint.

    Returns normalized review dicts matching the standard format.
    Returns empty list on any error (pipeline continues with other sources).
    """
    if not widget_id:
        logger.warning("[loox] Missing widget_id, skipping")
        return []

    all_reviews: List[Dict[str, Any]] = []
    page = 1
    url = f"{WIDGET_BASE}/{widget_id}/reviews"

    logger.info("[loox] Fetching reviews for widget=%s hash=%s (max=%d)", widget_id, hash_param or "none", max_reviews)

    while len(all_reviews) < max_reviews:
        try:
            params = {"limit": per_page, "page": page}
            if hash_param:
                params["h"] = hash_param
            resp = requests.get(
                url,
                params=params,
                headers={"User-Agent": USER_AGENT},
                timeout=15,
            )
            resp.raise_for_status()
            html = resp.text
        except Exception as e:
            logger.warning("[loox] Request failed (page %d): %s", page, e)
            break

        reviews = _parse_reviews_html(html)
        if not reviews:
            break

        for item in reviews:
            normalized = _normalize_review(item, page, len(all_reviews))
            if normalized:
                all_reviews.append(normalized)

        logger.info("[loox] Page %d: %d reviews (total: %d)", page, len(reviews), len(all_reviews))

        if len(reviews) < per_page or len(all_reviews) >= max_reviews:
            break

        page += 1

    logger.info("[loox] Fetched %d reviews for widget=%s", len(all_reviews), widget_id)
    return all_reviews[:max_reviews]


def _parse_reviews_html(html: str) -> List[Dict[str, Any]]:
    """Parse review data from Loox widget HTML response.

    Loox structure (as of 2026):
    - Review card: .grid-item-wrap
    - Reviewer name: .title or .feed-item-title-wrapper
    - Review text: .main-text
    - Product name: .name (confusingly named)
    - Rating: aria-label on .stars ul ("Rating icons: N / 5 star review")
              or count of data-lx-fill="full" SVGs
    - Verified: .loox-verified-badge present
    - Review ID: data-testid="review-{ID}-stars" on .stars div
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        logger.error("[loox] beautifulsoup4 is not installed")
        return []

    soup = BeautifulSoup(html, "html.parser")
    reviews = []

    cards = soup.select(".grid-item-wrap")
    if not cards:
        logger.warning("[loox] No .grid-item-wrap cards found in HTML (%d bytes)", len(html))
        return []

    for card in cards:
        # Review text
        text_el = card.select_one(".main-text")
        text = text_el.get_text(strip=True) if text_el else ""
        if not text:
            continue

        # Reviewer name (in .title, NOT .name which is the product)
        reviewer_el = card.select_one(".title, .feed-item-title-wrapper")
        reviewer = reviewer_el.get_text(strip=True) if reviewer_el else "Anonymous"

        # Product name
        product_el = card.select_one(".name")
        product = product_el.get_text(strip=True) if product_el else ""

        # Rating from aria-label or filled star count
        rating = None
        stars_el = card.select_one(".stars")
        if stars_el:
            # Try aria-label first: "Rating icons:  5 / 5 star review"
            ul = stars_el.select_one("ul[aria-label]")
            if ul:
                import re
                m = re.search(r"(\d+)\s*/\s*5", ul.get("aria-label", ""))
                if m:
                    rating = int(m.group(1))
            # Fallback: count filled stars
            if rating is None:
                filled = stars_el.select('[data-lx-fill="full"]')
                if filled:
                    rating = len(filled)

        # Verified badge
        is_verified = card.select_one(".loox-verified-badge") is not None

        # Review ID from data-testid
        review_id = ""
        if stars_el:
            testid = stars_el.get("data-testid", "")
            if testid.startswith("review-") and testid.endswith("-stars"):
                review_id = testid[7:-6]  # strip "review-" and "-stars"

        reviews.append({
            "text": text,
            "reviewer": reviewer,
            "product": product,
            "rating": rating,
            "verified": is_verified,
            "review_id": review_id,
        })

    logger.info("[loox] Parsed %d reviews from HTML", len(reviews))
    return reviews


def _normalize_review(
    item: Dict[str, Any],
    page: int,
    index: int,
) -> Dict[str, Any]:
    """Normalize a parsed Loox review to the standard format."""
    text = item.get("text", "").strip()
    if not text:
        return {}

    review_id = item.get("review_id") or f"loox_{page}_{index}"

    return {
        "review_id": str(review_id),
        "rating": item.get("rating"),
        "title": "",
        "text": text,
        "published_at": "",
        "language": "en",
        "country": "",
        "review_url": "",
        "reviewer_name": item.get("reviewer", "Anonymous"),
        "source": "loox",
        "raw_item": item,
    }
