"""
Prompt Studio routes — stateless per-step execution of the VOC coding chain
with editable prompts. No results are persisted to the database.
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import get_current_active_founder
from app.config import get_settings
from app.database import get_db
from app.models import LeadgenPipelineOutput, Prompt, User
from app.services.product_context_service import (
    DEFAULT_EXTRACT_SYSTEM_MSG,
    extract_product_name,
    normalize_url,
)
from app.services.trustpilot_apify_service import fetch_trustpilot_reviews_by_domain
from app.services.trustpilot_processor_service import (
    build_pre_llm_process_voc_rows,
    infer_company_name_from_domain,
)
from app.services.voc_coding_chain_prompts import (
    CODE_SCHEMA,
    CODE_SYSTEM_PROMPT,
    CODE_USER_PROMPT,
    DISCOVER_SCHEMA,
    DISCOVER_SYSTEM_PROMPT,
    DISCOVER_USER_PROMPT,
    REFINE_SCHEMA,
    REFINE_SYSTEM_PROMPT,
    REFINE_USER_PROMPT,
)
from app.services.voc_coding_chain_service import (
    VocCodingChainError,
    _compute_coding_stats,
    _format_reviews_for_discovery,
    call_claude_json_schema,
)
from app.services.web_crawler_service import WebCrawlerService

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response Schemas
# ---------------------------------------------------------------------------

class ScrapeRequest(BaseModel):
    url: str = Field(..., description="Prospect company URL (e.g. https://acme.com)")
    company_name: Optional[str] = Field(None, description="Override company name")
    max_reviews: int = Field(50, ge=1, le=5000)


class ScrapeResponse(BaseModel):
    run_id: str
    domain: str
    company_name: str
    company_url: str
    review_count: int


class ContextStepRequest(BaseModel):
    system_prompt: str
    url: str


class ContextStepResponse(BaseModel):
    output: Dict[str, Any]
    page_text: str
    elapsed_seconds: float


class DiscoverStepRequest(BaseModel):
    system_prompt: str
    user_prompt_template: str
    product_context: str
    reviews: List[Dict[str, Any]]


class CodeStepRequest(BaseModel):
    system_prompt: str
    user_prompt_template: str
    codebook: Dict[str, Any]
    reviews: List[Dict[str, Any]]


class RefineStepRequest(BaseModel):
    system_prompt: str
    user_prompt_template: str
    codebook: Dict[str, Any]
    stats: Dict[str, Any]
    no_matches: List[Dict[str, Any]]
    product_context: str


class ExtractStepRequest(BaseModel):
    system_prompt: str
    user_prompt_template: str
    product_context: str
    reviews: List[Dict[str, Any]]


class TaxonomyStepRequest(BaseModel):
    system_prompt: str
    user_prompt_template: str
    product_context: str
    signals: Dict[str, Any]


class ValidateStepRequest(BaseModel):
    system_prompt: str
    user_prompt_template: str
    product_context: str
    taxonomy: Dict[str, Any]
    signals: Dict[str, Any]


class StepResponse(BaseModel):
    output: Any
    elapsed_seconds: float


class PromptVersionItem(BaseModel):
    id: str
    name: str
    version: int
    status: str
    system_message: Optional[str] = None
    prompt_message: Optional[str] = None
    llm_model: str
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class PromptVersionsResponse(BaseModel):
    versions: List[PromptVersionItem]


class DefaultPromptsResponse(BaseModel):
    default_prompts: Dict[str, Optional[str]]


class InputsResponse(BaseModel):
    company_context: Optional[Dict[str, Any]] = None
    reviews: List[Dict[str, Any]]
    default_prompts: Dict[str, Optional[str]]
    pipeline_state: Optional[List[Dict[str, Any]]] = None


class SavePipelineRequest(BaseModel):
    pipeline_state: List[Dict[str, Any]]


# ---------------------------------------------------------------------------
# Helper: extract domain from URL
# ---------------------------------------------------------------------------

def _domain_from_url(url: str) -> str:
    normalized = normalize_url(url)
    parsed = urlparse(normalized)
    host = (parsed.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    if not host or "." not in host:
        raise HTTPException(status_code=400, detail="Could not extract domain from URL")
    return host


EXTRACT_SYSTEM_PROMPT_DEFAULT = """You are a Voice of Customer (VoC) analyst specialising in extracting granular claims from consumer reviews. Your job is to read raw reviews and tag every distinct claim, outcome, experience, or sentiment a reviewer expresses — at the most specific level possible.

