"""
Exposure-weighted aggregations for Creative MRI synthesis.
"""
from typing import Any, Dict, List


def _safe_float(v: Any, default: float = 0.0) -> float:
    if v is None:
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def compute_aggregates(ads: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compute raw and exposure-weighted aggregates for synthesis.
    Handles missing fields gracefully (backward compat).
    """
    n = len(ads)
    if n == 0:
        return _empty_aggregates()

    total_weight = sum(_safe_float(a.get("exposure_proxy"), 1.0) for a in ads)

    # Funnel: distribution_raw and distribution_exposure_weighted
    funnel_raw = {"tofu": 0, "mofu": 0, "bofu": 0}
    funnel_weighted: Dict[str, float] = {"tofu": 0.0, "mofu": 0.0, "bofu": 0.0}
    for a in ads:
        stage = (a.get("funnel_stage") or (a.get("llm") or {}).get("funnel_stage") or "tofu")
        stage = str(stage).lower()
        if stage not in funnel_raw:
            funnel_raw[stage] = 0
            funnel_weighted[stage] = 0.0
        funnel_raw[stage] += 1
        w = _safe_float(a.get("exposure_proxy"), 1.0)
        funnel_weighted[stage] = funnel_weighted.get(stage, 0) + w

    funnel_share_raw = {k: v / n for k, v in funnel_raw.items()} if n else {}
    funnel_share_weighted = (
        {k: v / total_weight for k, v in funnel_weighted.items()} if total_weight > 0 else {}
    )

    # MOFU job split (only among MOFU ads), exposure-weighted
    mofu_ads = [a for a in ads if (a.get("funnel_stage") or (a.get("llm") or {}).get("funnel_stage") or "tofu").lower() == "mofu"]
    mofu_weight = sum(_safe_float(a.get("exposure_proxy"), 1.0) for a in mofu_ads)
    mofu_job_split: Dict[str, float] = {}
    for a in mofu_ads:
        jt = (a.get("llm") or {}).get("mofu_job_type") or "unknown"
        jt = str(jt).lower() if jt else "unknown"
        if jt not in ("not_applicable", "unknown"):
            mofu_job_split[jt] = mofu_job_split.get(jt, 0) + _safe_float(a.get("exposure_proxy"), 1.0)
    if mofu_weight > 0:
        mofu_job_split = {k: v / mofu_weight for k, v in mofu_job_split.items()}

    # Dominant hook types, exposure-weighted
    hook_weights: Dict[str, float] = {}
    for a in ads:
        ht = (a.get("hook_type") or (a.get("llm") or {}).get("hook_type") or "unknown")
        ht = str(ht).lower() if ht else "unknown"
        w = _safe_float(a.get("exposure_proxy"), 1.0)
        hook_weights[ht] = hook_weights.get(ht, 0) + w
    dominant_hook_types = dict(sorted(hook_weights.items(), key=lambda x: -x[1])[:10])

    # Avg hook quality, exposure-weighted (overall from hook_scores)
    num = 0.0
    denom = 0.0
    for a in ads:
        hs = (a.get("llm") or {}).get("hook_scores") or {}
        overall = hs.get("overall") if isinstance(hs, dict) else None
        q = _safe_float(overall, 50.0)
        w = _safe_float(a.get("exposure_proxy"), 1.0)
        num += q * w
        denom += w
    avg_hook_quality = num / denom if denom > 0 else 50.0

    # Avg proof strength, exposure-weighted (credibility from hook_scores or subscores)
    num = 0.0
    denom = 0.0
    for a in ads:
        hs = (a.get("llm") or {}).get("hook_scores") or {}
        proof = hs.get("credibility") if isinstance(hs, dict) else None
        if proof is None:
            proof = (a.get("subscores") or {}).get("proof_strength")
        q = _safe_float(proof, 50.0)
        w = _safe_float(a.get("exposure_proxy"), 1.0)
        num += q * w
        denom += w
    avg_proof_strength = num / denom if denom > 0 else 50.0

    # Claim-proof mismatch rate, exposure-weighted
    # Mismatch = claim_audit.claim_proof_mismatch in {medium, high}
    mismatch_weight = 0.0
    for a in ads:
        ca = (a.get("llm") or {}).get("claim_audit") or {}
        cpm = (ca.get("claim_proof_mismatch") or "").lower() if isinstance(ca, dict) else ""
        is_mismatch = cpm in ("medium", "high")
        w = _safe_float(a.get("exposure_proxy"), 1.0)
        if is_mismatch:
            mismatch_weight += w
    claim_proof_mismatch_rate = mismatch_weight / total_weight if total_weight > 0 else 0.0

    # Replace vs refine mix: rates weighted by exposure_proxy and raw counts
    replace_count = 0
    refine_count = 0
    replace_weight = 0.0
    refine_weight = 0.0
    for a in ads:
        dec = (a.get("llm") or {}).get("replace_vs_refine") or {}
        decision = (dec.get("decision") or "").lower() if isinstance(dec, dict) else ""
        w = _safe_float(a.get("exposure_proxy"), 1.0)
        if decision == "replace":
            replace_count += 1
            replace_weight += w
        elif decision == "refine":
            refine_count += 1
            refine_weight += w
    total_dec = replace_count + refine_count
    replace_vs_refine_mix = {
        "raw": {"replace": replace_count, "refine": refine_count, "replace_rate": replace_count / total_dec if total_dec else 0},
        "exposure_weighted": {
            "replace_weight": replace_weight,
            "refine_weight": refine_weight,
            "replace_rate": replace_weight / (replace_weight + refine_weight) if (replace_weight + refine_weight) > 0 else 0,
        },
    }

    # Video first 2s aggregates (video only), exposure-weighted
    video_ads = [a for a in ads if _is_video_ad(a)]
    video_weight = sum(_safe_float(a.get("exposure_proxy"), 1.0) for a in video_ads)
    hook_present_count = 0.0
    first2s_quality_split: Dict[str, float] = {}
    for a in video_ads:
        vf = (a.get("llm") or {}).get("video_first_2s") or {}
        if not isinstance(vf, dict):
            continue
        if vf.get("applicable") is False:
            continue
        w = _safe_float(a.get("exposure_proxy"), 1.0)
        if vf.get("hook_present"):
            hook_present_count += w
        q = (vf.get("quality") or "unknown").lower()
        first2s_quality_split[q] = first2s_quality_split.get(q, 0) + w
    hook_present_in_first_2s_rate = hook_present_count / video_weight if video_weight > 0 else 0.0
    if video_weight > 0:
        first2s_quality_split = {k: v / video_weight for k, v in first2s_quality_split.items()}

    return {
        "distribution_raw": {"funnel": funnel_share_raw},
        "distribution_exposure_weighted": {"funnel": funnel_share_weighted},
        "mofu_job_split_exposure_weighted": mofu_job_split,
        "dominant_hook_types": dominant_hook_types,
        "avg_hook_quality": round(avg_hook_quality, 2),
        "avg_proof_strength": round(avg_proof_strength, 2),
        "claim_proof_mismatch_rate": round(claim_proof_mismatch_rate, 4),
        "replace_vs_refine_mix": replace_vs_refine_mix,
        "video_first_2s": {
            "hook_present_in_first_2s_rate": round(hook_present_in_first_2s_rate, 4),
            "first2s_quality_split": first2s_quality_split,
        },
    }


def _is_video_ad(ad: Dict[str, Any]) -> bool:
    fmt = (ad.get("ad_format") or "").lower()
    if fmt == "video":
        return True
    items = ad.get("media_items") or []
    return any((m or {}).get("media_type") == "video" for m in items)


def _empty_aggregates() -> Dict[str, Any]:
    return {
        "distribution_raw": {"funnel": {}},
        "distribution_exposure_weighted": {"funnel": {}},
        "mofu_job_split_exposure_weighted": {},
        "dominant_hook_types": {},
        "avg_hook_quality": 50.0,
        "avg_proof_strength": 50.0,
        "claim_proof_mismatch_rate": 0.0,
        "replace_vs_refine_mix": {"raw": {"replace": 0, "refine": 0, "replace_rate": 0}, "exposure_weighted": {"replace_weight": 0, "refine_weight": 0, "replace_rate": 0}},
        "video_first_2s": {"hook_present_in_first_2s_rate": 0.0, "first2s_quality_split": {}},
    }
