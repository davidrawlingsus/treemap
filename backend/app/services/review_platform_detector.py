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
    platform: str       # "trustpilot" | "reviews_io" | "yotpo" | "google_reviews"
    identifier: str     # domain (TP) | store ID (R.io) | app_key (Yotpo) | domain (Google)
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

        # Check Google Reviews widget presence (only add if detected, not as fallback)
        if _detect_google_reviews_widget(html):
            detected.append(DetectedPlatform("google_reviews", company_domain, "high"))
            logger.info("[detect] Found Google Reviews widget on page")

        # Check Judge.me
        judgeme_id = _detect_judge_me(html)
        if judgeme_id:
            detected.append(DetectedPlatform("judge_me", judgeme_id, "high"))
            logger.info("[detect] Found Judge.me: %s", judgeme_id[:20])

        # Check Stamped.io
        stamped_id = _detect_stamped(html)
        if stamped_id:
            detected.append(DetectedPlatform("stamped", stamped_id, "high"))
            logger.info("[detect] Found Stamped.io: %s", stamped_id[:20])

        # Check Loox
        loox_id = _detect_loox(html)
        if loox_id:
            detected.append(DetectedPlatform("loox", loox_id, "high"))
            logger.info("[detect] Found Loox: %s", loox_id[:30])

        # Check Okendo
        okendo_id = _detect_okendo(html)
        if okendo_id:
            detected.append(DetectedPlatform("okendo", okendo_id, "high"))
            logger.info("[detect] Found Okendo: %s", okendo_id[:20])

    # If HTML fetch failed (Cloudflare/WAF block), probe free review APIs directly
    if not html:
        logger.info("[detect] HTML fetch failed for %s — running blind API probes", company_domain)
        probed = _probe_review_apis(company_domain)
        detected.extend(probed)

    # Always include Trustpilot as fallback (works by domain without widget detection)
    # Google Reviews NOT included as fallback — too prone to finding the wrong business
    # for D2C e-commerce brands with ambiguous names
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
    "YOTPO_KEY",
    "yotpoToken",
    "useYotpoRefresh",
]

