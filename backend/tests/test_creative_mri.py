"""
Tests for Creative MRI v2: exposure proxy, aggregations, schema validation,
text analysis, batch synthesis.
"""
import json
from datetime import datetime, timezone, timedelta

import pytest

from app.services.creative_mri.exposure_proxy import (
    compute_exposure_proxy,
    enrich_ads_with_exposure,
)
from app.services.creative_mri.aggregations import compute_aggregates
from app.services.creative_mri.llm import build_user_message, parse_llm_response
from app.services.creative_mri.text_analysis import compute_reading_level
from app.services.creative_mri.synthesize import (
    build_synthesize_payload,
    parse_synthesis_response,
)


# --- Exposure proxy ---


def test_exposure_proxy_active_ad():
    """Active ad with end date: run_days from start to end."""
    ad = {
        "ad_delivery_start_time": "2024-01-01",
        "ad_delivery_end_time": "2024-01-31",
        "ads_using_creative_count": 5,
        "status": "Active",
    }
    run_days, proxy = compute_exposure_proxy(ad)
    assert run_days == 30
    assert proxy == 5 * 30 * 1.0


def test_exposure_proxy_inactive_ad():
    """Inactive ad: 0.7 multiplier."""
    ad = {
        "ad_delivery_start_time": "2024-01-01",
        "ad_delivery_end_time": "2024-01-15",
        "ads_using_creative_count": 2,
        "status": "Inactive",
    }
    run_days, proxy = compute_exposure_proxy(ad)
    assert run_days == 14
    assert proxy == 2 * 14 * 0.7


def test_exposure_proxy_no_end_uses_cutoff():
    """Ad without end uses report_end_date."""
    ad = {
        "ad_delivery_start_time": "2024-01-01",
        "ads_using_creative_count": 1,
        "status": "Active",
    }
    cutoff = datetime(2024, 2, 1, tzinfo=timezone.utc)
    run_days, proxy = compute_exposure_proxy(ad, report_end_date=cutoff)
    assert run_days == 31
    assert proxy >= 31


def test_enrich_ads_adds_run_days_and_exposure_proxy():
    """enrich_ads_with_exposure adds run_days and exposure_proxy."""
    ads = [
        {"ad_delivery_start_time": "2024-01-01", "ads_using_creative_count": 1, "status": "Active"},
    ]
    enrich_ads_with_exposure(ads)
    assert ads[0]["run_days"] >= 1
    assert ads[0]["exposure_proxy"] >= 1.0


# --- Aggregations ---


def test_compute_aggregates_empty():
    """Empty ads returns empty-style aggregates."""
    agg = compute_aggregates([])
    assert agg["distribution_raw"]["funnel"] == {}
    assert agg["dominant_hook_types"] == {}


def test_compute_aggregates_exposure_weighted():
    """Exposure-weighted funnel and hook aggregates."""
    ads = [
        {"funnel_stage": "tofu", "hook_type": "pain_agitation", "exposure_proxy": 10.0, "llm": {}},
        {"funnel_stage": "tofu", "hook_type": "direct_benefit", "exposure_proxy": 20.0, "llm": {}},
        {"funnel_stage": "mofu", "hook_type": "social_proof", "exposure_proxy": 5.0, "llm": {}},
    ]
    agg = compute_aggregates(ads)
    assert agg["distribution_exposure_weighted"]["funnel"]["tofu"] == 30 / 35
    assert agg["distribution_exposure_weighted"]["funnel"]["mofu"] == 5 / 35
    assert agg["dominant_hook_types"]["direct_benefit"] == 20.0
    assert agg["dominant_hook_types"]["pain_agitation"] == 10.0


# --- Text analysis ---


def test_compute_reading_level_simple():
    """Simple text should have low FK grade."""
    result = compute_reading_level("The cat sat on the mat. It was a good day.")
    assert result["flesch_kincaid_grade"] >= 0
    assert result["sentence_count"] == 2
    assert result["word_count"] == 11
    assert result["syllable_count"] > 0


def test_compute_reading_level_empty():
    """Empty text returns zeros."""
    result = compute_reading_level("")
    assert result["flesch_kincaid_grade"] == 0.0
    assert result["word_count"] == 0


