"""
Creative MRI pipeline: ingest → classify → score → LLM → similarity → aggregate.
Rules for scores; LLM supplements hook, angle, unsupported_claims, what_to_change.
"""
import re
import logging
from typing import Any, Dict, List, Optional

from app.services.creative_mri.rules import (
    detect_hook_type,
    detect_proof_types,
    detect_offer_elements,
    detect_funnel_stage,
)
from app.services.creative_mri.llm import call_creative_mri_llm

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
            "headline": headline,
            "primary_text": primary,
            "full_text": full_text,
            "word_count": wc,
            "cta": _normalize_text(ad.get("cta")) or None,
            "destination_url": (ad.get("destination_url") or "").strip() or None,
            "ad_format": (ad.get("ad_format") or "").strip() or None,
            "ad_delivery_start_time": ad.get("ad_delivery_start_time"),
            "ad_delivery_end_time": ad.get("ad_delivery_end_time"),
            "media_thumbnail_url": (ad.get("media_thumbnail_url") or "").strip() or None,
        }
        out.append(normalized)
    return out


def classify_and_score(ad: Dict[str, Any]) -> Dict[str, Any]:
    """Rule-based: hook_type, funnel_stage, proof_types, offer_elements; simple subscores and overall 0–100."""
    full = ad.get("full_text") or ""
    wc = max(1, ad.get("word_count") or 1)

    hook_type = detect_hook_type(full)
    funnel_stage = detect_funnel_stage(full)
    proof_types = detect_proof_types(full)
    offer_elements = detect_offer_elements(full)

    # Simple subscores 0–20 each (placeholder: rule-based heuristics)
    hook_score = 10 if hook_type != "unknown" else 4
    clarity_score = min(20, 5 + min(15, (wc // 20)))  # length proxy
    proof_score = min(20, len(proof_types) * 4)
    diff_score = 10 if ("new_mechanism" in hook_type or "comparison" in hook_type) else 6
    conv_score = 5
    if ad.get("cta"):
        conv_score += 5
    if ad.get("destination_url"):
        conv_score += 5
    if offer_elements:
        conv_score += 5
    conv_score = min(20, conv_score)

    overall = hook_score + clarity_score + proof_score + diff_score + conv_score
    overall = min(100, max(0, overall))

    ad["hook_type"] = hook_type
    ad["funnel_stage"] = funnel_stage
    ad["proof_types"] = proof_types
    ad["offer_elements"] = offer_elements
    ad["overall_score"] = overall
    ad["subscores"] = {
        "hook": hook_score,
        "clarity_specificity": clarity_score,
        "proof_strength": proof_score,
        "differentiation_mechanism": diff_score,
        "conversion_readiness": conv_score,
    }
    return ad


def llm_pass(ads: List[Dict[str, Any]], llm_service: Any) -> List[Dict[str, Any]]:
    """Call Claude per-ad; merge llm fields into each ad. On failure, keep rule-only."""
    for ad in ads:
        llm_out = call_creative_mri_llm(llm_service, ad)
        if not llm_out:
            ad["llm"] = None
            continue
        # Prefer LLM hook_type for display when present
        ad["llm"] = {
            "hook_type": llm_out.get("hook_type"),
            "hook_phrase": llm_out.get("hook_phrase"),
            "secondary_hook": llm_out.get("secondary_hook"),
            "angle": llm_out.get("angle"),
            "unsupported_claims": llm_out.get("unsupported_claims") or [],
            "what_to_change": llm_out.get("what_to_change") or [],
        }
        if llm_out.get("angle"):
            ad["angle"] = llm_out["angle"]
        if llm_out.get("hook_phrase"):
            ad["hook_phrase"] = llm_out["hook_phrase"]
    return ads


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

    # Fast wins: 5 generic copy-editable actions from low scores
    fast_wins = [
        "Add a clear hook in the first line (pain, result, or curiosity).",
        "Add proof (testimonial, data, or before/after) near key claims.",
        "Add a clear CTA and destination (button/link).",
        "Add one offer element (discount, guarantee, free shipping).",
        "Differentiate with mechanism or comparison.",
    ]

    # Tear-down: 2 best, 2 average, 2 weakest by overall_score
    by_score = sorted(ads, key=lambda a: -(a.get("overall_score") or 0))
    best = by_score[:2] if len(by_score) >= 2 else by_score[:1]
    mid_start = max(1, len(by_score) // 2 - 1)
    mid_end = mid_start + 2
    average = by_score[mid_start:mid_end]
    worst = by_score[-2:] if len(by_score) >= 2 else by_score[-1:]
    selected = best + average + worst
    for a in selected:
        a["what_to_change"] = (a.get("llm") or {}).get("what_to_change") or []

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
    }


def run_creative_mri_pipeline(
    ads: List[Dict[str, Any]],
    llm_service: Any,
) -> Dict[str, Any]:
    """
    Run full pipeline: ingest → classify/score → LLM per-ad → aggregate.
    Returns report payload (meta, executive_summary, ads, tear_down).
    """
    normalized = ingest_ads(ads)
    if not normalized:
        return aggregate([])

    for ad in normalized:
        classify_and_score(ad)

    llm_pass(normalized, llm_service)

    return aggregate(normalized)
