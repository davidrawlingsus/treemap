"""
Gamma deck generation service.

Generates a presentation deck via the Gamma API from markdown content.
Gracefully returns None if not configured or if the API fails.
"""

import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)

GAMMA_API_BASE = "https://gamma.app/api/v1"


def generate_deck(
    api_key: Optional[str],
    title: str,
    markdown_content: str,
) -> Optional[str]:
    """Generate a Gamma deck from markdown. Returns share URL or None."""
    if not api_key:
        logger.info("[gamma] Not configured — skipping deck generation")
        return None

    try:
        resp = requests.post(
            f"{GAMMA_API_BASE}/generate",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "title": title,
                "content": markdown_content,
                "format": "presentation",
            },
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        share_url = data.get("share_url") or data.get("url")
        if share_url:
            logger.info("[gamma] Deck created: %s", share_url)
        return share_url
    except Exception as e:
        logger.warning("[gamma] Deck generation failed: %s", e)
        return None
