"""
Founder admin routes for lead-gen VoC run inspection.
"""

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timezone
from threading import Lock

from app.config import get_settings
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
    delete_leadgen_run,
    get_leadgen_rows_as_process_voc_dicts,
    get_leadgen_run,
    list_leadgen_runs,
    upsert_leadgen_run_with_rows,
)
from app.services.trustpilot_processor_service import build_trustpilot_llm_input_payload
from app.services.voc_coding_chain_service import (
    VocCodingChainError,
    merge_coded_reviews_into_rows,
    run_voc_coding_chain,
    validate_import_ready_rows,
)

router = APIRouter()
_RERUN_LOCK = Lock()
_ACTIVE_RERUNS: set[str] = set()


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


@router.delete("/api/founder-admin/leadgen-runs/{run_id}", status_code=204)
def founder_delete_leadgen_run(
    run_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    deleted = delete_leadgen_run(db, run_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Lead-gen run not found")
    db.commit()
    return Response(status_code=204)


@router.post("/api/founder-admin/leadgen-runs/{run_id}/rerun")
def founder_rerun_leadgen_run(
    run_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    with _RERUN_LOCK:
        if run_id in _ACTIVE_RERUNS:
            raise HTTPException(status_code=409, detail="This run is already being reprocessed")
        _ACTIVE_RERUNS.add(run_id)

    try:
        run = get_leadgen_run(db, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Lead-gen run not found")

        settings = get_settings()
        if not bool(settings.voc_coding_enabled):
            raise HTTPException(status_code=400, detail="VOC coding is disabled in backend settings")

        stored_rows = get_leadgen_rows_as_process_voc_dicts(db, run_id)
        if not stored_rows:
            raise HTTPException(status_code=400, detail="No stored rows available for rerun")

        previous_payload = run.payload or {}
        company_context = previous_payload.get("company_context")
        if not isinstance(company_context, dict):
            company_context = {
                "name": run.company_name,
                "context_text": "No website context extracted. Proceed using Trustpilot review text only for coding and topic extraction.",
                "source_url": run.company_url,
            }

        try:
            coding_result = run_voc_coding_chain(
                settings=settings,
                reviews=stored_rows,
                product_context=company_context,
                run_id_override=run_id,
                db=db,
                use_prompt_db=True,
                strict_prompt_db=True,
                strict_mode=True,
            )
            import_ready_rows = merge_coded_reviews_into_rows(
                process_voc_rows=stored_rows,
                coded_reviews=coding_result.get("coded_reviews", []),
            )
            validate_import_ready_rows(import_ready_rows)
        except VocCodingChainError as exc:
            raise HTTPException(status_code=502, detail=f"[{exc.step}] {exc}")
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"[coding] {exc}")

        normalized_reviews = previous_payload.get("trustpilot_reviews_normalized")
        if not isinstance(normalized_reviews, list):
            normalized_reviews = []
        include_debug_data = bool(normalized_reviews)

        payload = build_trustpilot_llm_input_payload(
            work_email=run.work_email,
            company_domain=run.company_domain,
            company_url=run.company_url,
            company_name=run.company_name,
            company_context=company_context,
            normalized_reviews=normalized_reviews,
            process_voc_rows_import_ready=import_ready_rows,
            run_id=run_id,
            coding_result=coding_result,
            include_debug_data=include_debug_data,
        )

        generated_at = datetime.now(timezone.utc)
        run_record = upsert_leadgen_run_with_rows(
            db,
            run_id=run_id,
            work_email=run.work_email,
            company_domain=run.company_domain,
            company_url=run.company_url,
            company_name=run.company_name,
            review_count=len(import_ready_rows),
            coding_enabled=True,
            coding_status="completed",
            generated_at=generated_at,
            payload=payload,
            rows=import_ready_rows,
        )
        db.commit()
        return {
            "run_id": run_record.run_id,
            "review_count": run_record.review_count,
            "coding_status": run_record.coding_status,
            "updated_at": generated_at.isoformat(),
        }
    finally:
        with _RERUN_LOCK:
            _ACTIVE_RERUNS.discard(run_id)
