"""
Creative MRI v2 pipeline: ingest → FK pre-pass → LLM Pass 1 per-ad → LLM Pass 2 batch synthesis → aggregate.
Outputs analysis bundle (schema 2.0.0) for dashboard charts.  # deploy-trigger-001

Pass 1: Per-ad structured classification (sentences, belief clusters, close patterns, etc.)
Pass 2: Batch synthesis (13 dimension scores, findings, bottom-3, executive narrative)
"""
import json
import logging
import uuid
from datetime import datetime, timezone
import re
from typing import Any, Callable, Dict, List, Optional

from app.services.creative_mri.analysis_schema import (
    DIMENSION_LABELS,
    DIMENSION_NAMES,
    DIMENSION_WEIGHTS,
    SCHEMA_VERSION,
    build_taxonomy,
)
from app.services.creative_mri.exposure_proxy import enrich_ads_with_exposure
from app.services.creative_mri.aggregations import compute_aggregates
from app.services.creative_mri.llm import call_creative_mri_llm
from app.services.creative_mri.text_analysis import compute_reading_level
from app.services.creative_mri.synthesize import run_batch_synthesis

logger = logging.getLogger(__name__)

MIN_WORD_COUNT = 5


def _normalize_text(text: Optional[str]) -> str:
    """Trim, collapse whitespace, strip non-printable."""
    if not text:
        return ""
    s = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", (text or "").strip())
    return " ".join(re.split(r"\s+", s)).strip()


def _word_count(text: str) -> int:
    """Tokenize and count words (letters/numbers)."""
    tokens = re.findall(r"[a-zA-Z0-9]+", (text or "").lower())
    return len(tokens)


