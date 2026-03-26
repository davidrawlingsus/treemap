"""
Public, no-auth lead generation endpoints.
"""

from datetime import datetime, timezone
import logging
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.schemas import TrustpilotLeadgenRequest, TrustpilotLeadgenResponse
from app.services.product_context_service import extract_product_context_from_url_service, normalize_url
from app.services.trustpilot_apify_service import fetch_trustpilot_reviews_by_domain
from app.services.trustpilot_processor_service import (
    build_pre_llm_process_voc_rows,
    build_trustpilot_llm_input_payload,
    infer_company_name_from_domain,
    infer_company_url_from_domain,
    is_likely_work_email_domain,
    parse_domain_from_work_email,
)
from app.services.voc_coding_chain_service import (
    VocCodingChainError,
    merge_coded_reviews_into_rows,
    run_new_voc_pipeline,
    run_voc_coding_chain,
    validate_import_ready_rows,
)
from app.services.leadgen_voc_service import upsert_leadgen_run_with_rows, create_or_update_lead_client

router = APIRouter(prefix="/api/public", tags=["public-leadgen"])
logger = logging.getLogger(__name__)


def _safe_domain_slug(domain: str) -> str:
    return re.sub(r"[^a-z0-9.-]", "-", domain.lower())


@router.post("/trustpilot-leadgen", response_model=TrustpilotLeadgenResponse)
def build_trustpilot_llm_input(
    body: TrustpilotLeadgenRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    debug_run_id = body.resume_run_id or uuid.uuid4().hex
    try:
        company_domain = parse_domain_from_work_email(body.work_email)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if not is_likely_work_email_domain(company_domain):
        raise HTTPException(
            status_code=400,
            detail="Please provide a work email address (personal email domains are not supported).",
        )

    company_url = normalize_url(body.company_url or infer_company_url_from_domain(company_domain))
    company_name = (body.company_name or infer_company_name_from_domain(company_domain)).strip()
    settings = get_settings()
    logger.info(
        "Public trustpilot leadgen request: domain=%s actor_id=%s max_reviews=%s",
        company_domain,
        settings.apify_trustpilot_actor_id,
        body.max_reviews,
    )
    llm_service = getattr(request.app.state, "llm_service", None)
    if llm_service is None:
        raise HTTPException(status_code=503, detail="LLM service is not available")

    try:
        company_context = extract_product_context_from_url_service(
            db=db,
            llm_service=llm_service,
            url=company_url,
        )
    except (ValueError, RuntimeError) as exc:
        company_context = {
            "name": company_name,
            "context_text": (
                "No website context extracted. Proceed using Trustpilot review text only "
                "for coding and topic extraction."
            ),
            "source_url": company_url,
        }

    normalized_reviews = fetch_trustpilot_reviews_by_domain(
        settings=settings,
        domain=company_domain,
        max_reviews=body.max_reviews,
    )
    logger.info(
        "Public trustpilot leadgen fetched reviews: domain=%s count=%s",
        company_domain,
        len(normalized_reviews),
    )

    if len(normalized_reviews) > settings.voc_coding_max_reviews:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Review count ({len(normalized_reviews)}) exceeds configured max "
                f"({settings.voc_coding_max_reviews})"
            ),
        )

    pre_llm_rows = build_pre_llm_process_voc_rows(
        normalized_reviews=normalized_reviews,
        company_name=company_name,
        company_domain=company_domain,
    )

    import_ready_rows = pre_llm_rows
    coding_result = None
    run_id = debug_run_id
    if settings.voc_coding_enabled:
        try:
            coding_result = run_new_voc_pipeline(
                settings=settings,
                reviews=pre_llm_rows,
                product_context=company_context,
                db=db,
            )
            run_id = coding_result.get("run_id")
            import_ready_rows = merge_coded_reviews_into_rows(
                process_voc_rows=pre_llm_rows,
                coded_reviews=coding_result.get("coded_reviews", []),
            )
            validate_import_ready_rows(import_ready_rows)
        except VocCodingChainError as exc:
            raise HTTPException(status_code=502, detail=f"[{exc.step}] {exc}")
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"[coding] {exc}")

    payload = build_trustpilot_llm_input_payload(
        work_email=body.work_email,
        company_domain=company_domain,
        company_url=company_url,
        company_name=company_name,
        company_context=company_context,
        normalized_reviews=normalized_reviews,
        process_voc_rows_import_ready=import_ready_rows,
        run_id=run_id,
        coding_result=coding_result,
        include_debug_data=body.include_debug_data,
    )

    generated_at = _safe_parse_dt(payload.get("generated_at")) or datetime.now(timezone.utc)
    run_record = upsert_leadgen_run_with_rows(
        db,
        run_id=run_id,
        work_email=body.work_email,
        company_domain=company_domain,
        company_url=company_url,
        company_name=company_name,
        review_count=len(normalized_reviews),
        coding_enabled=bool(settings.voc_coding_enabled),
        coding_status="completed" if settings.voc_coding_enabled else "disabled",
        generated_at=generated_at,
        payload=payload,
        rows=import_ready_rows,
    )

    # Create/update a lead Client and copy rows to process_voc
    lead_client = create_or_update_lead_client(db, run_record)

    db.commit()
    run_id = run_record.run_id

    now = datetime.now(timezone.utc)
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    safe_domain = _safe_domain_slug(company_domain)
    file_name = f"trustpilot_llm_input_{safe_domain}_{stamp}.json"

    return TrustpilotLeadgenResponse(
        file_name=file_name,
        generated_at=now,
        company_domain=company_domain,
        company_url=company_url,
        company_name=company_name,
        run_id=run_id,
        client_id=str(lead_client.id),
        review_count=len(normalized_reviews),
        payload=payload,
    )


def _safe_parse_dt(value):
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None
