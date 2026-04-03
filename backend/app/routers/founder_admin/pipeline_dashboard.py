"""
Founder admin pipeline analytics dashboard.

Provides run-level and funnel-level analytics for lead gen pipelines.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import get_current_active_founder
from app.database import get_db
from app.models import User
from app.models.leadgen_voc import LeadgenVocRun
from app.models.lead_email import LeadEmail

router = APIRouter()

PIPELINE_STEPS = [
    "queued",
    "detecting_platforms",
    "scraping",
    "scraping_trustpilot",
    "scraping_reviews_io",
    "scraping_yotpo",
    "extracting_context",
    "extracting",
    "building_taxonomy",
    "validating",
    "classifying",
    "generating_ads",
    "generating_analysis",
    "scheduling_emails",
    "completed",
]

TERMINAL_STATES = {"completed", "failed", "disabled"}
HANG_THRESHOLD_MINUTES = 30


@router.get("/api/founder-admin/pipeline-dashboard")
def get_pipeline_dashboard(
    days: int = Query(default=7, ge=1, le=90),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Pipeline analytics: all runs, funnel stats, and flagged issues."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    now = datetime.now(timezone.utc)

    runs = (
        db.query(LeadgenVocRun)
        .filter(LeadgenVocRun.created_at >= cutoff)
        .order_by(LeadgenVocRun.created_at.desc())
        .all()
    )

    # Build per-run detail
    run_details = []
    for run in runs:
        payload = run.payload or {}
        step_times = payload.get("step_times", {})

        # Calculate step durations from timestamps
        steps = []
        sorted_steps = sorted(step_times.items(), key=lambda x: x[1])
        for i, (step_name, ts) in enumerate(sorted_steps):
            started = datetime.fromisoformat(ts.replace("Z", "+00:00")) if isinstance(ts, str) else ts
            if i + 1 < len(sorted_steps):
                next_ts = sorted_steps[i + 1][1]
                ended = datetime.fromisoformat(next_ts.replace("Z", "+00:00")) if isinstance(next_ts, str) else next_ts
                duration_s = (ended - started).total_seconds()
            else:
                duration_s = None  # still running or last step
            steps.append({
                "step": step_name,
                "started_at": ts,
                "duration_seconds": round(duration_s, 1) if duration_s is not None else None,
            })

        # Detect hanging
        is_hanging = False
        if run.coding_status not in TERMINAL_STATES:
            last_update = run.updated_at or run.created_at
            if last_update and (now - last_update).total_seconds() > HANG_THRESHOLD_MINUTES * 60:
                is_hanging = True

        # Total duration
        total_seconds = None
        if run.coding_status in TERMINAL_STATES and step_times:
            first_ts = min(step_times.values())
            last_ts = max(step_times.values())
            try:
                t0 = datetime.fromisoformat(first_ts.replace("Z", "+00:00"))
                t1 = datetime.fromisoformat(last_ts.replace("Z", "+00:00"))
                total_seconds = round((t1 - t0).total_seconds(), 1)
            except (ValueError, TypeError):
                pass

        # Email count
        email_count = (
            db.query(func.count(LeadEmail.id))
            .filter(LeadEmail.run_id == run.run_id)
            .scalar()
        )

        run_details.append({
            "run_id": run.run_id,
            "company_name": run.company_name,
            "company_domain": run.company_domain,
            "status": run.coding_status,
            "review_count": run.review_count,
            "email_count": email_count,
            "created_at": run.created_at.isoformat() if run.created_at else None,
            "total_seconds": total_seconds,
            "is_hanging": is_hanging,
            "detected_platform": payload.get("detected_platform"),
            "has_gamma": bool(payload.get("gamma_url")),
            "has_pdf": bool(payload.get("pdf_url")),
            "steps": steps,
        })

    # Funnel stats
    total = len(runs)
    status_counts = {}
    for run in runs:
        s = run.coding_status or "unknown"
        status_counts[s] = status_counts.get(s, 0) + 1

    completed = status_counts.get("completed", 0)
    failed = status_counts.get("failed", 0)
    in_progress = total - completed - failed - status_counts.get("disabled", 0)

    # Step reach: how many runs made it to each step
    step_reach = {s: 0 for s in PIPELINE_STEPS}
    for run in runs:
        payload = run.payload or {}
        step_times = payload.get("step_times", {})
        for step in step_times:
            if step in step_reach:
                step_reach[step] += 1

    return {
        "summary": {
            "total_runs": total,
            "completed": completed,
            "failed": failed,
            "in_progress": in_progress,
            "completion_rate": round(completed / total * 100, 1) if total else 0,
            "hanging": sum(1 for r in run_details if r["is_hanging"]),
        },
        "funnel": [
            {"step": step, "count": step_reach[step]}
            for step in PIPELINE_STEPS
        ],
        "status_counts": status_counts,
        "runs": run_details,
    }


@router.post("/api/founder-admin/pipeline-dashboard/{run_id}/retry")
def retry_run(
    run_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Retry a failed run."""
    from app.services.leadgen_pipeline_runner import run_full_pipeline_background

    run = db.query(LeadgenVocRun).filter(LeadgenVocRun.run_id == run_id).first()
    if not run:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Run not found")

    run.coding_status = "queued"
    db.commit()
    run_full_pipeline_background(run_id)
    return {"restarted": True, "run_id": run_id}


