from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import get_current_active_founder
from app.database import get_db
from app.models import Client, ShopifyStoreConnection, ShopifySurveyResponseRaw, User
from app.schemas import (
    ShopifyStoreConnectionCreate,
    ShopifyStoreConnectionResponse,
    ShopifySurveyRawResponseItem,
    ShopifySurveyRawResponseList,
)
from app.services.shopify import normalize_shop_domain

router = APIRouter()


@router.get(
    "/api/founder-admin/shopify/store-connections",
    response_model=list[ShopifyStoreConnectionResponse],
)
def founder_list_shopify_store_connections(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    connections = (
        db.query(ShopifyStoreConnection)
        .order_by(ShopifyStoreConnection.created_at.desc(), ShopifyStoreConnection.id.desc())
        .all()
    )
    return [ShopifyStoreConnectionResponse.model_validate(connection) for connection in connections]


@router.post(
    "/api/founder-admin/shopify/store-connections",
    response_model=ShopifyStoreConnectionResponse,
    status_code=201,
)
def founder_upsert_shopify_store_connection(
    payload: ShopifyStoreConnectionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    normalized_shop_domain = normalize_shop_domain(payload.shop_domain)
    if not normalized_shop_domain:
        raise HTTPException(status_code=400, detail="shop_domain is required")

    if payload.client_uuid is not None:
        client = db.query(Client).filter(Client.id == payload.client_uuid).first()
        if client is None:
            raise HTTPException(status_code=404, detail="Client not found")

    existing = (
        db.query(ShopifyStoreConnection)
        .filter(ShopifyStoreConnection.shop_domain == normalized_shop_domain)
        .first()
    )
    if existing:
        existing.client_uuid = payload.client_uuid
        existing.status = payload.status
        existing.installed_at = payload.installed_at
        existing.uninstalled_at = payload.uninstalled_at
        db.commit()
        db.refresh(existing)
        return ShopifyStoreConnectionResponse.model_validate(existing)

    connection = ShopifyStoreConnection(
        shop_domain=normalized_shop_domain,
        client_uuid=payload.client_uuid,
        status=payload.status,
        installed_at=payload.installed_at,
        uninstalled_at=payload.uninstalled_at,
    )
    try:
        db.add(connection)
        db.commit()
        db.refresh(connection)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Shop domain already mapped")

    return ShopifyStoreConnectionResponse.model_validate(connection)


@router.delete("/api/founder-admin/shopify/store-connections/{shop_domain}", status_code=204)
def founder_delete_shopify_store_connection(
    shop_domain: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    normalized_shop_domain = normalize_shop_domain(shop_domain)
    existing = (
        db.query(ShopifyStoreConnection)
        .filter(ShopifyStoreConnection.shop_domain == normalized_shop_domain)
        .first()
    )
    if existing is None:
        raise HTTPException(status_code=404, detail="Shopify store connection not found")

    db.delete(existing)
    db.commit()
    return Response(status_code=204)


@router.get(
    "/api/founder-admin/shopify/survey-responses/raw",
    response_model=ShopifySurveyRawResponseList,
)
def founder_list_shopify_raw_survey_responses(
    client_uuid: UUID | None = None,
    shop_domain: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    query = db.query(ShopifySurveyResponseRaw)

    if client_uuid is not None:
        query = query.filter(ShopifySurveyResponseRaw.client_uuid == client_uuid)
    if shop_domain:
        query = query.filter(ShopifySurveyResponseRaw.shop_domain == normalize_shop_domain(shop_domain))

    total = query.count()
    rows = (
        query.order_by(ShopifySurveyResponseRaw.submitted_at.desc(), ShopifySurveyResponseRaw.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return ShopifySurveyRawResponseList(
        items=[ShopifySurveyRawResponseItem.model_validate(row) for row in rows],
        total=total,
    )
