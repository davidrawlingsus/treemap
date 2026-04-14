"""
Ad analysis service — Full Funnel rubric scoring via Claude.

Streams analysis as formatted text rather than JSON to avoid parsing issues.
Also provides review signal analysis with the same streaming approach.

Prompts are loaded from the database (prompts table) by purpose, with
hardcoded constants as fallback if DB lookup fails.
"""

import logging
from typing import Any, Dict, Generator, List, Optional

import anthropic
import httpx

logger = logging.getLogger(__name__)


def _load_prompt(purpose: str, fallback: str) -> tuple:
    """Load a prompt from the database by purpose. Returns (system_message, model).

    Falls back to the hardcoded prompt if DB is unavailable or prompt not found.
    """
    try:
        from app.database import SessionLocal
        from app.models import Prompt
        db = SessionLocal()
        try:
            prompt = (
                db.query(Prompt)
                .filter(Prompt.prompt_purpose == purpose, Prompt.status == "live")
                .order_by(Prompt.version.desc())
                .first()
            )
            if prompt and prompt.system_message:
                return prompt.system_message, prompt.llm_model or "claude-sonnet-4-5-20250929"
        finally:
            db.close()
    except Exception as e:
        logger.debug("Could not load prompt '%s' from DB, using fallback: %s", purpose, e)
    return fallback, "claude-sonnet-4-5-20250929"

# ---------------------------------------------------------------------------
# Full Funnel Ad Analysis (streaming text)
# ---------------------------------------------------------------------------

FULL_FUNNEL_SYSTEM_PROMPT = """\
You are a senior Facebook Ads creative strategist who specialises in direct-response performance creative grounded in Voice of Customer (VoC) methodology.

You will receive one or more Facebook ads. For EACH ad, write your analysis using EXACTLY this format (keep the markers and labels exactly as shown):

===AD===
ID: <library_id or "Ad N">
GRADE: <A|B|C|D|F>
VERDICT: <1 punchy sentence summarising the ad's quality>
WEAKNESS: <1 sentence: the single most impactful improvement>
HOOK: <1-10> — <1-2 sentences: what hook technique is used, why it does/doesn't stop the scroll>
MIND MOVIE: <1-10> — <1-2 sentences: does the copy create vivid mental imagery?>
SPECIFICITY: <1-10> — <1-2 sentences: concrete numbers/names vs vague claims?>
EMOTION: <1-10> — <1-2 sentences: how emotionally loaded? desire, fear, frustration, relief?>
VOC DENSITY: <1-10> — <1-2 sentences: sounds like a customer or a copywriter?>
LATENCY: <low|medium|high> — <1-2 sentences: distance between reading and wanting to act>
FUNNEL: <TOF|MOF|BOF> — <1 sentence reasoning>
LONGEVITY: <1 sentence: what does run-time tell us about performance?>
===END===

Scoring guide:
- 1-3: Weak / generic / no technique present
- 4-5: Functional but forgettable
- 6-7: Good — clear technique, solid execution
- 8-9: Excellent — would expect strong CTR
- 10: Elite — textbook-level execution

Write nothing before the first ===AD=== and nothing after the last ===END===."""


