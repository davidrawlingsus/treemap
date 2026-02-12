"""
Creative MRI pipeline: ingest → LLM per-ad → aggregate.
Outputs analysis bundle (schema 1.0.0) for dashboard charts.
All classification and scoring comes from the LLM.
"""
import json
import re
import time
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

# #region agent log
import os as _diag_os
_DEBUG_LOG_DIR = _diag_os.path.join(_diag_os.path.dirname(__file__), "..", "..", "..", "..", ".cursor")
_DEBUG_LOG = _diag_os.path.join(_DEBUG_LOG_DIR, "debug.log")
def _diag(msg: str, data: dict = None, hyp: str = None):
    try:
        _diag_os.makedirs(_DEBUG_LOG_DIR, exist_ok=True)
        with open(_DEBUG_LOG, "a") as f:
            f.write(json.dumps({"location": "pipeline.py", "message": msg, "data": data or {}, "timestamp": int(time.time() * 1000), "hypothesisId": hyp}) + "\n")
    except Exception:
        pass
# #endregion

from app.services.creative_mri.analysis_schema import (
    SCHEMA_VERSION,
    build_taxonomy,
)
from app.services.creative_mri.exposure_proxy import enrich_ads_with_exposure
from app.services.creative_mri.aggregations import compute_aggregates
from app.services.creative_mri.llm import call_creative_mri_llm

logger = logging.getLogger(__name__)

MIN_WORD_COUNT = 5

# Map LLM hook_scores (0-100) to executive summary subscores
HOOK_SCORE_KEYS = ("clarity", "specificity", "novelty", "emotional_pull", "pattern_interrupt", "audience_specificity", "credibility", "overall")


def _subscores_from_llm(hook_scores: Dict[str, float]) -> Dict[str, float]:
    """Derive 5 subscores from LLM hook_scores (0-100)."""
    hs = dict(hook_scores or {})
    for k in HOOK_SCORE_KEYS:
        if k not in hs or not isinstance(hs.get(k), (int, float)):
            hs[k] = 50
        else:
            hs[k] = max(0, min(100, float(hs[k])))
    return {
        "hook": hs.get("overall", 50),
        "clarity_specificity": (hs.get("clarity", 50) + hs.get("specificity", 50)) / 2,
        "proof_strength": hs.get("credibility", 50),
        "differentiation_mechanism": (hs.get("novelty", 50) + hs.get("pattern_interrupt", 50)) / 2,
        "conversion_readiness": (hs.get("emotional_pull", 50) + hs.get("audience_specificity", 50)) / 2,
    }


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


