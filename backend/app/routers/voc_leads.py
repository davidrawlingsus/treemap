"""
Founder-only lead run VOC endpoints for visualization tab.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.auth import get_current_active_founder
from app.database import get_db
from app.models import User
from app.schemas import (
    LeadgenVocRunListResponse,
    LeadgenVocRunSummary,
    VocSummaryResponse,
    VocSummaryCategory,
    VocSummaryTopic,
)
from app.services.leadgen_voc_service import (
    build_leadgen_summary_dict,
    get_leadgen_rows_as_process_voc_dicts,
    get_leadgen_run,
    list_leadgen_runs,
)

router = APIRouter(prefix="/api/voc/leads", tags=["voc-leads"])


@router.get("/runs", response_model=LeadgenVocRunListResponse)
def list_runs(
    search: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    runs = list_leadgen_runs(db, search=search, limit=max(1, min(limit, 500)))
    return LeadgenVocRunListResponse(
        items=[
            LeadgenVocRunSummary(
                run_id=run.run_id,
                company_name=run.company_name,
                company_domain=run.company_domain,
                work_email=run.work_email,
                review_count=run.review_count,
                coding_enabled=run.coding_enabled,
                coding_status=run.coding_status,
                generated_at=run.generated_at,
                created_at=run.created_at,
                converted_at=run.converted_at,
                converted_client_uuid=run.converted_client_uuid,
            )
            for run in runs
        ]
    )


@router.get("/data")
def get_run_data(
    run_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    run = get_leadgen_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Lead-gen run not found")
    return get_leadgen_rows_as_process_voc_dicts(db, run_id)


@router.get("/summary", response_model=VocSummaryResponse)
def get_run_summary(
    run_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    run = get_leadgen_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Lead-gen run not found")
    summary = build_leadgen_summary_dict(db, run_id)
    categories = [
        VocSummaryCategory(
            name=category["name"],
            topics=[VocSummaryTopic(**topic) for topic in category["topics"]],
        )
        for category in summary["categories"]
    ]
    return VocSummaryResponse(categories=categories, total_verbatims=summary["total_verbatims"])
