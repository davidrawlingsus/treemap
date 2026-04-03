"""
VoC Creative Strategy Analysis Service.

Two-step process:
1. generate_voc_analysis_markdown() — Opus produces the full markdown analysis
2. parse_voc_analysis_to_json() — Sonnet extracts structured JSON from the markdown

The markdown is the canonical output (stored, displayed in slideout).
The JSON is derived for programmatic use (email queue, Gamma deck).
"""

import json
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# JSON Schema (used by the parse step only)
# ---------------------------------------------------------------------------

VOC_ANALYSIS_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": [
        "data_snapshot", "headline_insight", "creative_strategy_insights",
        "language_gold", "objection_map", "contradictions_and_complexity",
        "sequence_architecture", "emails", "deck_markdown",
    ],
    "properties": {
        "data_snapshot": {
            "type": "object",
            "required": ["temporal_window", "review_count", "primary_creative_lenses", "single_biggest_gap"],
            "properties": {
                "temporal_window": {"type": "string"},
                "review_count": {"type": "integer"},
                "primary_creative_lenses": {"type": "array", "items": {"type": "string"}},
                "single_biggest_gap": {"type": "string"},
            },
        },
        "headline_insight": {
            "type": "object",
            "required": ["what_ads_probably_say", "what_customers_actually_say", "creative_opportunity", "supporting_verbatims"],
            "properties": {
                "what_ads_probably_say": {"type": "string"},
                "what_customers_actually_say": {"type": "string"},
                "creative_opportunity": {"type": "string"},
                "supporting_verbatims": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["text"],
                        "properties": {
                            "text": {"type": "string"},
                            "date": {"type": ["string", "null"]},
                        },
                    },
                },
            },
        },
        "creative_strategy_insights": {
            "type": "array",
            "minItems": 6,
            "maxItems": 12,
            "items": {
                "type": "object",
                "required": ["title", "signal_type", "finding", "messaging_gap", "trajectory", "evidence", "creative_implications", "serialisation_notes"],
                "properties": {
                    "title": {"type": "string"},
                    "signal_type": {
                        "type": "string",
                        "enum": [
                            "message_reality_gap", "hidden_purchase_trigger",
                            "language_brand_not_using", "emotional_buying_architecture",
                            "objection_narrative", "audience_brand_doesnt_know",
                        ],
                    },
                    "finding": {"type": "string"},
                    "messaging_gap": {"type": "string"},
                    "trajectory": {
                        "type": "string",
                        "enum": ["emerging", "persisting", "fading", "insufficient_data"],
                    },
                    "evidence": {
                        "type": "array",
                        "minItems": 3,
                        "maxItems": 5,
                        "items": {
                            "type": "object",
                            "required": ["text"],
                            "properties": {
                                "text": {"type": "string"},
                                "date": {"type": ["string", "null"]},
                            },
                        },
                    },
                    "creative_implications": {
                        "type": "object",
                        "required": ["funnel_stage", "creative_lane", "emotional_register"],
                        "properties": {
                            "funnel_stage": {
                                "type": "string",
                                "enum": ["top_funnel", "mid_funnel", "bottom_funnel", "cross_funnel"],
                            },
                            "creative_lane": {"type": "string"},
                            "emotional_register": {"type": "string"},
                        },
                    },
                    "serialisation_notes": {
                        "type": "object",
                        "required": ["sequence_position", "pairs_with", "target_response"],
                        "properties": {
                            "sequence_position": {
                                "type": "string",
                                "enum": ["early", "mid", "late"],
                            },
                            "pairs_with": {"type": "array", "items": {"type": "integer"}},
                            "target_response": {"type": "string"},
                        },
                    },
                },
            },
        },
        "language_gold": {
            "type": "object",
            "required": ["the_problem", "the_transformation", "the_decision", "the_competition", "phrases_worth_stealing"],
            "properties": {
                "the_problem": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["verbatim", "ad_translation"],
                        "properties": {
                            "verbatim": {"type": "string"},
                            "date": {"type": ["string", "null"]},
                            "ad_translation": {"type": "string"},
                        },
                    },
                },
                "the_transformation": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["verbatim", "ad_translation"],
                        "properties": {
                            "verbatim": {"type": "string"},
                            "date": {"type": ["string", "null"]},
                            "ad_translation": {"type": "string"},
                        },
                    },
                },
                "the_decision": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["verbatim", "ad_translation"],
                        "properties": {
                            "verbatim": {"type": "string"},
                            "date": {"type": ["string", "null"]},
                            "ad_translation": {"type": "string"},
                        },
                    },
                },
                "the_competition": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["verbatim", "ad_translation"],
                        "properties": {
                            "verbatim": {"type": "string"},
                            "date": {"type": ["string", "null"]},
                            "ad_translation": {"type": "string"},
                        },
                    },
                },
                "phrases_worth_stealing": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["phrase", "context", "creative_potential"],
                        "properties": {
                            "phrase": {"type": "string"},
                            "context": {"type": "string"},
                            "date": {"type": ["string", "null"]},
                            "creative_potential": {"type": "string"},
                        },
                    },
                },
            },
        },
        "objection_map": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["objection", "customer_words", "frequency_intensity", "brand_likely_addresses", "what_ad_should_say"],
                "properties": {
                    "objection": {"type": "string"},
                    "customer_words": {"type": "string"},
                    "date": {"type": ["string", "null"]},
                    "frequency_intensity": {
                        "type": "string",
                        "enum": ["frequent_high", "frequent_moderate", "occasional_high", "occasional_moderate", "isolated"],
                    },
                    "brand_likely_addresses": {"type": "string"},
                    "what_ad_should_say": {"type": "string"},
                },
            },
        },
        "contradictions_and_complexity": {
            "type": "object",
            "required": ["conflicting_signals", "missing_voices", "creative_risk_flags"],
            "properties": {
                "conflicting_signals": {"type": "array", "items": {"type": "string"}},
                "missing_voices": {"type": "array", "items": {"type": "string"}},
                "data_bias": {"type": ["string", "null"]},
                "creative_risk_flags": {"type": "array", "items": {"type": "string"}},
            },
        },
        "sequence_architecture": {
            "type": "object",
            "required": ["lead_email", "narrative_arc", "closer_email", "through_line", "open_loop_map"],
            "properties": {
                "lead_email": {
                    "type": "object",
                    "required": ["insight_number", "rationale"],
                    "properties": {
                        "insight_number": {"type": "integer"},
                        "rationale": {"type": "string"},
                    },
                },
                "narrative_arc": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["email_number", "role"],
                        "properties": {
                            "email_number": {"type": "integer"},
                            "role": {"type": "string"},
                        },
                    },
                },
                "closer_email": {
                    "type": "object",
                    "required": ["insight_number", "rationale"],
                    "properties": {
                        "insight_number": {"type": "integer"},
                        "rationale": {"type": "string"},
                    },
                },
                "through_line": {"type": "string"},
                "open_loop_map": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["email_number"],
                        "properties": {
                            "email_number": {"type": "integer"},
                            "loops_opened": {"type": "array", "items": {"type": "string"}},
                            "loops_closed": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "required": ["thread", "opened_in_email"],
                                    "properties": {
                                        "thread": {"type": "string"},
                                        "opened_in_email": {"type": "integer"},
                                    },
                                },
                            },
                            "forward_hook": {"type": ["string", "null"]},
                        },
                    },
                },
            },
        },
        "emails": {
            "type": "array",
            "minItems": 9,
            "maxItems": 9,
            "items": {
                "type": "object",
                "required": ["sequence_number", "send_day", "subject_line", "preview_text", "headline", "body_sections", "cta_text", "cta_url", "strategic_intent"],
                "properties": {
                    "sequence_number": {"type": "integer", "minimum": 1, "maximum": 9},
                    "send_day": {"type": "integer", "minimum": 0},
                    "subject_line": {"type": "string"},
                    "preview_text": {"type": "string", "minLength": 30, "maxLength": 100},
                    "headline": {"type": "string"},
                    "body_sections": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["type", "content"],
                            "properties": {
                                "type": {"type": "string", "enum": ["text", "verbatim", "stat", "cta"]},
                                "content": {"type": "string"},
                                "attribution": {"type": ["string", "null"]},
                            },
                        },
                    },
                    "cta_text": {"type": "string"},
                    "cta_url": {"type": ["string", "null"]},
                    "strategic_intent": {"type": "string"},
                },
            },
        },
        "deck_markdown": {"type": "string"},
    },
}


