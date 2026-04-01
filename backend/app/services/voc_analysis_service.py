"""
VoC Creative Strategy Analysis Service.

After the lead gen pipeline completes, generates a comprehensive
creative strategy analysis from the VoC data. Produces structured
JSON for an email series + Gamma deck.
"""

import json
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


VOC_ANALYSIS_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "data_snapshot": {
            "type": "object",
            "properties": {
                "temporal_window": {"type": "string"},
                "review_count": {"type": "integer"},
                "primary_creative_lenses": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "single_biggest_gap": {"type": "string"},
            },
            "required": ["temporal_window", "review_count", "primary_creative_lenses", "single_biggest_gap"],
        },
        "headline_insight": {
            "type": "object",
            "properties": {
                "what_ads_probably_say": {"type": "string"},
                "what_customers_actually_say": {"type": "string"},
                "creative_opportunity": {"type": "string"},
                "supporting_verbatims": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"},
                            "date": {"type": "string"},
                        },
                        "required": ["text"],
                    },
                },
            },
            "required": ["what_ads_probably_say", "what_customers_actually_say", "creative_opportunity", "supporting_verbatims"],
        },
        "creative_strategy_insights": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "signal_type": {"type": "string"},
                    "finding": {"type": "string"},
                    "messaging_gap": {"type": "string"},
                    "trajectory": {"type": "string"},
                    "evidence": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "text": {"type": "string"},
                                "date": {"type": "string"},
                            },
                            "required": ["text"],
                        },
                    },
                    "creative_implications": {"type": "string"},
                    "serialisation_notes": {"type": "string"},
                },
                "required": ["title", "signal_type", "finding", "messaging_gap", "trajectory", "evidence", "creative_implications", "serialisation_notes"],
            },
        },
        "language_gold": {
            "type": "object",
            "properties": {
                "the_problem": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "verbatim": {"type": "string"},
                            "date": {"type": "string"},
                            "ad_translation": {"type": "string"},
                        },
                        "required": ["verbatim", "ad_translation"],
                    },
                },
                "the_transformation": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "verbatim": {"type": "string"},
                            "date": {"type": "string"},
                            "ad_translation": {"type": "string"},
                        },
                        "required": ["verbatim", "ad_translation"],
                    },
                },
                "the_decision": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "verbatim": {"type": "string"},
                            "date": {"type": "string"},
                            "ad_translation": {"type": "string"},
                        },
                        "required": ["verbatim", "ad_translation"],
                    },
                },
                "the_competition": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "verbatim": {"type": "string"},
                            "date": {"type": "string"},
                            "ad_translation": {"type": "string"},
                        },
                        "required": ["verbatim", "ad_translation"],
                    },
                },
                "phrases_worth_stealing": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "phrase": {"type": "string"},
                            "context": {"type": "string"},
                            "date": {"type": "string"},
                            "creative_potential": {"type": "string"},
                        },
                        "required": ["phrase", "context", "creative_potential"],
                    },
                },
            },
            "required": ["the_problem", "the_transformation", "the_decision", "the_competition", "phrases_worth_stealing"],
        },
        "objection_map": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "objection": {"type": "string"},
                    "customer_words": {"type": "string"},
                    "frequency_intensity": {"type": "string"},
                    "brand_likely_addresses": {"type": "string"},
                    "what_ad_should_say": {"type": "string"},
                },
                "required": ["objection", "customer_words", "frequency_intensity", "brand_likely_addresses", "what_ad_should_say"],
            },
        },
        "contradictions_and_complexity": {
            "type": "object",
            "properties": {
                "conflicting_signals": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "missing_voices": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "data_bias": {"type": "string"},
                "creative_risk_flags": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": ["conflicting_signals", "missing_voices", "creative_risk_flags"],
        },
        "emails": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "sequence_number": {"type": "integer"},
                    "send_day": {"type": "integer"},
                    "subject_line": {"type": "string"},
                    "preview_text": {"type": "string"},
                    "headline": {"type": "string"},
                    "body_sections": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {
                                    "type": "string",
                                    "enum": ["text", "verbatim", "stat", "cta"],
                                },
                                "content": {"type": "string"},
                                "attribution": {"type": "string"},
                            },
                            "required": ["type", "content"],
                        },
                    },
                    "cta_text": {"type": "string"},
                    "cta_url": {"type": "string"},
                    "strategic_intent": {"type": "string"},
                },
                "required": ["sequence_number", "send_day", "subject_line", "preview_text", "headline", "body_sections", "cta_text", "cta_url", "strategic_intent"],
            },
        },
        "deck_markdown": {"type": "string"},
    },
    "required": [
        "data_snapshot", "headline_insight", "creative_strategy_insights",
        "language_gold", "objection_map", "contradictions_and_complexity",
        "emails", "deck_markdown",
    ],
}