def test_compute_reading_level_complex():
    """Complex text should have higher FK grade than simple text."""
    simple = compute_reading_level("The dog ran. It was fun.")
    complex_text = compute_reading_level(
        "The unprecedented implementation of sophisticated methodological "
        "frameworks necessitates comprehensive organizational restructuring."
    )
    assert complex_text["flesch_kincaid_grade"] > simple["flesch_kincaid_grade"]


# --- LLM Pass 1 schema validation ---


SAMPLE_V2_RESPONSE = """{
  "sentences": [
    {"text": "Tired of dry, flaky skin?", "type": "pain", "proof_detail": null},
    {"text": "Our formula uses hyaluronic acid proven in a 2023 Stanford study.", "type": "proof", "proof_detail": {"has_number": false, "has_named_source": true, "has_timeline": true, "proof_type": "case_study"}},
    {"text": "Get the glow you deserve.", "type": "benefit", "proof_detail": null}
  ],
  "belief_clusters": [
    {"core_argument": "Product hydrates skin with scientifically proven ingredients", "supporting_sentences": [0, 1, 2]}
  ],
  "close_pattern": "future_state",
  "close_text": "Get the glow you deserve.",
  "close_anti_patterns": [],
  "product_timing": {"first_mention_word_position": 8, "first_mention_pct": 0.53, "total_words": 15},
  "specificity": {"vague_terms": [], "concrete_terms": ["hyaluronic acid", "2023 Stanford study"], "vague_count": 0, "concrete_count": 2},
  "qualifier_density": {"qualifiers_found": [], "count": 0, "per_100_words": 0.0},
  "social_context_refs": [],
  "emotional_scenes": [{"text": "Get the glow you deserve", "type": "mind_movie"}],
  "conversational_markers": {"markers_found": [], "count": 0, "per_100_words": 0.0},
  "pain_benefit_balance": {"pain_pct": 0.33, "benefit_pct": 0.33, "neutral_pct": 0.34},
  "hook_type": "pain_agitation",
  "funnel_stage": "tofu",
  "flesch_kincaid": {"flesch_kincaid_grade": 4.5, "sentence_count": 3, "word_count": 15, "syllable_count": 22}
}"""


def test_parse_llm_response_v2():
    """Parse accepts v2 structured classification format."""
    out = parse_llm_response(SAMPLE_V2_RESPONSE)
    assert out is not None
    assert len(out["sentences"]) == 3
    assert out["sentences"][0]["type"] == "pain"
    assert out["sentences"][1]["type"] == "proof"
    assert out["sentences"][1]["proof_detail"]["has_named_source"] is True
    assert out["sentences"][1]["proof_detail"]["proof_type"] == "case_study"
    assert len(out["belief_clusters"]) == 1
    assert out["close_pattern"] == "future_state"
    assert out["close_text"] == "Get the glow you deserve."
    assert out["close_anti_patterns"] == []
    assert out["product_timing"]["first_mention_pct"] == 0.53
    assert out["specificity"]["concrete_count"] == 2
    assert out["qualifier_density"]["count"] == 0
    assert out["social_context_refs"] == []
    assert len(out["emotional_scenes"]) == 1
    assert out["conversational_markers"]["count"] == 0
    assert out["pain_benefit_balance"]["pain_pct"] == 0.33
    assert out["hook_type"] == "pain_agitation"
    assert out["funnel_stage"] == "tofu"
    assert out["flesch_kincaid"]["flesch_kincaid_grade"] == 4.5


