"""
Founder admin routes for lead-gen VoC run inspection.
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
    LeadgenVocProcessedJsonResponse,
    LeadgenVocRowsResponse,
)
from app.services.leadgen_voc_service import (
    get_leadgen_rows_as_process_voc_dicts,
    get_leadgen_run,
    list_leadgen_runs,
)

router = APIRouter()


@router.get("/api/founder-admin/leadgen-runs", response_model=LeadgenVocRunListResponse)
def founder_list_leadgen_runs(
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


@router.get("/api/founder-admin/leadgen-runs/{run_id}/processed-json", response_model=LeadgenVocProcessedJsonResponse)
def founder_get_leadgen_processed_json(
    run_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    run = get_leadgen_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Lead-gen run not found")
    return LeadgenVocProcessedJsonResponse(run_id=run_id, payload=run.payload or {})


@router.get("/api/founder-admin/leadgen-runs/{run_id}/rows", response_model=LeadgenVocRowsResponse)
def founder_get_leadgen_rows(
    run_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    run = get_leadgen_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Lead-gen run not found")
    rows = get_leadgen_rows_as_process_voc_dicts(db, run_id)
    return LeadgenVocRowsResponse(run_id=run_id, rows=rows)
