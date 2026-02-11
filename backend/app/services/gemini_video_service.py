"""
Gemini video analysis service for Creative MRI.
Downloads video from URL, sends to Gemini for transcript/visual analysis,
returns structured JSON for inclusion in LLM context.
"""
import asyncio
import json
import logging
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

GEMINI_VIDEO_PROMPT = """Analyze this ad video for marketing effectiveness. Output a single JSON object (no markdown) with exactly these keys:

{
  "transcript": "Full spoken words/voiceover if any, or null if no speech",
  "visual_scenes": ["Short description of key visual moments with rough timestamps, e.g. '0:00-0:03 Product shot on white', '0:04-0:07 Bullet points appear'"],
  "on_screen_text": ["Exact or paraphrased text shown on screen (overlays, captions)"],
  "proof_shown_visually": ["What proof elements are shown (clinical data, testimonial, before/after, demo, etc.) with when they appear"],
  "emotional_cues": ["Noted tone, music, pacing, or emotional signals"],
  "duration_seconds": <actual duration if inferrable, else null>
}

Be concise. Use null for missing values. Keep arrays short (max 8 items each)."""


class GeminiVideoService:
    """Service for analyzing ad videos via Google Gemini."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = (api_key or "").strip() or None

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def analyze_video_url(self, video_url: str) -> Optional[Dict[str, Any]]:
        """
        Download video from URL, send to Gemini, return structured analysis.
        Returns None on failure (download error, API error, parse error).
        """
        if not self.api_key:
            logger.warning("Gemini API key not configured; skipping video analysis")
            return None

        try:
            # Download video
            async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                resp = await client.get(video_url)
                resp.raise_for_status()
                video_bytes = resp.content

            if len(video_bytes) > 20 * 1024 * 1024:  # 20 MB inline limit
                logger.warning(
                    "Video too large for inline (>20 MB), truncating or skipping: %s bytes",
                    len(video_bytes),
                )
                # Optionally truncate or use Files API; for now skip
                return None

            return await self._analyze_video_bytes(video_bytes, "video/mp4")
        except Exception as e:
            logger.warning("Video download/analysis failed for %s: %s", video_url[:80], e)
            return None

    def _call_gemini_sync(
        self, video_bytes: bytes, mime_type: str
    ) -> Optional[str]:
        """Sync call to Gemini (run in thread to avoid blocking)."""
        try:
            from google import genai
            from google.genai import types
        except ImportError:
            logger.warning("google-genai not installed; run: pip install google-genai")
            return None

        try:
            client = genai.Client(api_key=self.api_key)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    types.Content(
                        parts=[
                            types.Part(
                                inline_data=types.Blob(
                                    data=video_bytes,
                                    mime_type=mime_type,
                                )
                            ),
                            types.Part(text=GEMINI_VIDEO_PROMPT),
                        ]
                    )
                ],
            )
            return (response.text or "").strip()
        except Exception as e:
            logger.warning("Gemini API call failed: %s", e)
            return None

    async def _analyze_video_bytes(
        self, video_bytes: bytes, mime_type: str = "video/mp4"
    ) -> Optional[Dict[str, Any]]:
        """Send video bytes to Gemini and parse JSON response (runs sync in thread)."""
        text = await asyncio.to_thread(
            self._call_gemini_sync, video_bytes, mime_type
        )
        if not text:
            return None
        try:
            # Strip markdown code block if present
            if text.startswith("```"):
                lines = text.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                text = "\n".join(lines)
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.warning("Gemini video analysis JSON parse failed: %s", e)
            return None