def llm_pass(
    ads: List[Dict[str, Any]],
    llm_service: Any,
    progress_callback: Optional[Callable[[str, int, int, str], None]] = None,
    system_message: Optional[str] = None,
    model: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Call Claude per-ad; merge llm fields into each ad. Classification and scoring come from LLM."""
    n = len(ads)
    # #region agent log
    _diag("llm_pass_start", {"ad_count": n}, "H4")
    # #endregion
    for i, ad in enumerate(ads):
        if progress_callback:
            progress_callback("llm", i + 1, n, f"Analyzing ad copy {i + 1}/{n}")
        # #region agent log
        _diag("llm_pass_before_call", {"ad_index": i + 1, "total": n}, "H4")
        # #endregion
        llm_out = call_creative_mri_llm(llm_service, ad, system_message=system_message, model=model)
        # #region agent log
        _diag("llm_pass_after_call", {"ad_index": i + 1, "total": n}, "H4")
        # #endregion
        if not llm_out:
            ad["llm"] = None
            ad["hook_type"] = "unknown"
            ad["funnel_stage"] = "tofu"
            ad["overall_score"] = 50
            ad["subscores"] = {k: 50 for k in ("hook", "clarity_specificity", "proof_strength", "differentiation_mechanism", "conversion_readiness")}
            ad["mofu_job_type"] = "not_applicable"
            ad["replace_vs_refine"] = {"decision": "unknown"}
            ad["claim_audit"] = {}
            ad["video_first_2s"] = {"applicable": False}
            continue
        ad["llm"] = {
            "hook_type": llm_out.get("hook_type"),
            "hook_phrase": llm_out.get("hook_phrase"),
            "secondary_hook": llm_out.get("secondary_hook"),
            "angle": llm_out.get("angle"),
            "funnel_stage": llm_out.get("funnel_stage"),
            "stage_rationale": llm_out.get("stage_rationale") or [],
            "proof_claimed": llm_out.get("proof_claimed") or [],
            "proof_shown": llm_out.get("proof_shown") or [],
            "proof_gap": llm_out.get("proof_gap") or [],
            "objections_addressed": llm_out.get("objections_addressed") or [],
            "objections_unaddressed": llm_out.get("objections_unaddressed") or [],
            "offer_present": llm_out.get("offer_present"),
            "offer_types": llm_out.get("offer_types") or [],
            "hook_scores": llm_out.get("hook_scores") or {},
            "cta_type": llm_out.get("cta_type"),
            "destination_type": llm_out.get("destination_type"),
            "unsupported_claims": llm_out.get("unsupported_claims") or [],
            "what_to_change": llm_out.get("what_to_change") or [],
            "mofu_job_type": llm_out.get("mofu_job_type"),
            "replace_vs_refine": llm_out.get("replace_vs_refine") or {},
            "claim_audit": llm_out.get("claim_audit") or {},
            "video_first_2s": llm_out.get("video_first_2s") or {},
        }
        ad["hook_type"] = llm_out.get("hook_type") or "unknown"
        ad["funnel_stage"] = (llm_out.get("funnel_stage") or "tofu").lower()
        ad["angle"] = llm_out.get("angle")
        ad["hook_phrase"] = llm_out.get("hook_phrase")
        subscores = _subscores_from_llm(llm_out.get("hook_scores"))
        ad["subscores"] = subscores
        hs = llm_out.get("hook_scores") or {}
        overall = hs.get("overall") if isinstance(hs, dict) else None
        ad["overall_score"] = max(0, min(100, float(overall))) if isinstance(overall, (int, float)) else 50
    # #region agent log
    _diag("llm_pass_end", {"ad_count": n}, "H4")
    # #endregion
    return ads


def _build_dataset_summary(
    analysis_ads: List[Dict], n: int, overall_avg: float
) -> Dict[str, Any]:
    """Build dataset_summary from analysis_ads."""
    format_counts = {}
    funnel_counts = {"tofu": 0, "mofu": 0, "bofu": 0}
    hook_counts = {}
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
        "funnel": {"stage_share": funnel_share, "gap_notes": []},
        "hook": {"type_share": hook_share, "avg_scores": {}},
        "proof": {"avg_density_score_0_100": round(overall_avg, 1), "type_share": {}, "top_missing_proof": []},
        "objections": {"coverage_share": {}, "top_unaddressed": []},
        "opportunities": [],
    }


def aggregate(ads: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build report summary: overall score, subscores summary, top strengths/leaks, fast_wins, tear_down."""
    if not ads:
        return {
            "meta": {"total_ads": 0, "label": "copy-based effectiveness diagnostics"},
            "executive_summary": {
                "overall_effectiveness_score": 0,
                "subscores_summary": [],
                "top_strengths": [],
                "top_leaks": [],
                "fast_wins": [],
            },
            "ads": [],
            "tear_down": {"selected_ads": []},
            "analysis": {
                "schema_version": SCHEMA_VERSION,
                "run": {"run_id": str(uuid.uuid4()), "created_at_utc": datetime.now(timezone.utc).isoformat()},
                "taxonomy": build_taxonomy(),
                "analysis": {"ads": [], "redundancy": {"clusters": [], "summary": {}}, "dataset_summary": {}},
            },
        }

    n = len(ads)
    overall_avg = sum(a.get("overall_score", 0) for a in ads) / n
    sub_names = ["hook", "clarity_specificity", "proof_strength", "differentiation_mechanism", "conversion_readiness"]
    sub_avgs = []
    for name in sub_names:
        avg = sum((a.get("subscores") or {}).get(name, 0) for a in ads) / n
        sub_avgs.append({"name": name, "average": round(avg, 2)})

    # Top 3 strengths: subscores with highest avg; pick one ad each
    sorted_subs = sorted(enumerate(sub_avgs), key=lambda x: -x[1]["average"])
    top_strengths = []
    for idx, (_, s) in enumerate(sorted_subs[:3]):
        name = s["name"]
        best_ad = max(ads, key=lambda a: (a.get("subscores") or {}).get(name, 0))
        top_strengths.append({
            "subscore": name,
            "average": s["average"],
            "ad_id": best_ad.get("id"),
            "headline": (best_ad.get("headline") or "")[:80],
        })

    # Top 3 leaks: lowest subscores
    top_leaks = []
    for idx, (_, s) in enumerate(sorted_subs[-3:][::-1]):
        name = s["name"]
        worst_ad = min(ads, key=lambda a: (a.get("subscores") or {}).get(name, 0))
        top_leaks.append({
            "subscore": name,
            "average": s["average"],
            "ad_id": worst_ad.get("id"),
            "headline": (worst_ad.get("headline") or "")[:80],
        })

    # by_score: descending (best first) for tear-down
    by_score = sorted(ads, key=lambda a: -(a.get("overall_score") or 0))

    # Fast wins: from LLM what_to_change on worst-performing ads
    worst_ads = list(reversed(by_score))[: min(5, len(by_score))]
    fast_wins_seen = set()
    fast_wins = []
    for a in worst_ads:
        for item in (a.get("llm") or {}).get("what_to_change") or []:
            if item and item not in fast_wins_seen:
                fast_wins_seen.add(item)
                fast_wins.append(item)
                if len(fast_wins) >= 5:
                    break
        if len(fast_wins) >= 5:
            break
    if not fast_wins:
        fast_wins = ["Review and improve copy based on low-scoring areas above."]

    # Tear-down: 2 best, 2 average, 2 weakest by overall_score
    best = by_score[:2] if len(by_score) >= 2 else by_score[:1]
    mid_start = max(1, len(by_score) // 2 - 1)
    mid_end = mid_start + 2
    average = by_score[mid_start:mid_end]
    worst = by_score[-2:] if len(by_score) >= 2 else by_score[-1:]
    selected = best + average + worst
    for a in selected:
        a["what_to_change"] = (a.get("llm") or {}).get("what_to_change") or []

    # Build analysis bundle for dashboard (creative-llm-analysis.bundle schema)
    def _normalize_hook_scores(hs: dict) -> dict:
        out = {}
        for k in HOOK_SCORE_KEYS:
            v = hs.get(k) if isinstance(hs, dict) else None
            out[k] = v if isinstance(v, (int, float)) else 50
        return out

    analysis_ads = []
    for a in ads:
        llm = a.get("llm") or {}
        stage = (llm.get("funnel_stage") or a.get("funnel_stage") or "tofu").lower()
        funnel_obj = {
            "stage": stage,
            "stage_confidence": 0.8,
            "stage_rationale": llm.get("stage_rationale") or [],
            "substage_tags": [],
        }
        if stage == "mofu":
            funnel_obj["mofu_job_type"] = llm.get("mofu_job_type") or "unknown"
        hook_scores = _normalize_hook_scores(llm.get("hook_scores") or {})
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
                "cta_type": llm.get("cta_type"),
                "destination_url": a.get("destination_url"),
                "destination_type": llm.get("destination_type"),
            },
            "hook": {
                "hook_text": llm.get("hook_phrase") or "",
                "hook_position": "primary_text_opening",
                "hook_types": [{"type": llm.get("hook_type") or "unknown", "weight": 1.0}],
                "scores": hook_scores,
                "rationale": llm.get("stage_rationale") or [],
            },
            "funnel": funnel_obj,
            "proof": {
                "proof_claimed": llm.get("proof_claimed") or [],
                "proof_shown": llm.get("proof_shown") or [],
                "proof_gap": llm.get("proof_gap") or [],
                "proof_density": {"per_100_words": 0, "score_0_100": (a.get("subscores") or {}).get("proof_strength", 0)},
                "claims": [],
            },
            "objections": {
                "addressed": llm.get("objections_addressed") or [],
                "unaddressed": llm.get("objections_unaddressed") or [],
                "coverage_score_0_100": 50,
            },
            "offer": {
                "offer_present": llm.get("offer_present", False),
                "offer_types": llm.get("offer_types") or [],
                "urgency_present": False,
                "risk_reversal_present": False,
                "clarity_score_0_100": (a.get("subscores") or {}).get("conversion_readiness", 0),
                "extracted": {"raw_text_spans": []},
            },
            "scores": {
                "expected_performance_0_100": a.get("overall_score", 0),
                "value_force_0_100": (a.get("subscores") or {}).get("proof_strength", 0),
                "cost_force_0_100": 50,
                "fatigue_risk_0_100": 50,
                "improvement_bandwidth_0_100": 50,
            },
            "evidence": {"spans": []},
            "replace_vs_refine": llm.get("replace_vs_refine") or {},
            "claim_audit": llm.get("claim_audit") or {},
            "video_first_2s": llm.get("video_first_2s") or {"applicable": False},
        })

    run_id = str(uuid.uuid4())
    analysis = {
        "schema_version": SCHEMA_VERSION,
        "run": {
            "run_id": run_id,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "model": "claude-3-5-sonnet",
            "temperature": 0.3,
            "inputs_digest": {"hash_algo": "sha256", "hash": "pending"},
        },
        "taxonomy": build_taxonomy(),
        "analysis": {
            "ads": analysis_ads,
            "redundancy": {
                "method": {"embedding_model": "none", "similarity_metric": "cosine", "threshold": 0.9},
                "clusters": [],
                "summary": {
                    "unique_ratio_headlines": 1.0,
                    "unique_ratio_hooks": 1.0,
                    "redundancy_risk_0_100": 0,
                },
            },
            "dataset_summary": _build_dataset_summary(analysis_ads, n, overall_avg),
            "exposure_weighted_aggregates": compute_aggregates(ads),
        },
    }

    return {
        "meta": {"total_ads": n, "label": "copy-based effectiveness diagnostics"},
        "executive_summary": {
            "overall_effectiveness_score": round(overall_avg, 2),
            "subscores_summary": sub_avgs,
            "top_strengths": top_strengths,
            "top_leaks": top_leaks,
            "fast_wins": fast_wins,
        },
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
) -> Dict[str, Any]:
    """
    Run full pipeline: ingest → exposure proxy → LLM per-ad → aggregate.
    Returns report payload (meta, executive_summary, ads, tear_down).
    progress_callback(stage, current, total, message) is called during LLM pass.
    system_message and model from Prompt Engineering when configured; else use built-in prompts.
    """
    normalized = ingest_ads(ads)
    if not normalized:
        return aggregate([])

    enrich_ads_with_exposure(normalized)

    llm_pass(
        normalized,
        llm_service,
        progress_callback=progress_callback,
        system_message=system_message,
        model=model,
    )

    return aggregate(normalized)