RULES:
1. Extract ONE signal per entry. A single review may contain 5-15+ signals.
2. Each signal should be a specific, concrete claim — not a vague summary.
3. Preserve the reviewer's framing. If they say "my knees don't ache anymore" that's a joint pain signal, not a "health improvement" signal. Stay granular.
4. Tag each signal with a signal_type from this list:
   - OUTCOME: A result the reviewer experienced (weight loss, better sleep, pain relief, etc.)
   - EXPERIENCE: How they found using the product (ease of use, taste, routine fit, etc.)
   - SENTIMENT: An emotional or evaluative statement (satisfaction, disappointment, surprise, etc.)
   - CONTEXT: Background information about the reviewer (pre-existing conditions, prior products tried, what led them to purchase, etc.)
   - REFERRAL: How they discovered the product (radio ad, friend recommendation, social media, etc.)
   - TIMELINE: Any mention of how quickly or slowly results appeared
   - VALUE: Anything about price, cost, value for money, willingness to repurchase
5. Include a short VERBATIM QUOTE (max 15 words) from the review that anchors each signal.
6. If a review contains no extractable signals (e.g. just "Great product"), still extract what you can — that's a SENTIMENT signal.
7. review_id should use the format R-001, R-002, etc., assigned sequentially to each review in the order they appear. If one review produces 5 signals, all 5 share the same review_id."""

EXTRACT_USER_PROMPT_DEFAULT = """Here is the business context for this product/brand:

<business_context>
{BUSINESS_CONTEXT}
</business_context>

Here are the raw Trustpilot reviews to analyse:

<reviews>
{RAW_REVIEWS}
</reviews>

Extract every signal from every review following the rules in your instructions. Be exhaustive — I'd rather have too many signals than miss important ones. Return the JSON and nothing else."""

TAXONOMY_SYSTEM_PROMPT_DEFAULT = """You are a VoC taxonomy architect. Your job is to take a JSON array of extracted review signals and organise them into a clean, hierarchical topic taxonomy.

The taxonomy has exactly TWO levels:
- PARENT CATEGORY (e.g. "WEIGHT LOSS", "SLEEP QUALITY", "JOINT HEALTH")
- SUB-TOPIC (e.g. "Weight Loss Amount", "Inch Loss", "Clothing Size Change")

RULES FOR BUILDING THE TAXONOMY:

1. CLUSTER FROM THE BOTTOM UP. Start with the raw signals. Group signals that describe the same specific thing into a sub-topic. Then group related sub-topics under a parent category. Do NOT start with pre-conceived categories.

2. SUB-TOPIC NAMING: Each sub-topic label should be a clear, scannable name (2-5 words). Use the customer's framing where possible.

3. PARENT CATEGORY NAMING: Broad thematic buckets (1-3 words, ALL CAPS). Aim for 10-25 parent categories.

4. MINIMUM SIGNAL THRESHOLD: A sub-topic must be supported by signals from at least 2 different reviews. Single-review signals go in singletons.

5. OVERLAP RULES: If two sub-topics have >70% signal overlap, merge them. A signal CAN belong to two sub-topics if it genuinely spans both.

6. VERBATIM SELECTION: For each sub-topic, include the 3 best verbatim quotes. Each must include the review_id.

7. SPECIAL CATEGORIES TO WATCH FOR: REFERRAL SOURCE, PRIOR PRODUCT EXPERIENCE, PRE-EXISTING CONDITIONS, RESULTS TIMELINE, PRODUCT FEATURES, SATISFACTION/DISSATISFACTION.

IMPORTANT: review_ids in each topic should be the COMPLETE list of every review that contributed a signal. signal_count must match the length of review_ids (deduplicated). verbatims array: max 3 per sub-topic."""

TAXONOMY_USER_PROMPT_DEFAULT = """Here is the business context:

<business_context>
{BUSINESS_CONTEXT}
</business_context>

Here is the extracted signal data:

<signals>
{JSON_OUTPUT_FROM_PROMPT_1}
</signals>

Total reviews analysed: {REVIEW_COUNT}

Build the taxonomy following your rules. Cluster from the bottom up — don't impose categories, let them emerge from the signals. Return the JSON and nothing else."""

