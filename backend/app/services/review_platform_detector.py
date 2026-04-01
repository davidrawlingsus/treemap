"""
Review platform detector.

Fetches a company's website HTML and checks for known review widget
signatures to identify which platforms they use (Trustpilot, Reviews.io,
Yotpo) and extract the necessary API keys/identifiers.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


@dataclass
class DetectedPlatform:
    platform: str       # "trustpilot" | "reviews_io" | "yotpo"
    identifier: str     # domain (TP) | store ID (R.io) | app_key (Yotpo)
    confidence: str = "medium"  # "high" | "medium" | "low"


def detect_review_platforms(
    company_url: str,
    company_domain: str,
) -> List[DetectedPlatform]:
    """Fetch website HTML and detect review platforms.

    Returns a list of detected platforms sorted by confidence (high first).
    Always includes Trustpilot as a fallback (Apify works by domain alone).
    """
    detected: List[DetectedPlatform] = []
    html = _fetch_page_html(company_url)

    if html:
        # Check Yotpo
        yotpo_key = _detect_yotpo(html)
        if yotpo_key:
            detected.append(DetectedPlatform("yotpo", yotpo_key, "high"))
            logger.info("[detect] Found Yotpo app_key: %s", yotpo_key[:12] + "...")

        # Check Reviews.io
        reviewsio_store = _detect_reviews_io(html)
        if reviewsio_store:
            detected.append(DetectedPlatform("reviews_io", reviewsio_store, "high"))
            logger.info("[detect] Found Reviews.io store: %s", reviewsio_store)

        # Check Trustpilot widget presence
        if _detect_trustpilot_widget(html):
            detected.append(DetectedPlatform("trustpilot", company_domain, "high"))
            logger.info("[detect] Found Trustpilot widget on page")

    # Always include Trustpilot as fallback (works by domain without widget detection)
    if not any(p.platform == "trustpilot" for p in detected):
        detected.append(DetectedPlatform("trustpilot", company_domain, "low"))

    logger.info(
        "[detect] Detected %d platform(s) for %s: %s",
        len(detected), company_domain,
        ", ".join(f"{p.platform}({p.confidence})" for p in detected),
    )
    return sorted(detected, key=lambda p: {"high": 0, "medium": 1, "low": 2}.get(p.confidence, 3))


def _fetch_page_html(url: str) -> Optional[str]:
    """Fetch raw HTML from a URL. Returns None on failure."""
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=15,
            allow_redirects=True,
        )
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        logger.warning("[detect] Failed to fetch %s: %s", url, e)
        return None


# ---------------------------------------------------------------------------
# Yotpo detection
# ---------------------------------------------------------------------------

_YOTPO_SIGNATURES = [
    "staticw2.yotpo.com",
    "cdn-widgetsrepository.yotpo.com",
    "yotpo.com/widget",
    "yotpo-widget",
    "yotpoWidgetsContainer",
    "class=\"yotpo",
]

# Patterns to extract app_key
_YOTPO_KEY_PATTERNS = [
    # data-appkey="..." or data-app-key="..."
    re.compile(r'data-app-?key\s*=\s*["\']([a-zA-Z0-9]+)["\']', re.IGNORECASE),
    # CDN loader URL: cdn-widgetsrepository.yotpo.com/v1/loader/APP_KEY
    re.compile(r'yotpo\.com/v1/loader/([a-zA-Z0-9]+)', re.IGNORECASE),
    # yotpo.com/widget/APP_KEY or yotpo.com/...?appkey=APP_KEY
    re.compile(r'yotpo\.com/[^"\']*?(?:widget/|appkey=)([a-zA-Z0-9]+)', re.IGNORECASE),
    # JS variable: appKey: "...", appkey: "...", yotpoAppKey = "..."
    re.compile(r'(?:app_?key|yotpoAppKey)\s*[:=]\s*["\']([a-zA-Z0-9]+)["\']', re.IGNORECASE),
]


def _detect_yotpo(html: str) -> Optional[str]:
    """Check for Yotpo presence and extract app_key."""
    html_lower = html.lower()
    if not any(sig.lower() in html_lower for sig in _YOTPO_SIGNATURES):
        return None

    for pattern in _YOTPO_KEY_PATTERNS:
        match = pattern.search(html)
        if match:
            key = match.group(1)
            if len(key) >= 8:  # app_keys are typically 20+ chars
                return key

    logger.info("[detect] Yotpo signatures found but could not extract app_key")
    return None


# ---------------------------------------------------------------------------
# Reviews.io detection
# ---------------------------------------------------------------------------

_REVIEWSIO_SIGNATURES = [
    "widget.reviews.io",
    "api.reviews.io",
    "richsnippet-reviews",
    "reviewsio",
]

_REVIEWSIO_STORE_PATTERNS = [
    # store=STORE_ID in script src or widget config
    re.compile(r'reviews\.io/[^"\']*?store=([a-zA-Z0-9._-]+)', re.IGNORECASE),
    # store: 'company-name' or store: "company-name" in JS config
    re.compile(r"store\s*:\s*['\"]([a-zA-Z0-9._-]+)['\"]", re.IGNORECASE),
    # data-store="..." attribute
    re.compile(r'data-store\s*=\s*["\']([a-zA-Z0-9._-]+)["\']', re.IGNORECASE),
]


def _detect_reviews_io(html: str) -> Optional[str]:
    """Check for Reviews.io presence and extract store ID."""
    html_lower = html.lower()
    if not any(sig.lower() in html_lower for sig in _REVIEWSIO_SIGNATURES):
        return None

    for pattern in _REVIEWSIO_STORE_PATTERNS:
        match = pattern.search(html)
        if match:
            store_id = match.group(1)
            if len(store_id) >= 2:
                return store_id

    logger.info("[detect] Reviews.io signatures found but could not extract store ID")
    return None


# ---------------------------------------------------------------------------
# Trustpilot detection (widget presence only — Apify works by domain)
# ---------------------------------------------------------------------------

_TRUSTPILOT_SIGNATURES = [
    "trustpilot.com",
    "tp-widget",
    "trustpilot-widget",
    "data-businessunit-id",
    "trustbox",
]


def _detect_trustpilot_widget(html: str) -> bool:
    """Check if Trustpilot widgets are present on the page."""
    html_lower = html.lower()
    return any(sig.lower() in html_lower for sig in _TRUSTPILOT_SIGNATURES)