def stream_ads_analysis(
    ads: List[Dict[str, Any]],
    anthropic_api_key: str,
) -> Generator[str, None, None]:
    """Stream Full Funnel rubric analysis as formatted text chunks via Claude.

    Yields text chunks as they arrive from the Claude streaming API.
    """
    if not ads:
        yield "No ads to analyze."
        return

    # Build the user message with all ads
    ad_descriptions = []
    for i, ad in enumerate(ads, 1):
        parts = [f"--- Ad {i} ---"]
        if ad.get("library_id"):
            parts.append(f"Library ID: {ad['library_id']}")
        if ad.get("primary_text"):
            parts.append(f"Primary Text: {ad['primary_text'][:2000]}")
        if ad.get("headline"):
            parts.append(f"Headline: {ad['headline']}")
        if ad.get("description"):
            parts.append(f"Description: {ad['description']}")
        if ad.get("cta"):
            parts.append(f"CTA: {ad['cta']}")
        if ad.get("ad_format"):
            parts.append(f"Format: {ad['ad_format']}")
        if ad.get("started_running_on"):
            parts.append(f"Started Running: {ad['started_running_on']}")
        if ad.get("ad_delivery_end_time"):
            parts.append(f"Ended: {ad['ad_delivery_end_time']}")
        if ad.get("status"):
            parts.append(f"Status: {ad['status']}")
        if ad.get("destination_url"):
            parts.append(f"Destination URL: {ad['destination_url']}")
        ad_descriptions.append("\n".join(parts))

    user_message = (
        f"Analyze these {len(ads)} Facebook ads using the Full Funnel rubric.\n\n"
        + "\n\n".join(ad_descriptions)
    )

    try:
        system_prompt, model = _load_prompt("extension_ad_analysis", FULL_FUNNEL_SYSTEM_PROMPT)

        client = anthropic.Anthropic(
            api_key=anthropic_api_key,
            http_client=httpx.Client(timeout=180.0),
        )

        # ~250 tokens per ad analysis, plus buffer
        token_budget = max(4096, len(ads) * 300 + 512)

        with client.messages.stream(
            model=model,
            max_tokens=token_budget,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        ) as stream:
            for text in stream.text_stream:
                yield text

    except Exception as e:
        logger.exception("Full Funnel streaming analysis failed: %s", e)
        yield f"\n\nError: {e}"


# ---------------------------------------------------------------------------
# Opportunity Synthesis (streaming text)
# ---------------------------------------------------------------------------

SYNTHESIS_SYSTEM_PROMPT = """\
You are a senior performance creative strategist. You have just analyzed a set of Facebook ads for a single advertiser.

Given the full per-ad analysis below, write a short synthesis using EXACTLY this format:

===SYNTHESIS===
AD_COPY_SCORE: <1-10 — overall quality of this advertiser's ad copy. 10 = elite, sophisticated VoC-driven creative. 1 = generic, formulaic, no emotional resonance.>
SUMMARY: <2-3 sentences: overall quality of this advertiser's creative suite. Are they sophisticated or formulaic? VoC-rich or generic?>
PATTERNS: <2-3 bullet points — recurring strengths or weaknesses across ads>
PLAYBOOK: <2-3 bullet points — specific creative angles or tactics you'd use to beat them>
===END===

Write nothing before ===SYNTHESIS=== and nothing after ===END===."""


def stream_synthesis(
    analysis_text: str,
    anthropic_api_key: str,
) -> Generator[str, None, None]:
    """Stream opportunity synthesis based on completed per-ad analysis."""
    if not analysis_text.strip():
        yield "===SYNTHESIS===\nOPPORTUNITY: ?\nSUMMARY: No analysis available.\nPATTERNS: None\nPLAYBOOK: None\n===END==="
        return

    try:
        system_prompt, model = _load_prompt("extension_synthesis", SYNTHESIS_SYSTEM_PROMPT)

        client = anthropic.Anthropic(
            api_key=anthropic_api_key,
            http_client=httpx.Client(timeout=180.0),
        )

        with client.messages.stream(
            model=model,
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": f"Here is the per-ad analysis:\n\n{analysis_text}"}],
        ) as stream:
            for text in stream.text_stream:
                yield text

    except Exception as e:
        logger.exception("Synthesis streaming failed: %s", e)
        yield f"\n\nError: {e}"


# ---------------------------------------------------------------------------
# Review Signal Analysis (streaming text)
# ---------------------------------------------------------------------------