VALIDATE_SYSTEM_PROMPT_DEFAULT = """You are a VoC taxonomy editor. You receive a draft taxonomy in JSON and your job is to validate, refine, and produce the final version.

VALIDATION CHECKS:
1. COMPLETENESS: Are there signals without a home in the taxonomy?
2. OVERLAP: Are any two sub-topics or parent categories essentially the same? Merge them.
3. GRANULARITY: Sub-topics with 15+ signals — consider splitting. Categories with only 1 sub-topic — consider merging.
4. NAMING: Parallel structure, clear and scannable.
5. USEFULNESS: Is this useful for ad creative? Does it separate outcomes, context, discovery, and product attributes?
6. DATA INTEGRITY: signal_count matches review_ids length, all review_ids valid, verbatims match.

REFINEMENT ACTIONS: Merge overlapping, split overstuffed, rename unclear, reorder by strategic importance, kill empty categories.

IMPORTANT: coverage_pct = (total_signals_covered / total signals from extraction) * 100. Aim for 95%+. strategic_notes should contain 3-5 observations useful for ad creative strategy."""

VALIDATE_USER_PROMPT_DEFAULT = """Here is the business context:

<business_context>
{BUSINESS_CONTEXT}
</business_context>

Here is the draft taxonomy:

<draft_taxonomy>
{JSON_OUTPUT_FROM_PROMPT_2}
</draft_taxonomy>

Here is the original signal data for cross-reference:

<signals>
{JSON_OUTPUT_FROM_PROMPT_1}
</signals>

Validate, refine, and produce the final taxonomy. Be ruthless about overlap and naming clarity. Return the JSON and nothing else."""


