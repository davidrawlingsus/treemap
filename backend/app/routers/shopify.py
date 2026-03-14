from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import ShopifyStoreConnection, ShopifySurveyResponseRaw
from app.schemas import ShopifySurveyIngestRequest, ShopifySurveyIngestResponse

router = APIRouter(prefix="/api/shopify", tags=["shopify"])


def _normalize_shop_domain(value: str) -> str:
    return value.strip().lower()


@router.post("/survey-responses/raw", response_model=ShopifySurveyIngestResponse, status_code=201)
def ingest_shopify_raw_survey_response(
    payload: ShopifySurveyIngestRequest,
    request: Request,
    db: Session = Depends(get_db),
    x_vizualizd_shopify_secret: str | None = Header(default=None),
):
    settings = get_settings()
    expected_secret = (settings.shopify_ingest_shared_secret or "").strip()
    if not expected_secret:
        raise HTTPException(status_code=503, detail="Shopify ingest secret is not configured")
    if not x_vizualizd_shopify_secret or x_vizualizd_shopify_secret.strip() != expected_secret:
        raise HTTPException(status_code=401, detail="Invalid Shopify ingest secret")

    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit():
        body_size = int(content_length)
        if body_size > settings.shopify_ingest_max_payload_bytes:
            raise HTTPException(status_code=413, detail="Payload too large")

    normalized_shop_domain = _normalize_shop_domain(payload.shop_domain)
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
