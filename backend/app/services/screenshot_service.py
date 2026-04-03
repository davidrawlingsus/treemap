"""
Visualization screenshot service.

Takes a screenshot of a client's visualization using headless Playwright,
uploads to Vercel Blob, and stores the URL on the client record.
"""

import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

SCREENSHOT_WAIT_MS = 8000  # wait for treemap to render
VIEWPORT = {"width": 1280, "height": 900}


def capture_visualization_screenshot(
    *,
    frontend_base_url: str,
    token: str,
    email: str,
    client_id: str,
    company_name: str,
) -> Optional[str]:
    """Capture a screenshot of the client visualization.

    Args:
        frontend_base_url: e.g. "https://vizualizd.mapthegap.ai"
        token: raw magic link token (not hashed)
        email: user email for magic link auth
        client_id: UUID string of the client
        company_name: for naming the blob file

    Returns:
        Vercel Blob URL of the screenshot, or None on failure.
    """
    from urllib.parse import quote
    import re

    url = f"{frontend_base_url}?token={quote(token)}&email={quote(email)}&client_uuid={client_id}"
    logger.info("[screenshot] Capturing visualization for %s", company_name)

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport=VIEWPORT)

            # Navigate with magic link — auth happens automatically
            page.goto(url, wait_until="networkidle", timeout=30000)

            # Wait for the treemap to render
            page.wait_for_timeout(SCREENSHOT_WAIT_MS)

            # Try to wait for the treemap SVG to appear
            try:
                page.wait_for_selector("svg", timeout=10000)
            except Exception:
                logger.warning("[screenshot] SVG not found, taking screenshot anyway")

            # Take screenshot
            screenshot_bytes = page.screenshot(full_page=False)
            browser.close()

        logger.info("[screenshot] Captured %d bytes for %s", len(screenshot_bytes), company_name)

        # Upload to Vercel Blob
        blob_url = _upload_to_blob(screenshot_bytes, company_name)
        return blob_url

    except ImportError:
        logger.error("[screenshot] Playwright not installed")
        return None
    except Exception as e:
        logger.error("[screenshot] Failed for %s: %s", company_name, e)
        return None


def _upload_to_blob(image_bytes: bytes, company_name: str) -> Optional[str]:
    """Upload screenshot PNG to Vercel Blob."""
    import re

    try:
        import vercel_blob
        slug = re.sub(r"[^a-z0-9]+", "-", company_name.lower()).strip("-")
        blob_path = f"screenshots/{slug}-{int(time.time())}.png"
        blob = vercel_blob.put(
            blob_path,
            image_bytes,
            {"access": "public", "contentType": "image/png"},
        )
        blob_url = blob.get("url") if isinstance(blob, dict) else getattr(blob, "url", None)

        if blob_url:
            logger.info("[screenshot] Uploaded to blob: %s", blob_url)
            return blob_url
        logger.warning("[screenshot] Blob upload returned no URL: %s", blob)
        return None

    except ImportError:
        logger.warning("[screenshot] vercel_blob not installed")
        return None
    except Exception as e:
        logger.warning("[screenshot] Blob upload failed: %s", e)
        return None
