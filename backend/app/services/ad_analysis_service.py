"""
Ad analysis service — Full Funnel rubric scoring via Claude.

Assesses ad copy quality through the lens of direct-response creative strategy:
hook strength, mind-movie language, emotional specificity, funnel stage, latency.

Also provides review signal analysis — scoring reviews for emotional arc
vs. low-signal "fast shipping / great customer service" filler.
"""

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import anthropic

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Full Funnel Ad Analysis
# ---------------------------------------------------------------------------

FULL_FUNNEL_SYSTEM_PROMPT = """\
You are a senior Facebook Ads creative strategist who specialises in direct-response performance creative grounded in Voice of Customer (VoC) methodology.

You will receive one or more Facebook ads (primary text, headline, description, CTA, format, age info). For EACH ad, produce a JSON object with these fields:

{
  "library_id": "<from input>",
  "hook_score": <1-10>,
  "hook_analysis": "<1-2 sentences: what hook technique is used, why it does/doesn't stop the scroll>",
  "mind_movie_score": <1-10>,
  "mind_movie_analysis": "<1-2 sentences: does the copy create vivid mental imagery with specific, lived-in scenarios, or is it abstract/generic?>",
  "specificity_score": <1-10>,
  "specificity_analysis": "<1-2 sentences: is the language concrete (numbers, names, textures, emotions) or vague (best ever, amazing, life-changing)?>",
  "emotional_charge": <1-10>,
  "emotional_analysis": "<1-2 sentences: how emotionally loaded is the copy? Does it hit desire, fear, frustration, relief, envy, pride?>",
  "voc_density": <1-10>,
  "voc_analysis": "<1-2 sentences: does this sound like a real customer talking, or like a copywriter writing?>",
  "funnel_stage": "TOF|MOF|BOF",
  "funnel_reasoning": "<1 sentence>",
  "latency_rating": "low|medium|high",
  "latency_analysis": "<1-2 sentences: how much distance is there between reading the ad and wanting to act? Low latency = you want to click now. High latency = it's informational, brand-y, or too abstract to drive action.>",
  "overall_grade": "A|B|C|D|F",
  "one_line_verdict": "<1 punchy sentence summarising the ad's quality>",
  "biggest_weakness": "<1 sentence: the single most impactful improvement>",
  "ad_age_days": <number or null>,
  "longevity_signal": "<1 sentence: what does the run-time tell us about performance?>"
}

Scoring guide:
- 1-3: Weak / generic / no technique present
- 4-5: Functional but forgettable
- 6-7: Good — clear technique, solid execution
- 8-9: Excellent — would expect strong CTR
- 10: Elite — textbook-level execution

Hook scoring: Look for pattern interrupts, curiosity gaps, bold claims, emotional openers, specific numbers, counter-intuitive statements. Generic "Are you tired of..." = 3. "I spent $47,000 testing this" = 8+.

Mind movie scoring: Does the reader SEE themselves in a specific scene? "You're sitting on the couch..." = high. "Get the best results" = low.

Latency: Low latency ads create urgency and desire — you feel the pull to click. High latency ads feel educational, brand-building, or too abstract to prompt action. Most great DR ads are low-to-medium latency.

Return a JSON array of objects. One per ad. No markdown, no explanation — just valid JSON."""


def analyze_ads_full_funnel(
    ads: List[Dict[str, Any]],
    anthropic_api_key: str,
) -> List[Dict[str, Any]]:
    """Run Full Funnel rubric analysis on extracted ad copy via Claude.

    Args:
        ads: List of ad dicts with primary_text, headline, description, etc.
        anthropic_api_key: Anthropic API key for Claude calls.

    Returns:
        List of analysis result dicts, one per ad.
    """
    if not ads:
        return []

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
        client = anthropic.Anthropic(api_key=anthropic_api_key)
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4096,
            system=FULL_FUNNEL_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        raw = response.content[0].text.strip()
        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
            if raw.endswith("```"):
                raw = raw[:-3]
            raw = raw.strip()

        results = json.loads(raw)
        if isinstance(results, dict):
            results = [results]
        return results

    except json.JSONDecodeError as e:
        logger.error("Failed to parse Claude response as JSON: %s", e)
        return [{"error": "Failed to parse analysis response", "raw": raw[:500]}]
    except Exception as e:
        logger.exception("Full Funnel analysis failed: %s", e)
        return [{"error": str(e)}]


# ---------------------------------------------------------------------------
# Review Signal Analysis
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

You will receive a batch of reviews. For EACH review, return:
{
  "review_index": <0-based index>,
  "signal_level": "high|medium|low",
  "signal_score": <1-10>,
  "reason": "<1 sentence explaining why>",
  "usable_quote": "<best verbatim snippet for ad copy, or null if low signal>",
  "themes": ["<theme1>", "<theme2>"]
}

Also return a summary object at the end:
{
  "summary": true,
  "total_reviews": <n>,
  "high_signal_count": <n>,
  "medium_signal_count": <n>,
  "low_signal_count": <n>,
  "overall_signal_grade": "A|B|C|D|F",
  "top_themes": ["<theme1>", "<theme2>", "<theme3>"],
  "verdict": "<2-3 sentences: is this review corpus rich enough for VoC-driven ads? What's the overall quality of customer language?>"
}

Return a JSON array. No markdown, no explanation — just valid JSON."""


def analyze_review_signal(
    reviews: List[Dict[str, Any]],
    anthropic_api_key: str,
    max_reviews: int = 20,
) -> List[Dict[str, Any]]:
    """Analyze reviews for signal quality — emotion, arc, specificity vs generic praise.

    Args:
        reviews: List of review dicts with at minimum a "text" or "body" field.
        anthropic_api_key: Anthropic API key.
        max_reviews: Cap on reviews to send (keeps token cost reasonable).

    Returns:
        List of per-review signal assessments plus a summary object.
    """
    if not reviews:
        return [{"summary": True, "total_reviews": 0, "high_signal_count": 0,
                 "medium_signal_count": 0, "low_signal_count": 0,
                 "overall_signal_grade": "F",
                 "top_themes": [],
                 "verdict": "No reviews available to analyze."}]

    # Normalize review text
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
        return [{"summary": True, "total_reviews": 0, "high_signal_count": 0,
                 "medium_signal_count": 0, "low_signal_count": 0,
                 "overall_signal_grade": "F", "top_themes": [],
                 "verdict": "No reviews had readable text."}]

    user_message = (
        f"Analyze these {len(review_texts)} reviews for signal quality.\n\n"
        + "\n\n".join(review_texts)
    )

    try:
        client = anthropic.Anthropic(api_key=anthropic_api_key)
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4096,
            system=REVIEW_SIGNAL_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
            if raw.endswith("```"):
                raw = raw[:-3]
            raw = raw.strip()

        results = json.loads(raw)
        if isinstance(results, dict):
            results = [results]
        return results

    except json.JSONDecodeError as e:
        logger.error("Failed to parse review signal response: %s", e)
        return [{"error": "Failed to parse analysis response", "raw": raw[:500]}]
    except Exception as e:
        logger.exception("Review signal analysis failed: %s", e)
        return [{"error": str(e)}]