def test_parse_llm_response_invalid_types_normalized():
    """Invalid enum values are normalized to defaults."""
    content = """{
      "sentences": [{"text": "test", "type": "INVALID_TYPE", "proof_detail": null}],
      "belief_clusters": [],
      "close_pattern": "invalid_pattern",
      "close_text": null,
      "close_anti_patterns": [],
      "product_timing": {"first_mention_word_position": null, "first_mention_pct": null, "total_words": 0},
      "specificity": {"vague_terms": [], "concrete_terms": [], "vague_count": 0, "concrete_count": 0},
      "qualifier_density": {"qualifiers_found": [], "count": 0, "per_100_words": 0.0},
      "social_context_refs": [],
      "emotional_scenes": [],
      "conversational_markers": {"markers_found": [], "count": 0, "per_100_words": 0.0},
      "pain_benefit_balance": {"pain_pct": 0.5, "benefit_pct": 0.5, "neutral_pct": 0.0},
      "hook_type": "NOT_A_HOOK",
      "funnel_stage": "invalid"
    }"""
    out = parse_llm_response(content)
    assert out is not None
    assert out["sentences"][0]["type"] == "neutral"  # invalid -> neutral
    assert out["close_pattern"] == "none"  # invalid -> none
    assert out["hook_type"] == "unknown"  # invalid -> unknown
    assert out["funnel_stage"] == "tofu"  # invalid -> tofu


def test_parse_llm_response_minimal():
    """Minimal response with missing fields still parses with defaults."""
    content = '{"hook_type": "direct_benefit", "funnel_stage": "tofu"}'
    out = parse_llm_response(content)
    assert out is not None
    assert out["sentences"] == []
    assert out["belief_clusters"] == []
    assert out["close_pattern"] == "none"
    assert out["qualifier_density"]["count"] == 0
    assert out["pain_benefit_balance"]["pain_pct"] == 0.33  # default split


# --- Per-ad LLM user message ---


def test_build_user_message_includes_flesch_kincaid():
    """User message includes pre-computed flesch_kincaid."""
    ad = {
        "id": "ad-1",
        "headline": "Test Headline",
        "primary_text": "Test body copy",
        "cta": "Learn More",
        "destination_url": "https://example.com",
        "flesch_kincaid": {"flesch_kincaid_grade": 5.2, "sentence_count": 2, "word_count": 10, "syllable_count": 14},
    }
    msg = build_user_message(ad)
    payload = json.loads(msg)
    assert "flesch_kincaid" in payload
    assert payload["flesch_kincaid"]["flesch_kincaid_grade"] == 5.2


def test_build_user_message_includes_video_analysis():
    """Video analysis is included when present."""
    ad = {
        "id": "ad-1",
        "headline": "Test",
        "primary_text": "Body",
        "media_items": [
            {
                "media_type": "video",
                "video_analysis_json": {
                    "transcript": "Hello and welcome.",
                    "visual_scenes": [{"start": 0, "end": 5, "description": "Person speaking"}],
                },
            },
        ],
    }
    msg = build_user_message(ad)
    payload = json.loads(msg)
    assert "video_analysis" in payload
    assert payload["video_analysis"]["transcript"] == "Hello and welcome."


# --- Batch synthesis (LLM Pass 2) ---


def test_build_synthesize_payload():
    """Synthesize payload includes per-ad classification summaries."""
    ads = [
        {
            "id": "ad-1",
            "headline": "Test Headline",
            "primary_text": "Test body copy for the ad",
            "word_count": 25,
            "llm": {
                "sentences": [
                    {"text": "test claim", "type": "claim", "proof_detail": None},
                    {"text": "proven by study", "type": "proof", "proof_detail": {"has_number": True, "has_named_source": False, "has_timeline": False, "proof_type": "statistic"}},
                ],
                "belief_clusters": [{"core_argument": "test", "supporting_sentences": [0]}],
                "close_pattern": "echo",
                "close_anti_patterns": [],
                "product_timing": {"first_mention_word_position": 5, "first_mention_pct": 0.5, "total_words": 10},
                "specificity": {"vague_terms": [], "concrete_terms": ["50%"], "vague_count": 0, "concrete_count": 1},
                "qualifier_density": {"qualifiers_found": [], "count": 0, "per_100_words": 0.0},
                "social_context_refs": [],
                "emotional_scenes": [{"text": "imagine", "type": "mind_movie"}],
                "conversational_markers": {"markers_found": [], "count": 0, "per_100_words": 0.0},
                "pain_benefit_balance": {"pain_pct": 0.5, "benefit_pct": 0.5, "neutral_pct": 0.0},
                "hook_type": "pain_agitation",
                "funnel_stage": "tofu",
                "flesch_kincaid": {"flesch_kincaid_grade": 5.0, "sentence_count": 2, "word_count": 10, "syllable_count": 15},
            },
        },
    ]
    msg = build_synthesize_payload(ads)
    payload = json.loads(msg)
    assert payload["total_ads"] == 1
    assert len(payload["ads"]) == 1
    ad_data = payload["ads"][0]
    assert ad_data["close_pattern"] == "echo"
    assert ad_data["hook_type"] == "pain_agitation"
    assert ad_data["belief_clusters"] == 1
    assert ad_data["sentence_summary"]["total"] == 2
    assert ad_data["sentence_summary"]["by_type"]["claim"] == 1
    assert ad_data["sentence_summary"]["by_type"]["proof"] == 1
    assert ad_data["proof_specificity"]["total_proofs"] == 1
    assert ad_data["proof_specificity"]["with_number"] == 1
    assert ad_data["emotional_scenes_count"] == 1
    assert ad_data["social_context_refs_count"] == 0