@router.post("/api/founder-admin/pipeline-dashboard/{run_id}/cancel")
def cancel_run(
    run_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Mark a run as failed (cancel it)."""
    run = db.query(LeadgenVocRun).filter(LeadgenVocRun.run_id == run_id).first()
    if not run:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Run not found")

    run.coding_status = "failed"
    db.commit()
    return {"cancelled": True, "run_id": run_id}


@router.post("/api/founder-admin/pipeline-dashboard/{run_id}/backfill-gamma")
def backfill_gamma(
    run_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Generate Gamma deck for a completed run that's missing one."""
    import threading
    from app.config import get_settings
    from app.models.leadgen_pipeline_output import LeadgenPipelineOutput

    run = db.query(LeadgenVocRun).filter(LeadgenVocRun.run_id == run_id).first()
    if not run:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Run not found")

    # Get deck_markdown from JSON output
    json_output = (
        db.query(LeadgenPipelineOutput)
        .filter(LeadgenPipelineOutput.run_id == run_id, LeadgenPipelineOutput.step_type == "voc_analysis_json")
        .first()
    )
    if not json_output:
        # Fall back to raw markdown
        md_output = (
            db.query(LeadgenPipelineOutput)
            .filter(LeadgenPipelineOutput.run_id == run_id, LeadgenPipelineOutput.step_type == "voc_analysis_markdown")
            .first()
        )
        deck_content = (md_output.output or {}).get("markdown", "") if md_output else ""
    else:
        deck_content = (json_output.output or {}).get("deck_markdown", "")

    if not deck_content:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="No deck content available for this run")

    settings = get_settings()
    company_name = run.company_name

    def _generate():
        from app.services.gamma_service import generate_deck
        from app.database import SessionLocal
        from sqlalchemy.orm.attributes import flag_modified

        result = generate_deck(
            api_key=getattr(settings, "gamma_api_key", None),
            title=f"VoC Creative Strategy: {company_name}",
            markdown_content=deck_content,
        )
        if result:
            _db = SessionLocal()
            _run = _db.query(LeadgenVocRun).filter(LeadgenVocRun.run_id == run_id).first()
            if _run:
                payload = _run.payload or {}
                if result.gamma_url:
                    payload["gamma_url"] = result.gamma_url
                if result.pdf_url:
                    payload["pdf_url"] = result.pdf_url
                _run.payload = payload
                flag_modified(_run, "payload")
                _db.commit()
            _db.close()

    threading.Thread(target=_generate, daemon=True).start()
    return {"started": True, "run_id": run_id, "deck_content_length": len(deck_content)}
