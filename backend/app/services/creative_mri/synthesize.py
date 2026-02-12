"""
Creative MRI synthesized summary: second LLM pass over full report.
Uses prompt from Prompt Engineering (prompt_purpose=ad_creative_mri_synthesized_summary).
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

try:
    import json_repair
except ImportError:
    json_repair = None  # Install with: pip install json-repair

logger = logging.getLogger(__name__)

PROMPT_PURPOSE = "ad_creative_mri_synthesized_summary"


def _parse_date(s: Any) -> Optional[datetime]:
    """Parse date string from Meta format or ISO."""
    if not s:
        return None
    if isinstance(s, datetime):
        return s
    try:
        d = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return d
    except (ValueError, TypeError):
        pass
    try:
        d = datetime.strptime(str(s), "%b %d, %Y")
        return d
    except (ValueError, TypeError):
        pass
    return None


def _week_key(d: datetime) -> str:
    """ISO week Monday date string."""
    iso = d.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"  # year-Wweek


def _build_aggregate_metadata(report: Dict[str, Any]) -> Dict[str, Any]:
    """Build aggregate metadata for synthesize prompt from report."""
    analysis_ads = report.get("analysis", {}).get("analysis", {}).get("ads") or []
    ds = report.get("analysis", {}).get("analysis", {}).get("dataset_summary") or {}
    redundancy = report.get("analysis", {}).get("analysis", {}).get("redundancy") or {}
    raw_ads = report.get("ads") or []

    # Launch cadence (starts per week)
    by_week = {}
    for a in analysis_ads:
        d = _parse_date(a.get("started_running_on") or a.get("ad_delivery_start_time"))
        if d:
            wk = _week_key(d)
            by_week[wk] = by_week.get(wk, 0) + 1
    launch_cadence = [{"week": k, "count": v} for k, v in sorted(by_week.items())]

    # Active creatives over time (ad-weeks)
    active_by_week = {}
    for a in analysis_ads:
        start = _parse_date(a.get("ad_delivery_start_time") or a.get("started_running_on"))
        end = _parse_date(a.get("ad_delivery_end_time")) or start
        if not start:
            continue
        d = start
        while d <= end:
            wk = _week_key(d)
            active_by_week[wk] = active_by_week.get(wk, 0) + 1
            d = d + timedelta(days=7)
    active_creatives_over_time = [{"week": k, "count": v} for k, v in sorted(active_by_week.items())]

    # Format mix over time
    format_by_week = {}
    for a in analysis_ads:
        d = _parse_date(a.get("started_running_on") or a.get("ad_delivery_start_time"))
        if d:
            wk = _week_key(d)
            fmt = (a.get("labels") or {}).get("format") or "unknown"
            if wk not in format_by_week:
                format_by_week[wk] = {}
            format_by_week[wk][fmt] = format_by_week[wk].get(fmt, 0) + 1
    format_mix_over_time = [
        {"week": k, "formats": v} for k, v in sorted(format_by_week.items())
    ]

    funnel_dist = (ds.get("funnel") or {}).get("stage_share") or {}
    hook_dist = (ds.get("hook") or {}).get("type_share") or {}
    hook_avgs = (ds.get("hook") or {}).get("avg_scores") or {}

    proof = ds.get("proof") or {}
    proof_avg = proof.get("avg_density_score_0_100")

    objection_coverage = (ds.get("objections") or {}).get("coverage_share") or {}

    clusters = redundancy.get("clusters") or []
    redundancy_summary = redundancy.get("summary") or {}

    ads_using_counts = [a.get("ads_using_creative_count") for a in raw_ads if a.get("ads_using_creative_count") is not None]

    exposure_aggregates = (
        (report.get("analysis") or {}).get("analysis") or {}
    ).get("exposure_weighted_aggregates") or {}

    return {
        "launch_cadence": launch_cadence,
        "active_creatives_over_time": active_creatives_over_time,
        "format_mix_over_time": format_mix_over_time,
        "funnel_distribution": funnel_dist,
        "hook_type_distribution": hook_dist,
        "average_hook_scores": hook_avgs,
        "proof_density_averages": proof_avg,
        "objection_coverage_distribution": objection_coverage,
        "redundancy_clusters": clusters,
        "redundancy_summary": redundancy_summary,
        "ads_using_creative_count": sum(ads_using_counts) / len(ads_using_counts) if ads_using_counts else None,
        "exposure_weighted_aggregates": exposure_aggregates,
    }


def get_synthesized_summary_prompt(db: Session) -> Optional[tuple]:
    """Fetch prompt from Prompt Engineering. Returns (system_message, model) or None."""
    from sqlalchemy import func
    from app.models import Prompt

    purpose_lower = PROMPT_PURPOSE.lower()
    prompt = (
        db.query(Prompt)
        .filter(
            func.lower(Prompt.prompt_purpose) == purpose_lower,
            Prompt.status == "live",
        )
        .order_by(Prompt.version.desc())
        .first()
    )
    content = (prompt and (prompt.system_message or prompt.prompt_message)) or None
    if not content:
        return None
    model = prompt.llm_model or "claude-3-5-sonnet-20241022"
    return content, model


def build_synthesize_payload(report: Dict[str, Any]) -> str:
    """Build JSON payload for synthesize LLM (user message)."""
    analysis_ads = report.get("analysis", {}).get("analysis", {}).get("ads") or []
    metadata = _build_aggregate_metadata(report)
    payload = {
        "per_ad_mri": analysis_ads,
        "aggregate_metadata": metadata,
    }
    msg = json.dumps(payload, ensure_ascii=False, default=str)
    return msg


def run_synthesize(
    report: Dict[str, Any],
    llm_service: Any,
    db: Session,
) -> Optional[Dict[str, Any]]:
    """
    Run synthesized summary LLM pass. Returns parsed JSON or None on failure.
    Caller should merge result into report.synthesized_summary.
    """
    prompt_tuple = get_synthesized_summary_prompt(db)
    if not prompt_tuple:
        logger.warning("Synthesized summary prompt not configured (prompt_purpose=%s)", PROMPT_PURPOSE)
        return None

    system_message, model = prompt_tuple
    return _call_synthesize_llm(report, llm_service, system_message, model)


def _call_synthesize_llm(
    report: Dict[str, Any],
    llm_service: Any,
    system_message: str,
    model: str,
) -> Optional[Dict[str, Any]]:
    """Execute LLM call for synthesize (no db - safe for thread)."""
    user_message = build_synthesize_payload(report)
    try:
        result = llm_service.execute_prompt(
            system_message=system_message,
            user_message=user_message,
            model=model,
            max_tokens=16384,
        )
        content = (result or {}).get("content") or ""
        if not content.strip():
            return None

        text = content.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)

        try:
            out = json.loads(text)
        except json.JSONDecodeError as e:
            if json_repair is None:
                logger.warning("Synthesized summary JSON parse failed. Install json-repair for auto-repair: pip install json-repair")
                return None
            try:
                out = json_repair.loads(text)
            except Exception as repair_err:
                logger.warning("Synthesized summary LLM failed (parse + repair): %s", repair_err)
                return None
        if isinstance(out, dict):
            return out
        return None
    except Exception as e:
        logger.warning("Synthesized summary LLM failed: %s", e)
        return None