def test_parse_synthesis_response_valid():
    """Valid batch synthesis response parses correctly."""
    content = json.dumps({
        "dimensions": {
            "reading_level": {"score": 35, "finding": "Grade 9.2 average."},
            "claim_to_proof_ratio": {"score": 22, "finding": "11 claims, 2 proofs."},
            "proof_specificity": {"score": 18, "finding": "All proof is vague."},
            "belief_count": {"score": 60, "finding": "Average 2 beliefs per ad."},
            "product_timing": {"score": 70, "finding": "Brand appears mid-copy."},
            "specificity_score": {"score": 45, "finding": "Mix of vague and concrete."},
            "close_pattern_variety": {"score": 12, "finding": "Same close everywhere."},
            "close_anti_patterns": {"score": 90, "finding": "Clean closes."},
            "qualifier_density": {"score": 60, "finding": "4 hedges per 100 words."},
            "social_context_density": {"score": 30, "finding": "No social context."},
            "emotional_dimensionality": {"score": 25, "finding": "No mind movies."},
            "conversational_markers": {"score": 78, "finding": "Good tone."},
            "pain_benefit_balance": {"score": 55, "finding": "Balanced."},
        },
        "overall_score": 42,
        "bottom_3": [
            {"dimension": "proof_specificity", "score": 18, "finding": "All proof is vague."},
            {"dimension": "claim_to_proof_ratio", "score": 22, "finding": "11 claims, 2 proofs."},
            {"dimension": "emotional_dimensionality", "score": 25, "finding": "No mind movies."},
        ],
        "top_3": [
            {"dimension": "close_anti_patterns", "score": 90, "finding": "Clean closes."},
            {"dimension": "conversational_markers", "score": 78, "finding": "Good tone."},
            {"dimension": "product_timing", "score": 70, "finding": "Brand appears mid-copy."},
        ],
        "close_pattern_variety": {
            "patterns_used": ["direct_ask", "direct_ask"],
            "distinct_count": 1,
            "finding": "Same close everywhere.",
        },
        "executive_narrative": "Your ads lack proof and specificity.",
    })
    out = parse_synthesis_response(content)
    assert out is not None
    assert out["overall_score"] == 42
    assert out["dimensions"]["reading_level"]["score"] == 35
    assert out["dimensions"]["reading_level"]["finding"] == "Grade 9.2 average."
    assert len(out["bottom_3"]) == 3
    assert out["bottom_3"][0]["dimension"] == "proof_specificity"
    assert len(out["top_3"]) == 3
    assert out["close_pattern_variety"]["distinct_count"] == 1
    assert out["executive_narrative"] == "Your ads lack proof and specificity."


def test_parse_synthesis_response_missing_dimensions():
    """Missing dimensions get defaults."""
    content = json.dumps({
        "dimensions": {"reading_level": {"score": 50, "finding": "Average."}},
        "overall_score": 50,
    })
    out = parse_synthesis_response(content)
    assert out is not None
    assert out["dimensions"]["reading_level"]["score"] == 50
    # Missing dimensions get default score 50
    assert out["dimensions"]["claim_to_proof_ratio"]["score"] == 50
    assert out["dimensions"]["claim_to_proof_ratio"]["finding"] is None