def ingest_ads(ads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalize ads: full_text, word_count; skip empty; dedupe by (headline + first 100 of primary)."""
    seen = set()
    out = []
    for ad in ads:
        headline = _normalize_text(ad.get("headline"))
        primary = _normalize_text(ad.get("primary_text"))
        full_text = f"{headline}\n{primary}".strip()
        wc = _word_count(full_text)
        if wc < MIN_WORD_COUNT:
            continue
        key = (headline[:80], primary[:100])
        if key in seen:
            continue
        seen.add(key)
        normalized = {
            "id": str(ad.get("id", "")),
            "library_id": ad.get("library_id"),
            "headline": headline,
            "primary_text": primary,
            "full_text": full_text,
            "word_count": wc,
            "cta": _normalize_text(ad.get("cta")) or None,
            "destination_url": (ad.get("destination_url") or "").strip() or None,
            "ad_format": (ad.get("ad_format") or "").strip() or None,
            "started_running_on": ad.get("started_running_on"),
            "ad_delivery_start_time": ad.get("ad_delivery_start_time"),
            "ad_delivery_end_time": ad.get("ad_delivery_end_time"),
            "media_thumbnail_url": (ad.get("media_thumbnail_url") or "").strip() or None,
            "platforms": ad.get("platforms"),
            "media_items": ad.get("media_items"),
            "ads_using_creative_count": ad.get("ads_using_creative_count"),
            "status": ad.get("status"),
        }
        out.append(normalized)
    return out


def _default_llm_output() -> Dict[str, Any]:
    """Default LLM Pass 1 classification when the call fails."""
    return {
        "sentences": [],
        "belief_clusters": [],
        "close_pattern": "none",
        "close_text": None,
        "close_anti_patterns": [],
        "product_timing": {"first_mention_word_position": None, "first_mention_pct": None, "total_words": 0},
        "specificity": {"vague_terms": [], "concrete_terms": [], "vague_count": 0, "concrete_count": 0},
        "qualifier_density": {"qualifiers_found": [], "count": 0, "per_100_words": 0.0},
        "social_context_refs": [],
        "emotional_scenes": [],
        "conversational_markers": {"markers_found": [], "count": 0, "per_100_words": 0.0},
        "pain_benefit_balance": {"pain_pct": 0.33, "benefit_pct": 0.33, "neutral_pct": 0.34},
        "hook_type": "unknown",
        "funnel_stage": "tofu",
        "flesch_kincaid": {"flesch_kincaid_grade": 0.0, "sentence_count": 0, "word_count": 0, "syllable_count": 0},
    }


def llm_pass(
    ads: List[Dict[str, Any]],
    llm_service: Any,
    progress_callback: Optional[Callable[[str, int, int, str], None]] = None,
    system_message: Optional[str] = None,
    model: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    LLM Pass 1: Compute Flesch-Kincaid, then call Claude per-ad for structured classification.
    """
    n = len(ads)
    for i, ad in enumerate(ads):
        if progress_callback:
            progress_callback("llm", i + 1, n, f"Analyzing ad copy {i + 1}/{n}")

        # Pre-compute Flesch-Kincaid (only Python metric)
        fk = compute_reading_level(ad.get("full_text", ""))
        ad["flesch_kincaid"] = fk

        # Call LLM Pass 1
        llm_out = call_creative_mri_llm(llm_service, ad, system_message=system_message, model=model)
        if not llm_out:
            llm_out = _default_llm_output()
            llm_out["flesch_kincaid"] = fk

        ad["llm"] = llm_out
        ad["hook_type"] = llm_out.get("hook_type") or "unknown"
        ad["funnel_stage"] = (llm_out.get("funnel_stage") or "tofu").lower()
        # overall_score will come from batch synthesis; set placeholder
        ad["overall_score"] = 50

    return ads


def _default_batch_synthesis(ads: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Fallback batch synthesis when LLM Pass 2 fails."""
    return {
        "dimensions": {name: {"score": 50, "finding": None} for name in DIMENSION_NAMES},
        "overall_score": 50,
        "bottom_3": [],
        "top_3": [],
        "close_pattern_variety": {"patterns_used": [], "distinct_count": 0, "finding": None},
        "executive_narrative": None,
    }


def _build_dataset_summary(
    analysis_ads: List[Dict], n: int, overall_score: int,
) -> Dict[str, Any]:
    """Build dataset_summary from analysis_ads."""
    format_counts: Dict[str, int] = {}
    funnel_counts = {"tofu": 0, "mofu": 0, "bofu": 0}
    hook_counts: Dict[str, int] = {}
    for a in analysis_ads:
        fmt = (a.get("labels") or {}).get("format") or "unknown"
        format_counts[fmt] = format_counts.get(fmt, 0) + 1
        stage = (a.get("funnel") or {}).get("stage") or "tofu"
        funnel_counts[stage] = funnel_counts.get(stage, 0) + 1
        ht = ((a.get("hook") or {}).get("hook_types") or [{}])[0]
        htype = ht.get("type") or "unknown"
        hook_counts[htype] = hook_counts.get(htype, 0) + 1
    format_share = {k: round(v / n, 3) for k, v in format_counts.items()} if n else {}
    funnel_share = {k: round(v / n, 3) for k, v in funnel_counts.items()} if n else {"tofu": 0.33, "mofu": 0.33, "bofu": 0.34}
    hook_share = {k: round(v / n, 3) for k, v in hook_counts.items()} if n else {}
    return {
        "counts": {"ads_total": n, "creatives_total": n, "active_ads": n, "active_creatives": n},
        "mix": {"format_share": format_share, "platform_share": {}},
        "funnel": {"stage_share": funnel_share},
        "hook": {"type_share": hook_share},
    }


def aggregate(
    ads: List[Dict[str, Any]],
    batch_synthesis: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build report: executive summary from batch synthesis, tear-down from per-ad data, analysis bundle for charts."""
    if not ads:
        return {
            "meta": {"total_ads": 0, "schema_version": SCHEMA_VERSION, "label": "copy-based effectiveness diagnostics"},
            "executive_summary": {
                "overall_effectiveness_score": 0,
                "subscores_summary": [],
                "top_strengths": [],
                "top_leaks": [],
                "fast_wins": [],
            },
            "batch_synthesis": _default_batch_synthesis([]),
            "ads": [],
            "tear_down": {"selected_ads": []},
            "analysis": {
                "schema_version": SCHEMA_VERSION,
                "run": {"run_id": str(uuid.uuid4()), "created_at_utc": datetime.now(timezone.utc).isoformat()},
                "taxonomy": build_taxonomy(),
                "analysis": {"ads": [], "dataset_summary": {}},
            },
        }

    n = len(ads)
    synth = batch_synthesis or _default_batch_synthesis(ads)
    overall_score = synth.get("overall_score", 50)

    # Apply overall_score from synthesis back to ads (for tear-down sorting)
    # Per-ad scores aren't available from synthesis — use placeholder 50
    # (The synthesis scores the batch, not individual ads)

    # Build subscores_summary from synthesis dimensions (for frontend backward compat)
    dimensions = synth.get("dimensions") or {}
    subscores_summary = []
    for name in DIMENSION_NAMES:
        d = dimensions.get(name, {})
        subscores_summary.append({
            "name": name,
            "label": DIMENSION_LABELS.get(name, name),
            "average": d.get("score", 50),
            "weight": DIMENSION_WEIGHTS.get(name, 0),
            "finding": d.get("finding"),
        })

    # Top strengths from synthesis top_3
    top_strengths = []
    for item in synth.get("top_3", []):
        top_strengths.append({
            "dimension": item.get("dimension"),
            "label": DIMENSION_LABELS.get(item.get("dimension", ""), ""),
            "score": item.get("score", 50),
            "finding": item.get("finding"),
        })

    # Top leaks from synthesis bottom_3
    top_leaks = []
    for item in synth.get("bottom_3", []):
        top_leaks.append({
            "dimension": item.get("dimension"),
            "label": DIMENSION_LABELS.get(item.get("dimension", ""), ""),
            "score": item.get("score", 50),
            "finding": item.get("finding"),
        })

    # Fast wins = bottom-3 findings
    fast_wins = [item.get("finding") for item in synth.get("bottom_3", []) if item.get("finding")]
    if not fast_wins:
        fast_wins = ["Review and improve copy based on low-scoring dimensions above."]

    # Tear-down: select representative ads (no per-ad scoring, use word_count as proxy for variety)
    sorted_ads = sorted(ads, key=lambda a: a.get("word_count", 0), reverse=True)
    best = sorted_ads[:2] if len(sorted_ads) >= 2 else sorted_ads[:1]
    mid_start = max(1, len(sorted_ads) // 2 - 1)
    mid_end = mid_start + 2
    average = sorted_ads[mid_start:mid_end]
    worst = sorted_ads[-2:] if len(sorted_ads) >= 2 else sorted_ads[-1:]
    selected = best + average + worst

    # Build analysis bundle for D3 charts
    analysis_ads = []
    for a in ads:
        llm = a.get("llm") or {}
        stage = (llm.get("funnel_stage") or a.get("funnel_stage") or "tofu").lower()
        analysis_ads.append({
            "ad_id": a.get("id"),
            "library_id": a.get("library_id"),
            "started_running_on": a.get("started_running_on"),
            "ad_delivery_start_time": a.get("ad_delivery_start_time"),
            "ad_delivery_end_time": a.get("ad_delivery_end_time"),
            "meta_context": {
                "exposure_proxy": a.get("exposure_proxy", 1.0),
                "run_days": a.get("run_days", 1),
            },
            "labels": {
                "format": (a.get("ad_format") or "unknown").lower(),
                "platforms": a.get("platforms") or [],
                "cta_text": a.get("cta"),
                "destination_url": a.get("destination_url"),
            },
            "hook": {
                "hook_text": (llm.get("close_text") or ""),
                "hook_types": [{"type": llm.get("hook_type") or "unknown", "weight": 1.0}],
            },
            "funnel": {"stage": stage},
            "classification": llm,
        })

    run_id = str(uuid.uuid4())
    analysis = {
        "schema_version": SCHEMA_VERSION,
        "run": {
            "run_id": run_id,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "model": "claude-3-5-sonnet",
            "temperature": 0.3,
        },
        "taxonomy": build_taxonomy(),
        "analysis": {
            "ads": analysis_ads,
            "dataset_summary": _build_dataset_summary(analysis_ads, n, overall_score),
            "exposure_weighted_aggregates": compute_aggregates(ads),
        },
    }

    return {
        "meta": {"total_ads": n, "schema_version": SCHEMA_VERSION, "label": "copy-based effectiveness diagnostics"},
        "executive_summary": {
            "overall_effectiveness_score": overall_score,
            "subscores_summary": subscores_summary,
            "top_strengths": top_strengths,
            "top_leaks": top_leaks,
            "fast_wins": fast_wins,
        },
        "batch_synthesis": synth,
        "ads": ads,
        "tear_down": {"selected_ads": selected},
        "analysis": analysis,
    }


def run_creative_mri_pipeline(
    ads: List[Dict[str, Any]],
    llm_service: Any,
    progress_callback: Optional[Callable[[str, int, int, str], None]] = None,
    system_message: Optional[str] = None,
    model: Optional[str] = None,
    db: Any = None,
) -> Dict[str, Any]:
    """
    Run full v2 pipeline:
    1. Ingest & normalize
    2. Exposure proxy enrichment
    3. LLM Pass 1: per-ad structured classification (with FK pre-computation)
    4. LLM Pass 2: batch synthesis (13 dimensions, scores, findings)
    5. Aggregate into report

    progress_callback(stage, current, total, message) called during processing.
    system_message and model from Prompt Engineering when configured; else built-in prompts.
    db: optional SQLAlchemy session for Prompt Engineering lookup on Pass 2.
    """
    normalized = ingest_ads(ads)
    if not normalized:
        return aggregate([])

    enrich_ads_with_exposure(normalized)

    # LLM Pass 1: per-ad classification
    llm_pass(
        normalized,
        llm_service,
        progress_callback=progress_callback,
        system_message=system_message,
        model=model,
    )

    # LLM Pass 2: batch synthesis
    logger.warning("[MRI-DEBUG] Pass 1 complete for %d ads. Starting batch synthesis. db=%s", len(normalized), type(db).__name__ if db else "None")
    if progress_callback:
        progress_callback("synthesis", 0, 1, "Synthesizing batch analysis across all ads")

    batch_synthesis = run_batch_synthesis(normalized, llm_service, db=db)
    logger.warning("[MRI-DEBUG] Batch synthesis result: %s", "SUCCESS" if batch_synthesis else "NONE (fallback to defaults)")
    if batch_synthesis:
        logger.warning("[MRI-DEBUG] Synthesis overall_score=%s, bottom_3=%d, top_3=%d, dims=%s",
                    batch_synthesis.get("overall_score"),
                    len(batch_synthesis.get("bottom_3", [])),
                    len(batch_synthesis.get("top_3", [])),
                    list(batch_synthesis.get("dimensions", {}).keys())[:5])

    if progress_callback:
        progress_callback("synthesis", 1, 1, "Synthesis complete")

    return aggregate(normalized, batch_synthesis=batch_synthesis)
