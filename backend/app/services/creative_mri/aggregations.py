"""
Creative MRI v2: Exposure-weighted aggregations.
Simplified — heavy synthesis work moved to LLM Pass 2 (synthesize.py).
This module computes temporal/structural aggregates for charts 1-6.
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
    Compute raw and exposure-weighted aggregates for chart data.
    Dimension scoring and synthesis are handled by LLM Pass 2.
    """
    n = len(ads)
    if n == 0:
        return _empty_aggregates()

    total_weight = sum(_safe_float(a.get("exposure_proxy"), 1.0) for a in ads)

    # Funnel distribution: raw and exposure-weighted
    funnel_raw: Dict[str, int] = {"tofu": 0, "mofu": 0, "bofu": 0}
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

    # Dominant hook types, exposure-weighted
    hook_weights: Dict[str, float] = {}
    for a in ads:
        ht = (a.get("hook_type") or (a.get("llm") or {}).get("hook_type") or "unknown")
        ht = str(ht).lower() if ht else "unknown"
        w = _safe_float(a.get("exposure_proxy"), 1.0)
        hook_weights[ht] = hook_weights.get(ht, 0) + w
    dominant_hook_types = dict(sorted(hook_weights.items(), key=lambda x: -x[1])[:10])

    return {
        "distribution_raw": {"funnel": funnel_share_raw},
        "distribution_exposure_weighted": {"funnel": funnel_share_weighted},
        "dominant_hook_types": dominant_hook_types,
    }


def _empty_aggregates() -> Dict[str, Any]:
    return {
        "distribution_raw": {"funnel": {}},
        "distribution_exposure_weighted": {"funnel": {}},
        "dominant_hook_types": {},
    }
