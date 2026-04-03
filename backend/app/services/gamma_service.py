"""
Gamma deck generation service.

Generates a presentation deck via the Gamma API from markdown content.
Uses the v1.0 Generate API (async: create job → poll until complete).
Returns both a shareable URL and a PDF export URL.
"""

import logging
import time
from dataclasses import dataclass
from typing import Optional

import requests

logger = logging.getLogger(__name__)

GAMMA_API_BASE = "https://public-api.gamma.app/v1.0"
POLL_INTERVAL = 5  # seconds
MAX_POLLS = 120  # 10 minutes max wait
MAX_RETRIES = 2  # retry on 429 rate limit


@dataclass
class GammaDeckResult:
    gamma_url: Optional[str] = None
    pdf_url: Optional[str] = None  # Permanently hosted PDF on Vercel Blob


def generate_deck(
    api_key: Optional[str],
    title: str,
    markdown_content: str,
) -> Optional[GammaDeckResult]:
    """Generate a Gamma presentation from markdown content.

    Returns a GammaDeckResult with share URL and PDF export URL, or None on failure.
    """
    if not api_key:
        logger.info("[gamma] Not configured — skipping deck generation")
        return None

    if not markdown_content.strip():
        logger.info("[gamma] Empty markdown content — skipping")
        return None

    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json",
    }

    body = {
        "inputText": f"# {title}\n\n{markdown_content}",
        "textMode": "preserve",
        "format": "presentation",
        "numCards": 20,
        "themeId": "zlj1eyfj4b520tb",  # Map_The_Gap theme
        "exportAs": "pdf",
        "textOptions": {
            "tone": "professional",
            "amount": "detailed",
        },
        "imageOptions": {
            "source": "aiGenerated",
            "model": "ideogram-v3",
            "stylePreset": "illustration",
        },
        "sharingOptions": {
            "externalAccess": "view",
        },
    }

    logger.info("[gamma] Starting generation for '%s' (%d chars)", title, len(markdown_content))

    # Step 1: Start generation (with retry on 429)
    generation_id = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = requests.post(
                f"{GAMMA_API_BASE}/generations",
                headers=headers,
                json=body,
                timeout=30,
            )

            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 30))
                logger.warning("[gamma] Rate limited (429). Retrying in %ds (attempt %d/%d)",
                               retry_after, attempt + 1, MAX_RETRIES + 1)
                time.sleep(retry_after)
                continue

            if resp.status_code == 403:
                logger.error("[gamma] Access denied (403): %s", resp.text[:500])
                return None

            if not resp.ok:
                logger.error("[gamma] API error %d: %s", resp.status_code, resp.text[:500])
                return None

            data = resp.json()

            # Log warnings from the response
            warnings = data.get("warnings", [])
            if warnings:
                for w in warnings:
                    logger.warning("[gamma] Warning: %s", w)

            generation_id = data.get("id") or data.get("generationId")
            if not generation_id:
                logger.error("[gamma] No generation ID in response: %s", str(data)[:500])
                return None

            logger.info("[gamma] Generation started: %s", generation_id)
            break

        except Exception as e:
            logger.error("[gamma] Failed to start generation (attempt %d/%d): %s",
                         attempt + 1, MAX_RETRIES + 1, e)
            if attempt < MAX_RETRIES:
                time.sleep(5)

    if not generation_id:
        return None

    # Step 2: Poll until complete
    for i in range(MAX_POLLS):
        time.sleep(POLL_INTERVAL)
        try:
            poll_resp = requests.get(
                f"{GAMMA_API_BASE}/generations/{generation_id}",
                headers=headers,
                timeout=15,
            )

            if poll_resp.status_code == 429:
                retry_after = int(poll_resp.headers.get("Retry-After", 10))
                logger.warning("[gamma] Poll rate limited. Waiting %ds", retry_after)
                time.sleep(retry_after)
                continue

            if not poll_resp.ok:
                logger.warning("[gamma] Poll error %d: %s", poll_resp.status_code, poll_resp.text[:300])
                continue

            poll_data = poll_resp.json()
            status = poll_data.get("status", "")

            if status == "completed":
                gamma_url = poll_data.get("gammaUrl")
                export_url = poll_data.get("exportUrl")
                logger.info("[gamma] Deck created: %s (export: %s)", gamma_url, export_url)

                # Download PDF and upload to Vercel Blob for permanent hosting
                pdf_url = None
                if export_url:
                    pdf_url = _upload_pdf_to_blob(export_url, title)

                return GammaDeckResult(gamma_url=gamma_url, pdf_url=pdf_url or export_url)

            if status == "failed":
                error = poll_data.get("error") or poll_data.get("message") or "Unknown error"
                logger.error("[gamma] Generation failed: %s | Full response: %s", error, str(poll_data)[:500])
                return None

            if i % 6 == 0:
                logger.info("[gamma] Polling... status=%s (%ds elapsed)", status, (i + 1) * POLL_INTERVAL)

        except Exception as e:
            logger.warning("[gamma] Poll error (attempt %d): %s", i + 1, e)

    logger.error("[gamma] Generation timed out after %ds for '%s'", MAX_POLLS * POLL_INTERVAL, title)
    return None


def _upload_pdf_to_blob(export_url: str, title: str) -> Optional[str]:
    """Download PDF from Gamma's temporary export URL and upload to Vercel Blob."""
    import os
    import re

    try:
        # Download the PDF
        pdf_resp = requests.get(export_url, timeout=60)
        pdf_resp.raise_for_status()
        content = pdf_resp.content
        logger.info("[gamma] Downloaded PDF: %d bytes", len(content))

        # Upload to Vercel Blob
        import vercel_blob
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
        blob_path = f"decks/{slug}-{int(time.time())}.pdf"
        blob = vercel_blob.put(blob_path, content, {"access": "public", "contentType": "application/pdf"})
        blob_url = blob.get("url") if isinstance(blob, dict) else getattr(blob, "url", None)

        if blob_url:
            logger.info("[gamma] PDF uploaded to blob: %s", blob_url)
            return blob_url
        logger.warning("[gamma] Blob upload returned no URL: %s", blob)
        return None

    except ImportError:
        logger.warning("[gamma] vercel_blob not installed — returning temporary export URL")
        return None
    except Exception as e:
        logger.warning("[gamma] PDF upload failed: %s", e)
        return None
