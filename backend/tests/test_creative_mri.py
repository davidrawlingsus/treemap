"""
Tests for Creative MRI: exposure proxy, aggregations, schema validation.
"""
from datetime import datetime, timezone, timedelta

import pytest

from app.services.creative_mri.exposure_proxy import (
    compute_exposure_proxy,
    enrich_ads_with_exposure,
)
from app.services.creative_mri.aggregations import compute_aggregates
from app.services.creative_mri.llm import parse_llm_response


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
    assert agg["claim_proof_mismatch_rate"] == 0.0


def test_compute_aggregates_exposure_weighted():
    """Exposure-weighted funnel and hook aggregates."""
    ads = [
        {"funnel_stage": "tofu", "hook_type": "pain_agitation", "exposure_proxy": 10.0, "llm": {"hook_scores": {"overall": 70, "credibility": 60}}},
        {"funnel_stage": "tofu", "hook_type": "direct_benefit", "exposure_proxy": 20.0, "llm": {"hook_scores": {"overall": 50, "credibility": 50}}},
        {"funnel_stage": "mofu", "hook_type": "social_proof", "exposure_proxy": 5.0, "llm": {"hook_scores": {"overall": 80, "credibility": 70}, "mofu_job_type": "consideration"}},
    ]
    agg = compute_aggregates(ads)
    assert agg["distribution_exposure_weighted"]["funnel"]["tofu"] == 30 / 35
    assert agg["distribution_exposure_weighted"]["funnel"]["mofu"] == 5 / 35
    assert agg["dominant_hook_types"]["direct_benefit"] == 20.0
    assert agg["dominant_hook_types"]["pain_agitation"] == 10.0
    assert agg["mofu_job_split_exposure_weighted"]["consideration"] == 1.0


def test_claim_proof_mismatch_rate():
    """Mismatch rate only counts medium/high."""
    ads = [
        {"exposure_proxy": 10.0, "llm": {"claim_audit": {"claim_proof_mismatch": "high"}}},
        {"exposure_proxy": 10.0, "llm": {"claim_audit": {"claim_proof_mismatch": "low"}}},
    ]
    agg = compute_aggregates(ads)
    assert agg["claim_proof_mismatch_rate"] == 0.5


# --- Schema validation ---


def test_parse_llm_response_new_fields():
    """Parse accepts mofu_job_type, replace_vs_refine, claim_audit, video_first_2s."""
    content = """{
      "hook_type": "pain_agitation",
      "funnel_stage": "mofu",
      "mofu_job_type": "consideration",
      "replace_vs_refine": {"decision": "refine", "rationale": "Hook can be improved"},
      "claim_audit": {"claim_proof_mismatch": "medium", "top_risks": ["Unsupported efficacy claim"]},
      "video_first_2s": {"applicable": true, "hook_present": true, "quality": "strong"},
      "hook_scores": {"overall": 65, "clarity": 70, "specificity": 60, "novelty": 50, "emotional_pull": 70, "pattern_interrupt": 40, "audience_specificity": 55, "credibility": 60}
    }"""
    out = parse_llm_response(content)
    assert out is not None
    assert out["mofu_job_type"] == "consideration"
    assert out["replace_vs_refine"]["decision"] == "refine"
    assert out["claim_audit"]["claim_proof_mismatch"] == "medium"
    assert out["claim_audit"]["top_risks"] == ["Unsupported efficacy claim"]
    assert out["video_first_2s"]["applicable"] is True
    assert out["video_first_2s"]["quality"] == "strong"


def test_parse_llm_response_invalid_enum_normalized():
    """Invalid enum values are normalized to unknown/not_applicable."""
    content = """{
      "hook_type": "pain_agitation",
      "funnel_stage": "tofu",
      "mofu_job_type": "invalid_type",
      "replace_vs_refine": {"decision": "invalid"},
      "video_first_2s": {"applicable": true, "quality": "invalid"},
      "hook_scores": {"overall": 50, "clarity": 50, "specificity": 50, "novelty": 50, "emotional_pull": 50, "pattern_interrupt": 50, "audience_specificity": 50, "credibility": 50}
    }"""
    out = parse_llm_response(content)
    assert out is not None
    assert out["mofu_job_type"] == "unknown"
    assert out["replace_vs_refine"]["decision"] == "unknown"
    assert out["video_first_2s"]["quality"] == "unknown"


def test_parse_llm_response_backward_compat():
    """Old response without new fields still parses."""
    content = """{
      "hook_type": "direct_benefit",
      "funnel_stage": "tofu",
      "hook_scores": {"overall": 60, "clarity": 60, "specificity": 60, "novelty": 50, "emotional_pull": 60, "pattern_interrupt": 50, "audience_specificity": 55, "credibility": 55}
    }"""
    out = parse_llm_response(content)
    assert out is not None
    assert out["mofu_job_type"] == "not_applicable"
    assert out["replace_vs_refine"]["decision"] == "unknown"
    assert out["claim_audit"]["top_risks"] == []
    assert out["video_first_2s"]["applicable"] is False