# Patterns to extract app_key
_YOTPO_KEY_PATTERNS = [
    # data-appkey="..." or data-app-key="..."
    re.compile(r'data-app-?key\s*=\s*["\']([a-zA-Z0-9]+)["\']', re.IGNORECASE),
    # CDN loader URL: cdn-widgetsrepository.yotpo.com/v1/loader/APP_KEY
    re.compile(r'yotpo\.com/v1/loader/([a-zA-Z0-9]+)', re.IGNORECASE),
    # yotpo.com/widget/APP_KEY or yotpo.com/...?appkey=APP_KEY
    re.compile(r'yotpo\.com/[^"\']*?(?:widget/|appkey=)([a-zA-Z0-9]+)', re.IGNORECASE),
    # JS variable: appKey: "...", appkey: "...", yotpoAppKey = "...", YOTPO_KEY: "..."
    re.compile(r'(?:app_?key|yotpoAppKey|YOTPO_KEY|yotpoToken)\s*["\'\\]*\s*[:=]\s*["\'\\]*([a-zA-Z0-9]{8,})', re.IGNORECASE),
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


# ---------------------------------------------------------------------------
# Google Reviews detection (widget presence only)
# ---------------------------------------------------------------------------

_GOOGLE_REVIEWS_SIGNATURES = [
    "google.com/maps",
    "maps.googleapis.com",
    "google-reviews",
    "googlereviews",
    "data-google-place",
    "elfsight.com/google-review",
    "widget.trustindex.io",
    "google_review",
]


def _detect_google_reviews_widget(html: str) -> bool:
    """Check if Google Reviews widgets are present on the page."""
    html_lower = html.lower()
    return any(sig.lower() in html_lower for sig in _GOOGLE_REVIEWS_SIGNATURES)


# ---------------------------------------------------------------------------
# Judge.me detection
# ---------------------------------------------------------------------------

_JUDGEME_SIGNATURES = [
    "judge.me",
    "judgeme",
    "jdgm-widget",
    "jdgm-rev",
    "jdgm-badge",
    "jdgm-carousel",
    "data-jdgm",
]

_JUDGEME_SHOP_PATTERNS = [
    # Shopify.shop = "store-name.myshopify.com" (most reliable)
    re.compile(r'Shopify\.shop\s*=\s*["\']([a-zA-Z0-9._-]+\.myshopify\.com)["\']', re.IGNORECASE),
    # data-shop-domain="store-name.myshopify.com"
    re.compile(r'data-shop-domain\s*=\s*["\']([a-zA-Z0-9._-]+\.myshopify\.com)["\']', re.IGNORECASE),
    # data-shop-domain="store-name" (without .myshopify.com)
    re.compile(r'data-shop-domain\s*=\s*["\']([a-zA-Z0-9._-]+)["\']', re.IGNORECASE),
    # judge.me/reviews/STORE.myshopify.com (specific shop review page)
    re.compile(r'judge\.me/reviews/([a-zA-Z0-9._-]+\.myshopify\.com)', re.IGNORECASE),
    # Any .myshopify.com reference in the page (broad fallback)
    re.compile(r'["\']([a-zA-Z0-9-]+\.myshopify\.com)["\']', re.IGNORECASE),
]

# False positives to filter out from judge.me/reviews/ matches
_JUDGEME_SHOP_BLACKLIST = {"stores", "login", "terms", "privacy", "api", "widget", "badges"}


def _detect_judge_me(html: str) -> Optional[str]:
    """Check for Judge.me presence and extract shop identifier."""
    html_lower = html.lower()
    if not any(sig.lower() in html_lower for sig in _JUDGEME_SIGNATURES):
        return None

    for pattern in _JUDGEME_SHOP_PATTERNS:
        match = pattern.search(html)
        if match:
            identifier = match.group(1)
            # Filter out generic paths that aren't shop domains
            if identifier.lower() in _JUDGEME_SHOP_BLACKLIST:
                continue
            logger.info("[detect] Judge.me shop identifier: %s", identifier)
            return identifier

    # Detected but can't extract identifier
    logger.info("[detect] Judge.me signatures found but could not extract shop ID")
    return "detected"


# ---------------------------------------------------------------------------
# Stamped.io detection
# ---------------------------------------------------------------------------

_STAMPED_SIGNATURES = [
    "stamped.io",
    "stampedio",
    "stamped-badge",
    "stamped-reviews",
    "stamped-ugc",
    "data-store-hash",
    "stamped-main-widget",
]

_STAMPED_KEY_PATTERNS = [
    re.compile(r'data-api-key\s*=\s*["\']([a-zA-Z0-9]+)["\']', re.IGNORECASE),
    re.compile(r'data-store-hash\s*=\s*["\']([a-zA-Z0-9]+)["\']', re.IGNORECASE),
    re.compile(r'stamped\.io/[^"\']*?apiKey=([a-zA-Z0-9]+)', re.IGNORECASE),
]


def _detect_stamped(html: str) -> Optional[str]:
    """Check for Stamped.io presence and extract API key / store hash."""
    html_lower = html.lower()
    if not any(sig.lower() in html_lower for sig in _STAMPED_SIGNATURES):
        return None

    for pattern in _STAMPED_KEY_PATTERNS:
        match = pattern.search(html)
        if match:
            return match.group(1)

    logger.info("[detect] Stamped.io signatures found but could not extract key")
    return "detected"


# ---------------------------------------------------------------------------
# Loox detection
# ---------------------------------------------------------------------------

_LOOX_SIGNATURES = [
    "loox.io",
    "loox-widget",
    "loox-rating",
    "loox-review",
    "loox.app",
]

_LOOX_ID_PATTERNS = [
    # iframe src: loox.io/widget/{WIDGET_ID}/reviews?h={HASH}
    re.compile(r'loox\.io/widget/([a-zA-Z0-9]+)/reviews\?[^"\']*h=([a-zA-Z0-9]+)', re.IGNORECASE),
    # script/iframe: loox.io/widget/{WIDGET_ID}/ (any path after widget ID)
    re.compile(r'loox\.io/widget/([a-zA-Z0-9]{6,})', re.IGNORECASE),
    # loox.app/widget/{WIDGET_ID}
    re.compile(r'loox\.app/widget/([a-zA-Z0-9]{6,})', re.IGNORECASE),
    # data attribute: data-loox-id="..." or data-widget-id="..."
    re.compile(r'data-(?:loox-id|widget-id)\s*=\s*["\']([a-zA-Z0-9]{6,})["\']', re.IGNORECASE),
]


def _detect_loox(html: str) -> Optional[str]:
    """Check for Loox presence and extract widget ID + hash.

    Returns 'widget_id|hash' if both found, 'widget_id' if only ID found,
    or None if no Loox signatures detected.
    """
    html_lower = html.lower()
    if not any(sig.lower() in html_lower for sig in _LOOX_SIGNATURES):
        return None

    # Unescape JSON-escaped forward slashes (common in Shopify inline scripts)
    html_unescaped = html.replace("\\/", "/")

    # Try to extract widget ID and hash
    for pattern in _LOOX_ID_PATTERNS:
        match = pattern.search(html_unescaped)
        if match:
            widget_id = match.group(1)
            hash_param = match.group(2) if match.lastindex >= 2 else ""
            if hash_param:
                return f"{widget_id}|{hash_param}"
            return widget_id

    # Loox detected but can't extract identifiers
    return "detected"


# ---------------------------------------------------------------------------
# Okendo detection
# ---------------------------------------------------------------------------

_OKENDO_SIGNATURES = [
    "okendo.io",
    "oke-widget",
    "oke-reviews",
    "okendo-reviews",
    "data-oke-",
    "okeReviews",
    "d3hw6dc1ow8pp2.cloudfront.net",  # Okendo CDN
]

# UUID pattern for subscriber IDs (xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)
_UUID_PATTERN = r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}'

