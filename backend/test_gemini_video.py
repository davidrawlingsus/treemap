#!/usr/bin/env python3
"""
Quick test of Gemini video analysis - connection and payload.
Run from backend/: python test_gemini_video.py [video_url]

Uses GEMINI_API_KEY from .env. If no URL given, uses a small public sample.
"""
import asyncio
import json
import sys
from pathlib import Path

# Load env before imports
from dotenv import load_dotenv
PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env", override=False)

# Add backend to path
sys.path.insert(0, str(PROJECT_ROOT))

from app.config import get_settings
from app.services.gemini_video_service import GeminiVideoService

# Small public test video (~1MB)
DEFAULT_VIDEO_URL = "https://www.w3schools.com/html/mov_bbb.mp4"


async def main():
    video_url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_VIDEO_URL
    settings = get_settings()
    api_key = settings.gemini_api_key

    if not api_key:
        print("ERROR: GEMINI_API_KEY not set in .env")
        sys.exit(1)

    print(f"Testing Gemini video analysis")
    print(f"  URL: {video_url[:80]}...")
    print(f"  API key: {api_key[:8]}...{api_key[-4:]}")
    print()

    service = GeminiVideoService(api_key=api_key)
    if not service.is_configured():
        print("ERROR: GeminiVideoService reports not configured")
        sys.exit(1)

    print("Calling analyze_video_url...")
    try:
        analysis = await service.analyze_video_url(video_url)
        if analysis:
            print("SUCCESS")
            print("Keys:", list(analysis.keys()))
            transcript = analysis.get("transcript") or (analysis.get("timeline_first_2s") or {}).get("transcript_excerpt")
            print("Has transcript:", bool(transcript))
            if transcript:
                print("Transcript preview:", transcript[:200] + "..." if len(transcript) > 200 else transcript)
            print()
            print("Full analysis (truncated):")
            print(json.dumps(analysis, indent=2)[:1500] + "...")
        else:
            print("FAILED: analyze_video_url returned None")
    except Exception as e:
        print(f"EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
