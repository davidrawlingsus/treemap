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

try:
    from app.services.mri_media_diagnostic import (
        log_gemini_video_download,
        log_gemini_image_download,
        log_gemini_video_analysis,
        log_gemini_video_analysis_failed,
    )
except ImportError:
    def _noop(*a, **k): pass
    log_gemini_video_download = log_gemini_image_download = log_gemini_video_analysis = log_gemini_video_analysis_failed = _noop

logger = logging.getLogger(__name__)

GEMINI_VIDEO_PROMPT = """Analyze this ad video for marketing effectiveness. Output a single JSON object (no markdown) with exactly these keys:

{
  "transcript": "Full spoken words/voiceover if any, or null if no speech",
  "visual_scenes": ["Short description of key visual moments with rough timestamps, e.g. '0:00-0:03 Product shot on white', '0:04-0:07 Bullet points appear'"],
  "on_screen_text": ["Exact or paraphrased text shown on screen (overlays, captions)"],
  "proof_shown_visually": ["What proof elements are shown (clinical data, testimonial, before/after, demo, etc.) with when they appear"],
  "emotional_cues": ["Noted tone, music, pacing, or emotional signals"],
  "duration_seconds": <actual duration if inferrable, else null>,
  "timeline_first_2s": {
    "transcript_excerpt": "First ~12 words or first sentence of transcript (approximate first 2 seconds of speech), or null",
    "on_screen_text_excerpt": "First overlay/caption text shown in first 2 seconds, or null",
    "visual_description": "Brief description of what appears on screen in first 2 seconds, or null"
  }
}

Be concise. Use null for missing values. Keep arrays short (max 8 items each). For timeline_first_2s, approximate if precise timestamps are unavailable: use first sentence or first ~12 words for transcript, first overlay item for on_screen_text."""