REVIEW_SIGNAL_SYSTEM_PROMPT = """\
You are a Voice of Customer analyst who specialises in identifying high-signal reviews for direct-response advertising.

HIGH-SIGNAL reviews contain:
- Emotional arc (before/after transformation)
- Specific, lived-in detail ("I've had back pain for 12 years", "my daughter noticed the difference")
- Desire language, relief, frustration, surprise, delight
- Identity shifts ("I finally feel like myself again")
- Sensory language (textures, feelings, scenes)
- Objection-busting moments ("I was skeptical but...")

LOW-SIGNAL reviews contain:
- Generic praise ("great product", "love it", "5 stars")
- Logistics praise ("fast shipping", "great customer service", "arrived on time")
- One-liners with no specificity
- No emotional content or transformation

IMPORTANT CONTEXT: You are analyzing a SAMPLE of ~20 reviews from the first page. A full extraction would pull hundreds or thousands. Grade the POTENTIAL of this review corpus, not just the sample:
- 2-3 high-signal reviews in a sample of 20 is a STRONG signal — a full extraction will yield 10x-50x more usable material. Grade this A or B.
- Even 1 high-signal review with emotional depth suggests the customer base produces rich VoC language. That's encouraging.
- Only grade C or below if the sample is almost entirely generic praise with zero emotional content, transformation arcs, or specificity.
- The question is: "If we scraped ALL their reviews, would we find enough gold for VoC-driven ad campaigns?" Be optimistic when there are encouraging signs.

For each batch of reviews, write your analysis using EXACTLY this format:

===SUMMARY===
SIGNAL_SCORE: <1-10 — overall VoC signal quality of this review corpus. 10 = goldmine of emotional, specific, transformation-rich reviews. 1 = entirely generic praise with no usable VoC.>
HIGH: <count>
MEDIUM: <count>
LOW: <count>
THEMES: <theme1>, <theme2>, <theme3>
VERDICT: <2-3 sentences: assess the POTENTIAL of this review corpus at scale. If there are high-signal reviews in this small sample, note that a full extraction would multiply that signal significantly.>
===END===

Then for EACH review:

===REVIEW===
INDEX: <1-based number>
SIGNAL: <high|medium|low>
SCORE: <1-10>
REASON: <1 sentence explaining why>
QUOTE: <best verbatim snippet for ad copy, or "none" if low signal>
===END===

Write nothing before ===SUMMARY=== and nothing after the last ===END===.
Sort reviews by signal level: high first, then medium, then low."""


def stream_review_signal(
    reviews: List[Dict[str, Any]],
    anthropic_api_key: str,
    max_reviews: int = 50,
) -> Generator[str, None, None]:
    """Stream review signal analysis as formatted text chunks via Claude."""
    if not reviews:
        yield "===SUMMARY===\nGRADE: F\nHIGH: 0\nMEDIUM: 0\nLOW: 0\nTHEMES: none\nVERDICT: No reviews available to analyze.\n===END==="
        return

    capped = reviews[:max_reviews]
    review_texts = []
    for i, r in enumerate(capped):
        text = r.get("text") or r.get("body") or r.get("reviewBody") or r.get("content") or ""
        text = text.strip()
        if not text:
            continue
        rating = r.get("rating") or r.get("stars") or r.get("score") or ""
        author = r.get("author") or r.get("reviewer") or r.get("name") or ""
        parts = [f"--- Review {i + 1} ---"]
        if author:
            parts.append(f"Author: {author}")
        if rating:
            parts.append(f"Rating: {rating}")
        parts.append(f"Text: {text[:1500]}")
        review_texts.append("\n".join(parts))

    if not review_texts:
        yield "===SUMMARY===\nGRADE: F\nHIGH: 0\nMEDIUM: 0\nLOW: 0\nTHEMES: none\nVERDICT: No reviews had readable text.\n===END==="
        return

    user_message = (
        f"Analyze these {len(review_texts)} reviews for signal quality.\n\n"
        + "\n\n".join(review_texts)
    )

    try:
        system_prompt, model = _load_prompt("extension_review_signal", REVIEW_SIGNAL_SYSTEM_PROMPT)

        client = anthropic.Anthropic(
            api_key=anthropic_api_key,
            http_client=httpx.Client(timeout=180.0),
        )

        # ~120 tokens per review assessment + summary
        token_budget = max(4096, len(review_texts) * 150 + 512)

        with client.messages.stream(
            model=model,
            max_tokens=token_budget,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        ) as stream:
            for text in stream.text_stream:
                yield text

    except Exception as e:
        logger.exception("Review signal streaming analysis failed: %s", e)
        yield f"\n\nError: {e}"