_OKENDO_ID_PATTERNS = [
    # data-oke-reviews-subscriber-id="UUID"
    re.compile(r'data-oke-reviews-subscriber-id\s*=\s*["\'](' + _UUID_PATTERN + r')["\']', re.IGNORECASE),
    # subscriberId=UUID in URL params
    re.compile(r'okendo\.io/[^"\']*?subscriberId=(' + _UUID_PATTERN + r')', re.IGNORECASE),
    # CDN URL: cdn-static.okendo.io/widget/UUID/ or d3hw6dc1ow8pp2.cloudfront.net/reviews-widget-plus/UUID/
    re.compile(r'(?:cdn-static\.okendo\.io|d3hw6dc1ow8pp2\.cloudfront\.net)/[^"\']*?(' + _UUID_PATTERN + r')', re.IGNORECASE),
    # JSON config: "subscriberId":"UUID" or subscriberId: "UUID"
    re.compile(r'["\']?subscriberId["\']?\s*[:=]\s*["\'](' + _UUID_PATTERN + r')["\']', re.IGNORECASE),
    # data-oke-subscriber-id (alternate attribute)
    re.compile(r'data-oke-subscriber-id\s*=\s*["\'](' + _UUID_PATTERN + r')["\']', re.IGNORECASE),
    # Shopify app embed: any UUID near "okendo" context (broad fallback)
    re.compile(r'okendo[^"\']{0,100}(' + _UUID_PATTERN + r')', re.IGNORECASE),
    re.compile(r'(' + _UUID_PATTERN + r')[^"\']{0,100}okendo', re.IGNORECASE),
]


def _detect_okendo(html: str) -> Optional[str]:
    """Check for Okendo presence and extract subscriber ID."""
    html_lower = html.lower()
    if not any(sig.lower() in html_lower for sig in _OKENDO_SIGNATURES):
        return None

    for pattern in _OKENDO_ID_PATTERNS:
        match = pattern.search(html)
        if match:
            subscriber_id = match.group(1)
            logger.info("[detect] Okendo subscriber ID extracted: %s", subscriber_id)
            return subscriber_id

    logger.info("[detect] Okendo signatures found but could not extract subscriber ID")
    return "detected"


# ---------------------------------------------------------------------------
# Blind API probes (when HTML fetch is blocked by Cloudflare/WAF)
# ---------------------------------------------------------------------------

def _probe_review_apis(company_domain: str) -> List[DetectedPlatform]:
    """Probe free review APIs directly when we can't access the website HTML.

    Tries Yotpo, Reviews.io, and Okendo discovery approaches to find
    which platform the site uses without needing to render the page.
    """
    probed: List[DetectedPlatform] = []

    # Probe Reviews.io — try the domain as store ID
    try:
        resp = requests.get(
            "https://api.reviews.io/merchant/reviews",
            params={"store": company_domain, "page": 1, "per_page": 1},
            headers={"User-Agent": USER_AGENT},
            timeout=8,
        )
        if resp.ok:
            data = resp.json()
            reviews = data.get("reviews", [])
            if reviews:
                probed.append(DetectedPlatform("reviews_io", company_domain, "medium"))
                logger.info("[probe] Reviews.io has reviews for %s", company_domain)
    except Exception:
        pass

    # Probe Yotpo — try fetching site reviews with domain as app_key
    # (unlikely to work without the real key, but worth trying)

    # Probe Judge.me — try the myshopify.com domain pattern
    shopify_domain = company_domain.replace(".com", "").replace(".", "") + ".myshopify.com"
    try:
        resp = requests.get(
            f"https://judge.me/api/v1/reviews",
            params={"shop_domain": shopify_domain, "per_page": 1},
            headers={"User-Agent": USER_AGENT},
            timeout=8,
        )
        if resp.ok:
            data = resp.json()
            reviews = data.get("reviews", [])
            if reviews:
                probed.append(DetectedPlatform("judge_me", shopify_domain, "medium"))
                logger.info("[probe] Judge.me has reviews for %s", shopify_domain)
    except Exception:
        pass

    if probed:
        logger.info("[probe] Found %d platform(s) via blind probes for %s", len(probed), company_domain)
    else:
        logger.info("[probe] No platforms found via blind probes for %s", company_domain)

    return probed
