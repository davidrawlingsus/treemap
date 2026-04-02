"""
Gamma deck generation service.

Generates a presentation deck via the Gamma API from markdown content.
Uses the v1.0 Generate API (async: create job → poll until complete).
"""

import logging
import time
from typing import Optional

import requests

logger = logging.getLogger(__name__)

GAMMA_API_BASE = "https://public-api.gamma.app/v1.0"
POLL_INTERVAL = 5  # seconds
MAX_POLLS = 120  # 10 minutes max wait


def generate_deck(
    api_key: Optional[str],
    title: str,
    markdown_content: str,
) -> Optional[str]:
    """Generate a Gamma presentation from markdown content.

    Returns the share URL (gammaUrl) or None on failure.
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

    # Step 1: Start generation
    try:
        body = {
            "inputText": f"# {title}\n\n{markdown_content}",
            "textMode": "preserve",
            "format": "presentation",
            "numCards": 20,
            "themeId": "zlj1eyfj4b520tb",  # Map_The_Gap theme
            "textOptions": {
                "tone": "professional",
                "amount": "detailed",
            },
            "imageOptions": {
                "source": "noImages",
            },
            "sharingOptions": {
                "externalAccess": "view",
            },
        }

        logger.info("[gamma] Starting generation for '%s' (%d chars)", title, len(markdown_content))
        resp = requests.post(
            f"{GAMMA_API_BASE}/generations",
            headers=headers,
            json=body,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        generation_id = data.get("id") or data.get("generationId")
        if not generation_id:
            logger.warning("[gamma] No generation ID in response: %s", data)
            return None

        logger.info("[gamma] Generation started: %s", generation_id)

    except Exception as e:
        logger.warning("[gamma] Failed to start generation: %s", e)
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
            poll_resp.raise_for_status()
            poll_data = poll_resp.json()
            status = poll_data.get("status", "")

            if status == "completed":
                gamma_url = poll_data.get("gammaUrl")
                export_url = poll_data.get("exportUrl")
                logger.info("[gamma] Deck created: %s (export: %s)", gamma_url, export_url)
                return gamma_url

            if status == "failed":
                error = poll_data.get("error") or poll_data.get("message") or "Unknown error"
                logger.warning("[gamma] Generation failed: %s", error)
                return None

            if i % 6 == 0:
                logger.info("[gamma] Polling... status=%s (%ds elapsed)", status, (i + 1) * POLL_INTERVAL)

        except Exception as e:
            logger.warning("[gamma] Poll error (attempt %d): %s", i + 1, e)

    logger.warning("[gamma] Generation timed out after %ds", MAX_POLLS * POLL_INTERVAL)
    return None