VOC_ANALYSIS_SYSTEM_PROMPT = """You are a Senior VoC Creative Strategist. You receive a company's customer review data (already categorised into a taxonomy with topics and sentiment) and produce a comprehensive creative strategy analysis.

Your output serves three purposes:
1. An executive overview and deck content for a presentation
2. A series of daily emails that deliver insights one by one, building a strategic narrative
3. Actionable creative strategy insights with verbatim evidence

## Analysis Approach

For each insight:
- Identify what the brand is probably saying in their ads vs what customers actually say
- Find the messaging gap — the most expensive disconnect between brand voice and customer voice
- Extract verbatim quotes that could become ad concepts
- Map objections and how to reframe them
- Identify "language gold" — customer phrases worth stealing for creative

## Email Series Rules

- D+0 (send_day: 0): Acknowledgement email — "Your analysis is underway" / anticipation-building
- D+1: The headline insight — the single most important finding
- D+2 through D+N: One insight per email, building a strategic narrative
- Final email: Includes link to full deck and CTA to view visualisation
- Each email should stand alone as valuable but also build on previous emails
- The number of emails depends on how many significant insights the data yields (typically 5-10)
- cta_url should use {{MAGIC_LINK_URL}} for app links or {{GAMMA_DECK_URL}} for the deck

## Email Content Structure

Each email has body_sections — an array of content blocks:
- "text": Narrative prose (the analysis, interpretation, strategic advice)
- "verbatim": A customer quote with attribution
- "stat": A data point or metric (e.g., "67% of reviews mention...")
- "cta": A call-to-action block

## Deck Markdown

Produce clean markdown suitable for Gamma API deck generation:
- H1: Company name — VoC Creative Strategy
- H2 sections: Executive Overview, Theme Analysis, Creative Insights, Language Gold, Objection Map
- Use tables, bullet points, and blockquotes for verbatims
- Keep it scannable — executives will read this in 5 minutes

## Tone

- Expert but accessible — like a strategist presenting to a CMO
- Data-driven — every claim backed by specific verbatims
- Actionable — each insight ends with what to do about it
- Warm but direct — no filler, no hedging, no "it might be worth considering"
"""


VOC_ANALYSIS_USER_PROMPT = """Analyze the following Voice of Customer data for {company_name} ({company_url}) and produce a complete creative strategy analysis.

## Business Context
{context_text}

## Validated Taxonomy (categories and topics from customer reviews)
{taxonomy_json}

## Review Classification Summary
{classification_summary}

## Ad Topics Generated
The following themes were selected for ad generation: {ad_topics}

Produce the full analysis following the schema. Include as many insights as the data warrants — don't pad, don't truncate. Let the data dictate the email count."""


def generate_voc_analysis(
    *,
    settings: Any,
    company_name: str,
    company_url: str,
    context_text: str,
    validate_output: Dict[str, Any],
    classified_reviews: List[Dict[str, Any]],
    ad_topics: List[str],
) -> Dict[str, Any]:
    """Generate a full VoC creative strategy analysis from pipeline outputs.

    Returns structured JSON matching VOC_ANALYSIS_SCHEMA.
    """
    from app.services.voc_coding_chain_service import call_claude_json_schema_streaming

    # Build classification summary (grouped by topic with counts + top verbatims)
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
        "[voc-analysis] Generating for %s (taxonomy: %d categories, %d classified reviews)",
        company_name,
        len(validate_output.get("categories", [])),
        len(classified_reviews),
    )

    result = call_claude_json_schema_streaming(
        settings=settings,
        model="claude-opus-4-6",
        system_prompt=VOC_ANALYSIS_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        schema=VOC_ANALYSIS_SCHEMA,
        temperature=0.5,
        max_tokens=64000,
    )

    email_count = len(result.get("emails", []))
    insight_count = len(result.get("creative_strategy_insights", []))
    logger.info(
        "[voc-analysis] Generated %d insights, %d emails for %s",
        insight_count, email_count, company_name,
    )
    return result


def _build_classification_summary(classified_reviews: List[Dict[str, Any]]) -> str:
    """Summarise classified reviews by topic with counts and top verbatims.

    Avoids sending all 200+ raw reviews to the analysis prompt.
    """
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
            # Keep up to 5 sample verbatims per topic
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