GEMINI_IMAGE_PROMPT = """Analyze this ad image for marketing effectiveness. Output a single JSON object (no markdown) with exactly these keys:

{
  "visual_description": "Brief description of the main visual (product, person, scene, layout)",
  "on_screen_text": ["Exact or paraphrased text shown in the image (overlays, captions, headlines)"],
  "proof_shown_visually": ["What proof elements are shown (clinical data, testimonial, before/after, demo, badges, logos)"],
  "emotional_cues": ["Noted tone, imagery style, or emotional signals"],
  "focal_point": "What the eye is drawn to first, or null",
  "layout_style": "e.g. product shot, lifestyle, testimonial, infographic, or null"
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
            async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                resp = await client.get(video_url)
                log_gemini_video_download(video_url, resp.status_code, len(resp.content), None)
                resp.raise_for_status()
                video_bytes = resp.content

            if len(video_bytes) > 20 * 1024 * 1024:  # 20 MB inline limit
                log_gemini_video_download(video_url, 200, len(video_bytes), "video_too_large_20mb")
                logger.warning(
                    "Video too large for inline (>20 MB), truncating or skipping: %s bytes",
                    len(video_bytes),
                )
                return None

            analysis, fail_reason = await self._analyze_video_bytes(video_bytes, "video/mp4")
            if analysis:
                t = analysis.get("transcript") or (analysis.get("timeline_first_2s") or {}).get("transcript_excerpt")
                log_gemini_video_analysis(video_url, bool(t), len(t) if t else 0)
                return analysis
            log_gemini_video_analysis_failed(video_url, fail_reason or "unknown")
            return None
        except Exception as e:
            log_gemini_video_download(video_url, -1, 0, str(e))
            logger.warning("Video download/analysis failed for %s: %s", video_url[:80], e)
            return None

    async def analyze_image_url(self, image_url: str) -> Optional[Dict[str, Any]]:
        """
        Download image from URL, send to Gemini, return structured analysis.
        Returns None on failure.
        """
        if not self.api_key:
            logger.warning("Gemini API key not configured; skipping image analysis")
            return None

        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                resp = await client.get(image_url)
                log_gemini_image_download(image_url, resp.status_code, len(resp.content), None)
                resp.raise_for_status()
                image_bytes = resp.content

            if len(image_bytes) > 4 * 1024 * 1024:  # 4 MB inline limit
                log_gemini_image_download(image_url, 200, len(image_bytes), "image_too_large_4mb")
                logger.warning("Image too large for inline (>4 MB): %s bytes", len(image_bytes))
                return None

            mime = "image/jpeg"
            if image_url.lower().endswith(".png"):
                mime = "image/png"
            elif image_url.lower().endswith(".webp"):
                mime = "image/webp"
            elif image_url.lower().endswith(".gif"):
                mime = "image/gif"

            return await self._analyze_image_bytes(image_bytes, mime)
        except Exception as e:
            log_gemini_image_download(image_url, -1, 0, str(e))
            logger.warning("Image download/analysis failed for %s: %s", image_url[:80], e)
            return None

    def _call_gemini_sync(
        self, media_bytes: bytes, mime_type: str, prompt: str
    ) -> tuple[Optional[str], Optional[str]]:
        """Sync call to Gemini (run in thread to avoid blocking).
        Returns (text, None) on success, (None, error_reason) on failure."""
        try:
            from google import genai
            from google.genai import types
        except ImportError as e:
            logger.warning("google-genai not installed; run: pip install google-genai")
            return None, "import_error:google-genai"

        try:
            client = genai.Client(api_key=self.api_key)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    types.Content(
                        parts=[
                            types.Part(
                                inline_data=types.Blob(
                                    data=media_bytes,
                                    mime_type=mime_type,
                                )
                            ),
                            types.Part(text=prompt),
                        ]
                    )
                ],
            )
            text = (response.text or "").strip()
            return (text, None) if text else (None, "gemini_empty_response")
        except Exception as e:
            err = str(e)
            logger.warning("Gemini API call failed: %s", err)
            return None, f"api_error:{err[:120]}"

    async def _analyze_video_bytes(
        self, video_bytes: bytes, mime_type: str = "video/mp4"
    ) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Send video bytes to Gemini and parse JSON response (runs sync in thread).
        Returns (analysis_dict, None) on success, (None, error_reason) on failure."""
        text, call_err = await asyncio.to_thread(
            self._call_gemini_sync, video_bytes, mime_type, GEMINI_VIDEO_PROMPT
        )
        if not text:
            return None, call_err or "gemini_empty_response"
        try:
            if text.startswith("```"):
                lines = text.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                text = "\n".join(lines)
            out = json.loads(text)
            return _ensure_timeline_first_2s(out), None
        except json.JSONDecodeError as e:
            logger.warning("Gemini video analysis JSON parse failed: %s", e)
            return None, f"json_parse_error:{str(e)[:80]}"

    async def _analyze_image_bytes(
        self, image_bytes: bytes, mime_type: str = "image/jpeg"
    ) -> Optional[Dict[str, Any]]:
        """Send image bytes to Gemini and parse JSON response."""
        text, _ = await asyncio.to_thread(
            self._call_gemini_sync, image_bytes, mime_type, GEMINI_IMAGE_PROMPT
        )
        if not text:
            return None
        try:
            if text.startswith("```"):
                lines = text.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                text = "\n".join(lines)
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.warning("Gemini image analysis JSON parse failed: %s", e)
            return None


def _ensure_timeline_first_2s(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure timeline_first_2s exists; approximate from transcript/on_screen_text if missing."""
    if "timeline_first_2s" in analysis and isinstance(analysis["timeline_first_2s"], dict):
        return analysis
    t = analysis.get("transcript") or ""
    ost = analysis.get("on_screen_text") or []
    first_ost = ost[0] if isinstance(ost, list) and ost else None
    words = t.split()[:12] if isinstance(t, str) else []
    transcript_excerpt = " ".join(words) if words else None
    analysis["timeline_first_2s"] = {
        "transcript_excerpt": transcript_excerpt,
        "on_screen_text_excerpt": first_ost if isinstance(first_ost, str) else None,
        "visual_description": None,
    }
    return analysis
