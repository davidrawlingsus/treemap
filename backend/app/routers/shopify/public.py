from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ShopifyStoreConnection, ShopifySurveyResponse, ShopifySurveyResponseRaw
from app.routers import shopify as shopify_router_module
from app.schemas.shopify import (
    ShopifyRuntimeSurveyEnvelope,
    ShopifySurveyDetailResponse,
    ShopifyStoreConnectionSyncRequest,
    ShopifyStoreTokenResponse,
    ShopifySurveyIngestRequest,
    ShopifySurveyIngestResponse,
    ShopifySurveyListItem,
    ShopifySurveyResponseIngestRequest,
    ShopifySurveyResponseIngestResponse,
    ShopifySurveyResponseList,
    ShopifySurveyTemplateItem,
    ShopifySurveyUpsertRequest,
)
from app.services.shopify import (
    delete_survey,
    get_active_runtime_survey,
    get_survey_detail,
    get_survey_templates,
    ingest_survey_response,
    list_survey_responses,
    list_surveys,
    normalize_shop_domain,
    publish_survey,
    require_shopify_ingest_secret,
    unpublish_survey,
    upsert_survey_draft,
)

router = APIRouter(prefix="/api/shopify", tags=["shopify"])


@router.post("/survey-responses/raw", response_model=ShopifySurveyIngestResponse, status_code=201)
def ingest_shopify_raw_survey_response(
    payload: ShopifySurveyIngestRequest,
    request: Request,
    db: Session = Depends(get_db),
    x_vizualizd_shopify_secret: str | None = Header(default=None),
):
    require_shopify_ingest_secret(
        x_vizualizd_shopify_secret,
        settings_getter=shopify_router_module.get_settings,
    )
    settings = shopify_router_module.get_settings()

    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit():
        body_size = int(content_length)
        if body_size > settings.shopify_ingest_max_payload_bytes:
            raise HTTPException(status_code=413, detail="Payload too large")

    normalized_shop_domain = normalize_shop_domain(payload.shop_domain)
    if not normalized_shop_domain:
        raise HTTPException(status_code=400, detail="shop_domain is required")

    existing = (
        db.query(ShopifySurveyResponseRaw)
        .filter(
            ShopifySurveyResponseRaw.shop_domain == normalized_shop_domain,
            ShopifySurveyResponseRaw.idempotency_key == payload.idempotency_key,
        )
        .first()
    )
    if existing:
        return ShopifySurveyIngestResponse(
            id=existing.id,
            shop_domain=existing.shop_domain,
            client_uuid=existing.client_uuid,
            deduplicated=True,
            submitted_at=existing.submitted_at,
        )

    store_connection = (
        db.query(ShopifyStoreConnection)
        .filter(ShopifyStoreConnection.shop_domain == normalized_shop_domain)
        .first()
    )
    client_uuid = store_connection.client_uuid if store_connection else None

    record = ShopifySurveyResponseRaw(
        shop_domain=normalized_shop_domain,
        idempotency_key=payload.idempotency_key,
        shopify_order_id=payload.shopify_order_id,
        order_gid=payload.order_gid,
        customer_reference=payload.customer_reference,
        survey_version=payload.survey_version,
        answers_json=payload.answers,
        extension_context_json=payload.extension_context,
        client_uuid=client_uuid,
        submitted_at=payload.submitted_at,
    )

    try:
        db.add(record)
        db.commit()
        db.refresh(record)
    except IntegrityError:
        db.rollback()
        deduped = (
            db.query(ShopifySurveyResponseRaw)
            .filter(
                ShopifySurveyResponseRaw.shop_domain == normalized_shop_domain,
                ShopifySurveyResponseRaw.idempotency_key == payload.idempotency_key,
            )
            .first()
        )
        if deduped:
            return ShopifySurveyIngestResponse(
                id=deduped.id,
                shop_domain=deduped.shop_domain,
                client_uuid=deduped.client_uuid,
                deduplicated=True,
                submitted_at=deduped.submitted_at,
            )
        raise HTTPException(status_code=409, detail="Duplicate Shopify survey submission")

    return ShopifySurveyIngestResponse(
        id=record.id,
        shop_domain=record.shop_domain,
        client_uuid=record.client_uuid,
        deduplicated=False,
        submitted_at=record.submitted_at,
    )