def _get_default_prompts(db: Session) -> Dict[str, Optional[str]]:
    """Load live DB prompts or fall back to hardcoded constants."""
    purposes = {
        "product_context_extract": ("context_system", None),
        "voc_discover": ("discover_system", "discover_user"),
        "voc_code": ("code_system", "code_user"),
        "voc_refine": ("refine_system", "refine_user"),
        "voc_extract": ("extract_system", "extract_user"),
        "voc_taxonomy": ("taxonomy_system", "taxonomy_user"),
        "voc_validate": ("validate_system", "validate_user"),
    }
    hardcoded = {
        "context_system": DEFAULT_EXTRACT_SYSTEM_MSG,
        "discover_system": DISCOVER_SYSTEM_PROMPT,
        "discover_user": DISCOVER_USER_PROMPT,
        "code_system": CODE_SYSTEM_PROMPT,
        "code_user": CODE_USER_PROMPT,
        "refine_system": REFINE_SYSTEM_PROMPT,
        "refine_user": REFINE_USER_PROMPT,
        "extract_system": EXTRACT_SYSTEM_PROMPT_DEFAULT,
        "extract_user": EXTRACT_USER_PROMPT_DEFAULT,
        "taxonomy_system": TAXONOMY_SYSTEM_PROMPT_DEFAULT,
        "taxonomy_user": TAXONOMY_USER_PROMPT_DEFAULT,
        "validate_system": VALIDATE_SYSTEM_PROMPT_DEFAULT,
        "validate_user": VALIDATE_USER_PROMPT_DEFAULT,
    }
    result: Dict[str, Optional[str]] = dict(hardcoded)

    for purpose, (sys_key, user_key) in purposes.items():
        prompt = (
            db.query(Prompt)
            .filter(func.lower(Prompt.prompt_purpose) == purpose.lower(), Prompt.status == "live")
            .order_by(Prompt.version.desc(), Prompt.updated_at.desc())
            .first()
        )
        if prompt:
            if sys_key and prompt.system_message:
                result[sys_key] = prompt.system_message
            if user_key and prompt.prompt_message:
                result[user_key] = prompt.prompt_message

    return result


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/api/founder-admin/prompt-studio/scrape",
    response_model=ScrapeResponse,
)
def prompt_studio_scrape(
    body: ScrapeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Scrape Trustpilot reviews and persist as a leadgen run for later reload."""
    import traceback
    import uuid
    from datetime import datetime, timezone
    from app.services.leadgen_voc_service import upsert_leadgen_run_with_rows

    try:
        settings = get_settings()
        domain = _domain_from_url(body.url)
        company_name = (body.company_name or "").strip() or infer_company_name_from_domain(domain)
        company_url = normalize_url(body.url)

        logger.info("[scrape] Starting for domain=%s max_reviews=%s", domain, body.max_reviews)

        normalized_reviews = fetch_trustpilot_reviews_by_domain(
            settings=settings,
            domain=domain,
            max_reviews=body.max_reviews,
        )
        logger.info("[scrape] Got %d reviews from Apify", len(normalized_reviews))

        rows = build_pre_llm_process_voc_rows(
            normalized_reviews=normalized_reviews,
            company_name=company_name,
            company_domain=domain,
        )
        logger.info("[scrape] Built %d rows", len(rows))

        # Persist so the run appears in the "Load Existing Run" dropdown
        run_id = uuid.uuid4().hex
        upsert_leadgen_run_with_rows(
            db,
            run_id=run_id,
            work_email=f"studio@{domain}",
            company_domain=domain,
            company_url=company_url,
            company_name=company_name,
            review_count=len(rows),
            coding_enabled=False,
            coding_status="pending",
            generated_at=datetime.now(timezone.utc),
            payload={
                "source": "prompt_studio_scrape",
                "company_context": {
                    "name": company_name,
                    "source_url": company_url,
                    "domain": domain,
                },
            },
            rows=rows,
        )
        db.commit()
        logger.info("[scrape] Persisted run_id=%s with %d rows", run_id, len(rows))

        return ScrapeResponse(
            run_id=run_id,
            domain=domain,
            company_name=company_name,
            company_url=company_url,
            review_count=len(rows),
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[scrape] Unexpected error: %s\n%s", exc, traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Scrape failed: {exc}")


@router.get(
    "/api/founder-admin/prompt-studio/default-prompts",
    response_model=DefaultPromptsResponse,
)
def prompt_studio_get_default_prompts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Return default prompts (live DB versions or hardcoded fallbacks)."""
    return DefaultPromptsResponse(default_prompts=_get_default_prompts(db))


@router.get(
    "/api/founder-admin/prompt-studio/{run_id}/inputs",
    response_model=InputsResponse,
)
def prompt_studio_get_inputs(
    run_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Load reviews, company context, and default prompts for an existing run."""
    from app.services.leadgen_voc_service import get_leadgen_rows_as_process_voc_dicts, get_leadgen_run

    run = get_leadgen_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Lead-gen run not found")

    reviews = get_leadgen_rows_as_process_voc_dicts(db, run_id)
    payload = run.payload or {}
    company_context = payload.get("company_context")
    if not isinstance(company_context, dict):
        # Fallback for older scrape-only runs that lack company_context in payload
        company_context = {
            "name": run.company_name,
            "source_url": run.company_url,
            "domain": run.company_domain,
        }

    default_prompts = _get_default_prompts(db)
    pipeline_state = payload.get("pipeline_state")
    return InputsResponse(
        company_context=company_context,
        reviews=reviews,
        default_prompts=default_prompts,
        pipeline_state=pipeline_state if isinstance(pipeline_state, list) else None,
    )


@router.put(
    "/api/founder-admin/prompt-studio/{run_id}/pipeline",
)
def prompt_studio_save_pipeline(
    run_id: str,
    body: SavePipelineRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Save the full pipeline state (step outputs, prompts, etc.) to the run."""
    from app.services.leadgen_voc_service import get_leadgen_run

    run = get_leadgen_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Lead-gen run not found")

    payload = run.payload or {}
    payload["pipeline_state"] = body.pipeline_state
    run.payload = payload
    # Force SQLAlchemy to detect the JSONB mutation
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(run, "payload")
    db.commit()
    return {"status": "ok"}


class SaveStepOutputRequest(BaseModel):
    step_type: str
    step_order: int
    output: Dict[str, Any]
    elapsed_seconds: Optional[float] = None
    prompt_version_id: Optional[str] = None


class StepOutputItem(BaseModel):
    id: int
    step_type: str
    step_order: int
    output: Dict[str, Any]
    elapsed_seconds: Optional[float] = None
    prompt_version_id: Optional[str] = None
    created_at: str


class StepOutputsResponse(BaseModel):
    outputs: List[StepOutputItem]


@router.put(
    "/api/founder-admin/prompt-studio/{run_id}/step-output",
)
def prompt_studio_save_step_output(
    run_id: str,
    body: SaveStepOutputRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Save or update the output for a single pipeline step."""
    from app.services.leadgen_voc_service import get_leadgen_run

    run = get_leadgen_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Lead-gen run not found")

    # Upsert: replace existing output for this step_type + run_id
    existing = (
        db.query(LeadgenPipelineOutput)
        .filter(
            LeadgenPipelineOutput.run_id == run_id,
            LeadgenPipelineOutput.step_type == body.step_type,
        )
        .first()
    )
    if existing:
        existing.output = body.output
        existing.step_order = body.step_order
        existing.elapsed_seconds = body.elapsed_seconds
        if body.prompt_version_id:
            import uuid as _uuid
            existing.prompt_version_id = _uuid.UUID(body.prompt_version_id)
    else:
        import uuid as _uuid
        row = LeadgenPipelineOutput(
            run_id=run_id,
            step_type=body.step_type,
            step_order=body.step_order,
            output=body.output,
            elapsed_seconds=body.elapsed_seconds,
            prompt_version_id=_uuid.UUID(body.prompt_version_id) if body.prompt_version_id else None,
        )
        db.add(row)

    db.commit()
    return {"status": "ok"}


@router.get(
    "/api/founder-admin/prompt-studio/{run_id}/step-outputs",
    response_model=StepOutputsResponse,
)
def prompt_studio_get_step_outputs(
    run_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Load all saved step outputs for a run."""
    rows = (
        db.query(LeadgenPipelineOutput)
        .filter(LeadgenPipelineOutput.run_id == run_id)
        .order_by(LeadgenPipelineOutput.step_order)
        .all()
    )
    return StepOutputsResponse(
        outputs=[
            StepOutputItem(
                id=r.id,
                step_type=r.step_type,
                step_order=r.step_order,
                output=r.output,
                elapsed_seconds=r.elapsed_seconds,
                prompt_version_id=str(r.prompt_version_id) if r.prompt_version_id else None,
                created_at=r.created_at.isoformat() if r.created_at else "",
            )
            for r in rows
        ]
    )


@router.get(
    "/api/founder-admin/prompt-studio/prompt-versions/{prompt_purpose}",
    response_model=PromptVersionsResponse,
)
def prompt_studio_get_versions(
    prompt_purpose: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """List all prompt versions for a given purpose (e.g. voc_discover)."""
    prompts = (
        db.query(Prompt)
        .filter(func.lower(Prompt.prompt_purpose) == prompt_purpose.lower())
        .order_by(Prompt.version.desc())
        .all()
    )
    return PromptVersionsResponse(
        versions=[
            PromptVersionItem(
                id=str(p.id),
                name=p.name,
                version=p.version,
                status=p.status,
                system_message=p.system_message,
                prompt_message=p.prompt_message,
                llm_model=p.llm_model or "gpt-4o-mini",
                updated_at=p.updated_at.isoformat() if p.updated_at else None,
            )
            for p in prompts
        ]
    )


@router.post(
    "/api/founder-admin/prompt-studio/context",
    response_model=ContextStepResponse,
)
def prompt_studio_run_context(
    body: ContextStepRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Run the business context extraction step with a custom system prompt."""
    import httpx
    from anthropic import Anthropic

    settings = get_settings()
    normalized_url = normalize_url(body.url)
    if not normalized_url:
        raise HTTPException(status_code=400, detail="URL is required")

    crawler = WebCrawlerService()
    page_text = crawler.fetch_single_page(normalized_url, max_chars=10000)
    if not page_text:
        raise HTTPException(status_code=502, detail="Could not fetch content from URL")

    api_key = (getattr(settings, "anthropic_api_key", None) or "").strip()
    if not api_key:
        raise HTTPException(status_code=500, detail="Anthropic API key not configured")

    start = time.time()
    client = Anthropic(api_key=api_key, http_client=httpx.Client(timeout=180.0))
    response = client.messages.create(
        model=getattr(settings, "voc_coding_discover_model", "claude-sonnet-4-5-20250929"),
        max_tokens=4096,
        temperature=0.4,
        system=body.system_prompt,
        messages=[{"role": "user", "content": page_text}],
    )
    context_text = ""
    for block in response.content:
        text = getattr(block, "text", None)
        if text:
            context_text += text

    elapsed = round(time.time() - start, 2)
    product_name = extract_product_name(context_text, normalized_url)

    return ContextStepResponse(
        output={
            "name": product_name,
            "context_text": context_text,
            "source_url": normalized_url,
        },
        page_text=page_text,
        elapsed_seconds=elapsed,
    )


@router.post(
    "/api/founder-admin/prompt-studio/discover",
    response_model=StepResponse,
)
def prompt_studio_run_discover(
    body: DiscoverStepRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Run the DISCOVER codebook step with custom prompts."""
    settings = get_settings()
    reviews_text = _format_reviews_for_discovery(body.reviews)

    user_prompt = body.user_prompt_template.format(
        product_context=body.product_context,
        review_count=len(body.reviews),
        reviews=reviews_text,
    )

    start = time.time()
    try:
        output = call_claude_json_schema(
            settings=settings,
            model=getattr(settings, "voc_coding_discover_model", "claude-sonnet-4-5-20250929"),
            system_prompt=body.system_prompt,
            user_prompt=user_prompt,
            schema=DISCOVER_SCHEMA,
            temperature=float(getattr(settings, "voc_coding_discover_temperature", 0.6)),
            max_tokens=int(getattr(settings, "voc_coding_discover_max_tokens", 8192)),
        )
    except VocCodingChainError as exc:
        raise HTTPException(status_code=502, detail=f"[discover] {exc}")

    elapsed = round(time.time() - start, 2)
    return StepResponse(output=output, elapsed_seconds=elapsed)


@router.post(
    "/api/founder-admin/prompt-studio/code",
    response_model=StepResponse,
)
def prompt_studio_run_code(
    body: CodeStepRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Run the CODE reviews step with custom prompts and codebook."""
    settings = get_settings()
    reviews_text = _format_reviews_for_discovery(body.reviews)

    user_prompt = body.user_prompt_template.format(
        codebook=json.dumps(body.codebook, ensure_ascii=True),
        reviews=reviews_text,
    )

    start = time.time()
    try:
        output = call_claude_json_schema(
            settings=settings,
            model=getattr(settings, "voc_coding_code_model", "claude-haiku-4-5-20251001"),
            system_prompt=body.system_prompt,
            user_prompt=user_prompt,
            schema=CODE_SCHEMA,
            temperature=float(getattr(settings, "voc_coding_code_temperature", 0.2)),
            max_tokens=int(getattr(settings, "voc_coding_code_max_tokens", 4096)),
        )
    except VocCodingChainError as exc:
        raise HTTPException(status_code=502, detail=f"[code] {exc}")

    elapsed = round(time.time() - start, 2)

    coded_reviews = output.get("coded_reviews", [])
    stats = _compute_coding_stats(body.codebook, coded_reviews)
    no_matches = [r for r in coded_reviews if r.get("status") == "NO_MATCH"]

    return StepResponse(
        output={
            "coded_reviews": coded_reviews,
            "stats": stats,
            "no_matches": no_matches,
        },
        elapsed_seconds=elapsed,
    )


@router.post(
    "/api/founder-admin/prompt-studio/refine",
    response_model=StepResponse,
)
def prompt_studio_run_refine(
    body: RefineStepRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Run the REFINE codebook step with custom prompts."""
    settings = get_settings()

    user_prompt = body.user_prompt_template.format(
        product_context=body.product_context,
        codebook=json.dumps(body.codebook, ensure_ascii=True),
        stats=json.dumps(body.stats, ensure_ascii=True),
        no_matches=json.dumps(body.no_matches, ensure_ascii=True),
    )

    start = time.time()
    try:
        output = call_claude_json_schema(
            settings=settings,
            model=getattr(settings, "voc_coding_refine_model", "claude-sonnet-4-5-20250929"),
            system_prompt=body.system_prompt,
            user_prompt=user_prompt,
            schema=REFINE_SCHEMA,
            temperature=float(getattr(settings, "voc_coding_refine_temperature", 0.4)),
            max_tokens=int(getattr(settings, "voc_coding_refine_max_tokens", 8192)),
        )
    except VocCodingChainError as exc:
        raise HTTPException(status_code=502, detail=f"[refine] {exc}")

    elapsed = round(time.time() - start, 2)
    return StepResponse(output=output, elapsed_seconds=elapsed)


# ---------------------------------------------------------------------------
# JSON schemas for the new VoC taxonomy chain
# ---------------------------------------------------------------------------

EXTRACT_SCHEMA = {
    "type": "object",
    "properties": {
        "meta": {
            "type": "object",
            "properties": {
                "total_reviews_processed": {"type": "integer"},
                "total_signals_extracted": {"type": "integer"},
                "signal_type_counts": {"type": "object"},
            },
        },
        "signals": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "review_id": {"type": "string"},
                    "signal_type": {"type": "string"},
                    "description": {"type": "string"},
                    "verbatim": {"type": "string"},
                },
                "required": ["review_id", "signal_type", "description", "verbatim"],
            },
        },
    },
    "required": ["meta", "signals"],
}

_TOPIC_SCHEMA = {
    "type": "object",
    "properties": {
        "label": {"type": "string"},
        "signal_count": {"type": "integer"},
        "review_ids": {"type": "array", "items": {"type": "string"}},
        "verbatims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "review_id": {"type": "string"},
                    "text": {"type": "string"},
                },
                "required": ["review_id", "text"],
            },
        },
    },
    "required": ["label", "signal_count", "review_ids", "verbatims"],
}

