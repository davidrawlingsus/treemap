"""
Exposure proxy computation for Creative MRI.
Stable per-report run: run_days, exposure_proxy, status.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


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


def _ensure_utc(d: datetime) -> datetime:
    """Ensure datetime has UTC timezone for subtraction."""
    if d.tzinfo is None:
        return d.replace(tzinfo=timezone.utc)
    return d


def _status_multiplier(status: Optional[str]) -> float:
    """Status multiplier for exposure proxy: Active=1.0, Inactive=0.7, else 0.85."""
    s = (status or "").strip().lower()
    if s == "active":
        return 1.0
    if s == "inactive":
        return 0.7
    return 0.85


def compute_exposure_proxy(
    ad: Dict[str, Any],
    report_end_date: Optional[datetime] = None,
) -> tuple[int, float]:
    """
    Compute run_days and exposure_proxy for a single ad.
    If ended_running_on (ad_delivery_end_time) is null, use report_end_date or now (UTC).
    Returns (run_days, exposure_proxy).
    """
    start = _parse_date(ad.get("ad_delivery_start_time") or ad.get("started_running_on"))
    end = _parse_date(ad.get("ad_delivery_end_time"))
    cutoff = report_end_date or datetime.now(timezone.utc)
    if end and start and end >= start:
        effective_end = end
    else:
        effective_end = cutoff
    effective_start = start or cutoff
    end_utc = _ensure_utc(effective_end)
    start_utc = _ensure_utc(effective_start)
    run_days = max(1, int((end_utc - start_utc).total_seconds() / 86400))

    ads_count = ad.get("ads_using_creative_count")
    ads_count = max(1, int(ads_count)) if isinstance(ads_count, (int, float)) else 1

    status = ad.get("status")
    mult = _status_multiplier(status)
    exposure_proxy = float(ads_count * run_days * mult)
    exposure_proxy = max(1.0, exposure_proxy)

    return run_days, exposure_proxy


def enrich_ads_with_exposure(
    ads: List[Dict[str, Any]],
    report_end_date: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """
    Add run_days, exposure_proxy, and ensure status to each ad.
    Backward compat: missing status -> None; run_days/exposure_proxy default to 1.
    """
    if report_end_date is None:
        report_end_date = datetime.now(timezone.utc)
    for ad in ads:
        if "run_days" in ad and "exposure_proxy" in ad:
            continue
        run_days, exposure_proxy = compute_exposure_proxy(ad, report_end_date)
        ad["run_days"] = run_days
        ad["exposure_proxy"] = exposure_proxy
        # status stays as-is from ad (from scrape or None)
    return ads