@router.post("/store-connections/sync", status_code=200)
def sync_shopify_store_connection(
    payload: ShopifyStoreConnectionSyncRequest,
    db: Session = Depends(get_db),
    x_vizualizd_shopify_secret: str | None = Header(default=None),
):
    require_shopify_ingest_secret(
        x_vizualizd_shopify_secret,
        settings_getter=shopify_router_module.get_settings,
    )
    normalized_shop_domain = normalize_shop_domain(payload.shop_domain)
    if not normalized_shop_domain:
        raise HTTPException(status_code=400, detail="shop_domain is required")

    existing = (
        db.query(ShopifyStoreConnection)
        .filter(ShopifyStoreConnection.shop_domain == normalized_shop_domain)
        .first()
    )
    now = datetime.now(timezone.utc)
    if existing is None:
        existing = ShopifyStoreConnection(
            shop_domain=normalized_shop_domain,
            status=payload.status,
            installed_at=payload.installed_at,
            uninstalled_at=payload.uninstalled_at,
        )
        db.add(existing)

    existing.status = payload.status
    if payload.installed_at is not None:
        existing.installed_at = payload.installed_at
    if payload.uninstalled_at is not None:
        existing.uninstalled_at = payload.uninstalled_at

    if payload.clear_offline_token:
        existing.offline_access_token = None
        existing.offline_access_scopes = None
        existing.token_updated_at = now
    elif payload.offline_access_token:
        existing.offline_access_token = payload.offline_access_token
        existing.offline_access_scopes = payload.offline_access_scopes
        existing.token_updated_at = now

    db.commit()
    db.refresh(existing)
    return {
        "shop_domain": existing.shop_domain,
        "status": existing.status,
        "has_offline_access_token": bool(existing.offline_access_token),
    }


@router.get("/store-connections/{shop_domain}/offline-token", response_model=ShopifyStoreTokenResponse)
def get_shopify_store_offline_token(
    shop_domain: str,
    db: Session = Depends(get_db),
    x_vizualizd_shopify_secret: str | None = Header(default=None),
):
    require_shopify_ingest_secret(
        x_vizualizd_shopify_secret,
        settings_getter=shopify_router_module.get_settings,
    )
    normalized_shop_domain = normalize_shop_domain(shop_domain)
    if not normalized_shop_domain:
        raise HTTPException(status_code=400, detail="shop_domain is required")

    existing = (
        db.query(ShopifyStoreConnection)
        .filter(ShopifyStoreConnection.shop_domain == normalized_shop_domain)
        .first()
    )
    if existing is None:
        raise HTTPException(status_code=404, detail="Shopify store connection not found")

    return ShopifyStoreTokenResponse(
        shop_domain=existing.shop_domain,
        has_offline_access_token=bool(existing.offline_access_token),
        offline_access_token=existing.offline_access_token,
        offline_access_scopes=existing.offline_access_scopes,
    )


@router.get("/survey-templates", response_model=list[ShopifySurveyTemplateItem])
def list_shopify_survey_templates(
    x_vizualizd_shopify_secret: str | None = Header(default=None),
):
    require_shopify_ingest_secret(
        x_vizualizd_shopify_secret,
        settings_getter=shopify_router_module.get_settings,
    )
    return get_survey_templates()


@router.get("/surveys/{shop_domain}", response_model=list[ShopifySurveyListItem])
def list_shopify_surveys(
    shop_domain: str,
    db: Session = Depends(get_db),
    x_vizualizd_shopify_secret: str | None = Header(default=None),
):
    require_shopify_ingest_secret(
        x_vizualizd_shopify_secret,
        settings_getter=shopify_router_module.get_settings,
    )
    normalized_shop_domain = normalize_shop_domain(shop_domain)
    if not normalized_shop_domain:
        raise HTTPException(status_code=400, detail="shop_domain is required")
    return list_surveys(db, normalized_shop_domain)


@router.post("/surveys/{shop_domain}", response_model=ShopifySurveyDetailResponse, status_code=201)
def create_shopify_survey(
    shop_domain: str,
    payload: ShopifySurveyUpsertRequest,
    db: Session = Depends(get_db),
    x_vizualizd_shopify_secret: str | None = Header(default=None),
):
    require_shopify_ingest_secret(
        x_vizualizd_shopify_secret,
        settings_getter=shopify_router_module.get_settings,
    )
    try:
        return upsert_survey_draft(db, shop_domain, payload, survey_id=None)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))


@router.get("/surveys/{shop_domain}/{survey_id}", response_model=ShopifySurveyDetailResponse)
def get_shopify_survey(
    shop_domain: str,
    survey_id: int,
    db: Session = Depends(get_db),
    x_vizualizd_shopify_secret: str | None = Header(default=None),
):
    require_shopify_ingest_secret(
        x_vizualizd_shopify_secret,
        settings_getter=shopify_router_module.get_settings,
    )
    try:
        return get_survey_detail(db, shop_domain, survey_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))