TAXONOMY_SCHEMA = {
    "type": "object",
    "properties": {
        "meta": {"type": "object"},
        "categories": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "category": {"type": "string"},
                    "topics": {"type": "array", "items": _TOPIC_SCHEMA},
                },
                "required": ["category", "topics"],
            },
        },
        "singletons": {"type": "array"},
        "taxonomy_notes": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["meta", "categories"],
}

VALIDATE_SCHEMA = {
    "type": "object",
    "properties": {
        "meta": {"type": "object"},
        "categories": TAXONOMY_SCHEMA["properties"]["categories"],
        "singletons": {"type": "array"},
        "changes_made": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "action": {"type": "string"},
                    "detail": {"type": "string"},
                },
                "required": ["action", "detail"],
            },
        },
        "strategic_notes": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["meta", "categories", "changes_made", "strategic_notes"],
}


# ---------------------------------------------------------------------------
# New VoC taxonomy chain endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/api/founder-admin/prompt-studio/extract",
    response_model=StepResponse,
)
def prompt_studio_run_extract(
    body: ExtractStepRequest,
    stream: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Run the EXTRACT signals step — pulls granular signals from reviews."""
    settings = get_settings()
    reviews_text = _format_reviews_for_discovery(body.reviews)

    user_prompt = (body.user_prompt_template
        .replace("{BUSINESS_CONTEXT}", body.product_context)
        .replace("{RAW_REVIEWS}", reviews_text)
    )

    if not user_prompt.strip():
        raise HTTPException(
            status_code=422,
            detail="User prompt is empty after template substitution. "
                   "Ensure the prompt template contains text beyond just {BUSINESS_CONTEXT} and {RAW_REVIEWS} placeholders.",
        )

    llm_kwargs = dict(
        settings=settings,
        model=getattr(settings, "voc_coding_discover_model", "claude-sonnet-4-5-20250929"),
        system_prompt=body.system_prompt,
        user_prompt=user_prompt,
        schema=EXTRACT_SCHEMA,
        temperature=0.0,
        max_tokens=64000,
    )

    if stream:
        from app.services.voc_coding_chain_service import stream_claude_json_schema
        return StreamingResponse(
            stream_claude_json_schema(**llm_kwargs),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    start = time.time()
    try:
        output = call_claude_json_schema(**llm_kwargs)
    except VocCodingChainError as exc:
        raise HTTPException(status_code=502, detail=f"[extract] {exc}")

    elapsed = round(time.time() - start, 2)
    return StepResponse(output=output, elapsed_seconds=elapsed)


@router.post(
    "/api/founder-admin/prompt-studio/taxonomy",
    response_model=StepResponse,
)
def prompt_studio_run_taxonomy(
    body: TaxonomyStepRequest,
    stream: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Run the TAXONOMY construction step — clusters signals into categories/topics."""
    settings = get_settings()

    user_prompt = (body.user_prompt_template
        .replace("{BUSINESS_CONTEXT}", body.product_context)
        .replace("{JSON_OUTPUT_FROM_PROMPT_1}", json.dumps(body.signals, ensure_ascii=False))
        .replace("{REVIEW_COUNT}", str(len(body.signals.get("signals", []))))
    )

    llm_kwargs = dict(
        settings=settings,
        model=getattr(settings, "voc_coding_discover_model", "claude-sonnet-4-5-20250929"),
        system_prompt=body.system_prompt,
        user_prompt=user_prompt,
        schema=TAXONOMY_SCHEMA,
        temperature=0.0,
        max_tokens=64000,
    )

    if stream:
        from app.services.voc_coding_chain_service import stream_claude_json_schema
        return StreamingResponse(
            stream_claude_json_schema(**llm_kwargs),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    start = time.time()
    try:
        output = call_claude_json_schema(**llm_kwargs)
    except VocCodingChainError as exc:
        raise HTTPException(status_code=502, detail=f"[taxonomy] {exc}")

    elapsed = round(time.time() - start, 2)
    return StepResponse(output=output, elapsed_seconds=elapsed)


@router.post(
    "/api/founder-admin/prompt-studio/validate",
    response_model=StepResponse,
)
def prompt_studio_run_validate(
    body: ValidateStepRequest,
    stream: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Run the VALIDATE & refine step — validates taxonomy and produces final output."""
    settings = get_settings()

    user_prompt = (body.user_prompt_template
        .replace("{BUSINESS_CONTEXT}", body.product_context)
        .replace("{JSON_OUTPUT_FROM_PROMPT_2}", json.dumps(body.taxonomy, ensure_ascii=False))
        .replace("{JSON_OUTPUT_FROM_PROMPT_1}", json.dumps(body.signals, ensure_ascii=False))
    )

    llm_kwargs = dict(
        settings=settings,
        model=getattr(settings, "voc_coding_discover_model", "claude-sonnet-4-5-20250929"),
        system_prompt=body.system_prompt,
        user_prompt=user_prompt,
        schema=VALIDATE_SCHEMA,
        temperature=0.0,
        max_tokens=64000,
    )

    if stream:
        from app.services.voc_coding_chain_service import stream_claude_json_schema
        return StreamingResponse(
            stream_claude_json_schema(**llm_kwargs),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    start = time.time()
    try:
        output = call_claude_json_schema(**llm_kwargs)
    except VocCodingChainError as exc:
        raise HTTPException(status_code=502, detail=f"[validate] {exc}")

    elapsed = round(time.time() - start, 2)
    return StepResponse(output=output, elapsed_seconds=elapsed)


# ---------------------------------------------------------------------------
# Prompt 6: Creative generation
# ---------------------------------------------------------------------------

GENERATE_AD_SCHEMA = {
    "type": "object",
    "properties": {
        "topic_label": {"type": "string"},
        "ads": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "primary_text": {"type": "string"},
                    "headline": {"type": "string"},
                    "description": {"type": "string"},
                    "call_to_action": {
                        "type": "string",
                        "enum": [
                            "LEARN_MORE", "DOWNLOAD", "SHOP_NOW", "SIGN_UP",
                            "GET_QUOTE", "APPLY_NOW", "BOOK_NOW", "CONTACT_US",
                            "GET_OFFER", "SUBSCRIBE", "REQUEST_TIME",
                        ],
                    },
                    "destination_url": {"type": "string"},
                    "media": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string"},
                            "image_hash": {"type": ["string", "null"]},
                        },
                    },
                    "testType": {
                        "type": "string",
                        "enum": [
                            "Surprise", "Story", "Curiosity", "Guidance",
                            "Instructional", "Hyperbole", "Newness", "Ranking",
                            "Pattern Break", "Proof", "Mistake Avoidance", "Transformation",
                        ],
                    },
                    "origin": {"type": "string"},
                    "voc_evidence": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "strategic_memo": {"type": "string"},
                },
                "required": ["id", "primary_text", "headline", "description",
                             "call_to_action", "destination_url", "testType", "origin"],
            },
        },
    },
    "required": ["topic_label", "ads"],
}


class GenerateAdRequest(BaseModel):
    system_prompt: str
    user_prompt: str


@router.post(
    "/api/founder-admin/prompt-studio/generate-ad",
    response_model=StepResponse,
)
def prompt_studio_generate_ad(
    body: GenerateAdRequest,
    stream: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Generate Facebook ad concepts. Accepts a pre-assembled user prompt with full VoC data."""
    settings = get_settings()

    llm_kwargs = dict(
        settings=settings,
        model="claude-opus-4-6-20250904",
        system_prompt=body.system_prompt,
        user_prompt=body.user_prompt,
        schema=GENERATE_AD_SCHEMA,
        temperature=0.7,
        max_tokens=64000,
    )

    if stream:
        from app.services.voc_coding_chain_service import stream_claude_json_schema
        return StreamingResponse(
            stream_claude_json_schema(**llm_kwargs),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    start = time.time()
    try:
        output = call_claude_json_schema(**llm_kwargs)
    except VocCodingChainError as exc:
        raise HTTPException(status_code=502, detail=f"[generate-ad] {exc}")

    return StepResponse(output=output, elapsed_seconds=round(time.time() - start, 2))