# ---------------------------------------------------------------------------
# Step 1: Generate markdown analysis (Opus)
# ---------------------------------------------------------------------------

VOC_ANALYSIS_USER_PROMPT = """Analyze the following Voice of Customer data for {company_name} ({company_url}) and produce a complete creative strategy analysis.

## Business Context
{context_text}

## Validated Taxonomy (categories and topics from customer reviews)
{taxonomy_json}

## Review Classification Summary
{classification_summary}

## Ad Topics Generated
The following themes were selected for ad generation: {ad_topics}

Produce the full analysis following the prompt instructions. Output as markdown."""


def generate_voc_analysis_markdown(
    *,
    settings: Any,
    system_prompt: str,
    company_name: str,
    company_url: str,
    context_text: str,
    validate_output: Dict[str, Any],
    classified_reviews: List[Dict[str, Any]],
    ad_topics: List[str],
) -> str:
    """Generate the full VoC creative strategy analysis as markdown.

    Uses Opus with the live prompt (system_prompt from DB or default).
    Returns the raw markdown string.
    """
    from app.services.voc_coding_chain_service import call_claude_json_schema_streaming

    topic_summary = _build_classification_summary(classified_reviews)

    user_prompt = (
        VOC_ANALYSIS_USER_PROMPT
        .replace("{company_name}", company_name)
        .replace("{company_url}", company_url)
        .replace("{context_text}", context_text or company_name)
        .replace("{taxonomy_json}", json.dumps(validate_output, ensure_ascii=False))
        .replace("{classification_summary}", topic_summary)
        .replace("{ad_topics}", ", ".join(ad_topics) if ad_topics else "None")
    )

    logger.info(
        "[voc-analysis] Generating markdown for %s (taxonomy: %d categories, %d classified reviews)",
        company_name,
        len(validate_output.get("categories", [])),
        len(classified_reviews),
    )

    # Call Anthropic directly for raw text — no JSON schema wrapping.
    # JSON schema mode causes Opus to truncate or return garbage for very large outputs
    # because 70k+ chars of markdown must be escaped inside a JSON string.
    import anthropic
    import httpx

    MAX_RETRIES = 2
    for attempt in range(MAX_RETRIES + 1):
        try:
            # Must pass http_client to work around anthropic SDK / httpx version mismatch
            client = anthropic.Anthropic(
                api_key=settings.anthropic_api_key,
                http_client=httpx.Client(timeout=600.0),
            )
            response = client.messages.create(
                model="claude-opus-4-6",
                max_tokens=64000,
                temperature=0.5,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            markdown = response.content[0].text if response.content else ""

            if len(markdown) > 1000:
                logger.info("[voc-analysis] Generated %d chars of markdown for %s (attempt %d)",
                            len(markdown), company_name, attempt + 1)
                return markdown

            logger.warning("[voc-analysis] Short markdown (%d chars) for %s (attempt %d/%d): %s",
                           len(markdown), company_name, attempt + 1, MAX_RETRIES + 1, markdown[:200])
        except Exception as e:
            logger.error("[voc-analysis] API call failed for %s (attempt %d/%d): %s",
                         company_name, attempt + 1, MAX_RETRIES + 1, e)
            markdown = ""

    logger.error("[voc-analysis] All attempts returned short markdown for %s (%d chars)", company_name, len(markdown))
    return markdown


# ---------------------------------------------------------------------------
# Step 2: Parse markdown to structured JSON (Sonnet)
# ---------------------------------------------------------------------------

PARSE_SYSTEM_PROMPT = """You are a precise text-to-JSON converter. You receive a VoC Creative Strategy Analysis written in markdown and extract its content into a structured JSON schema.

Rules:
- Extract content verbatim from the markdown. Do not summarise, rephrase, or add interpretation.
- Every customer quote must be preserved exactly as written.
- If a field in the schema has no corresponding content in the markdown, use null for nullable fields or empty arrays/strings for required fields.
- The emails section: extract each email's subject line, preview text, body (split into typed sections), CTA, and strategic intent exactly as written.
- The deck_markdown field: include the full Sections 1-6 content as a single markdown string (everything except the emails).
- Output valid JSON only. No commentary."""

PARSE_USER_PROMPT = """Extract the following VoC Creative Strategy Analysis markdown into the JSON schema.

## Markdown Analysis

{markdown_content}

Extract into the required JSON schema. Preserve all verbatims, dates, and content exactly as written."""


def parse_voc_analysis_to_json(
    *,
    settings: Any,
    markdown_content: str,
) -> Dict[str, Any]:
    """Parse a markdown VoC analysis into structured JSON.

    Uses Sonnet (fast, cheap) with JSON schema enforcement.
    Returns the structured dict matching VOC_ANALYSIS_SCHEMA.
    """
    from app.services.voc_coding_chain_service import call_claude_json_schema_streaming

    user_prompt = PARSE_USER_PROMPT.replace("{markdown_content}", markdown_content)

    logger.info("[voc-parse] Parsing %d chars of markdown to JSON", len(markdown_content))

    result = call_claude_json_schema_streaming(
        settings=settings,
        model="claude-sonnet-4-5-20250929",
        system_prompt=PARSE_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        schema=VOC_ANALYSIS_SCHEMA,
        temperature=0.0,
        max_tokens=64000,
    )

    email_count = len(result.get("emails", []))
    insight_count = len(result.get("creative_strategy_insights", []))
    logger.info("[voc-parse] Extracted %d insights, %d emails", insight_count, email_count)
    return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_classification_summary(classified_reviews: List[Dict[str, Any]]) -> str:
    """Summarise classified reviews by topic with counts and top verbatims."""
    topic_data: Dict[str, Dict[str, Any]] = {}
    sentiment_counts = {"positive": 0, "negative": 0, "mixed": 0, "neutral": 0}

    for review in classified_reviews:
        sentiment = review.get("overall_sentiment", "neutral")
        sentiment_counts[sentiment] = sentiment_counts.get(sentiment, 0) + 1

        for topic in review.get("topics", []):
            cat = topic.get("category", "Unknown")
            label = topic.get("label", "Unknown")
            key = f"{cat} > {label}"
            if key not in topic_data:
                topic_data[key] = {
                    "category": cat,
                    "label": label,
                    "count": 0,
                    "sentiments": {"positive": 0, "negative": 0, "mixed": 0, "neutral": 0},
                    "sample_verbatims": [],
                }
            td = topic_data[key]
            td["count"] += 1
            s = topic.get("sentiment", "neutral")
            td["sentiments"][s] = td["sentiments"].get(s, 0) + 1
            value = review.get("value") or review.get("text", "")
            if value and len(td["sample_verbatims"]) < 5:
                td["sample_verbatims"].append(value[:300])

    total = len(classified_reviews)
    lines = [
        f"Total reviews classified: {total}",
        f"Sentiment: {sentiment_counts['positive']} positive, {sentiment_counts['negative']} negative, "
        f"{sentiment_counts['mixed']} mixed, {sentiment_counts['neutral']} neutral",
        "",
        "Top topics by frequency:",
    ]

    sorted_topics = sorted(topic_data.values(), key=lambda t: t["count"], reverse=True)
    for t in sorted_topics[:30]:
        dominant = max(t["sentiments"], key=t["sentiments"].get)
        lines.append(f"- {t['category']} > {t['label']}: {t['count']} mentions ({dominant})")
        for v in t["sample_verbatims"][:2]:
            lines.append(f'  "{v}"')

    return "\n".join(lines)