@router.put("/surveys/{shop_domain}/{survey_id}", response_model=ShopifySurveyDetailResponse)
def update_shopify_survey(
    shop_domain: str,
    survey_id: int,
    payload: ShopifySurveyUpsertRequest,
    db: Session = Depends(get_db),
    x_vizualizd_shopify_secret: str | None = Header(default=None),
):
    require_shopify_ingest_secret(
        x_vizualizd_shopify_secret,
        settings_getter=shopify_router_module.get_settings,
    )
    try:
        return upsert_survey_draft(db, shop_domain, payload, survey_id=survey_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))


@router.post("/surveys/{shop_domain}/{survey_id}/publish", response_model=ShopifySurveyDetailResponse)
def publish_shopify_survey_route(
    shop_domain: str,
    survey_id: int,
    db: Session = Depends(get_db),
    x_vizualizd_shopify_secret: str | None = Header(default=None),
):
    require_shopify_ingest_secret(
        x_vizualizd_shopify_secret,
        settings_getter=shopify_router_module.get_settings,
    )
    try:
        return publish_survey(db, shop_domain, survey_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))


@router.post("/surveys/{shop_domain}/{survey_id}/unpublish", response_model=ShopifySurveyDetailResponse)
def unpublish_shopify_survey_route(
    shop_domain: str,
    survey_id: int,
    db: Session = Depends(get_db),
    x_vizualizd_shopify_secret: str | None = Header(default=None),
):
    require_shopify_ingest_secret(
        x_vizualizd_shopify_secret,
        settings_getter=shopify_router_module.get_settings,
    )
    try:
        return unpublish_survey(db, shop_domain, survey_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))


@router.delete("/surveys/{shop_domain}/{survey_id}", status_code=204)
def delete_shopify_survey_route(
    shop_domain: str,
    survey_id: int,
    db: Session = Depends(get_db),
    x_vizualizd_shopify_secret: str | None = Header(default=None),
):
    require_shopify_ingest_secret(
        x_vizualizd_shopify_secret,
        settings_getter=shopify_router_module.get_settings,
    )
    try:
        delete_survey(db, shop_domain, survey_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))


@router.get("/surveys/{shop_domain}/{survey_id}/responses", response_model=ShopifySurveyResponseList)
def list_shopify_survey_responses_route(
    shop_domain: str,
    survey_id: int,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    x_vizualizd_shopify_secret: str | None = Header(default=None),
):
    require_shopify_ingest_secret(
        x_vizualizd_shopify_secret,
        settings_getter=shopify_router_module.get_settings,
    )
    return list_survey_responses(db, shop_domain, survey_id, limit=limit, offset=offset)


@router.get("/survey-runtime/active", response_model=ShopifyRuntimeSurveyEnvelope)
def get_shopify_active_runtime_survey(
    shop_domain: str = Query(..., min_length=3),
    db: Session = Depends(get_db),
    x_vizualizd_shopify_secret: str | None = Header(default=None),
):
    require_shopify_ingest_secret(
        x_vizualizd_shopify_secret,
        settings_getter=shopify_router_module.get_settings,
    )
    survey = get_active_runtime_survey(db, shop_domain)
    return ShopifyRuntimeSurveyEnvelope(survey=survey)


@router.post("/survey-responses", response_model=ShopifySurveyResponseIngestResponse, status_code=201)
def ingest_shopify_normalized_survey_response(
    payload: ShopifySurveyResponseIngestRequest,
    db: Session = Depends(get_db),
    x_vizualizd_shopify_secret: str | None = Header(default=None),
):
    require_shopify_ingest_secret(
        x_vizualizd_shopify_secret,
        settings_getter=shopify_router_module.get_settings,
    )
    try:
        return ingest_survey_response(db, payload)
    except IntegrityError:
        db.rollback()
        existing = (
            db.query(ShopifySurveyResponse)
            .filter(
                ShopifySurveyResponse.shop_domain == normalize_shop_domain(payload.shop_domain),
                ShopifySurveyResponse.idempotency_key == payload.idempotency_key,
            )
            .first()
        )
        if existing:
            return ShopifySurveyResponseIngestResponse(
                id=existing.id,
                shop_domain=existing.shop_domain,
                survey_id=existing.survey_id,
                survey_version_id=existing.survey_version_id,
                deduplicated=True,
                submitted_at=existing.submitted_at,
            )
        raise HTTPException(status_code=409, detail="Duplicate Shopify survey submission")
