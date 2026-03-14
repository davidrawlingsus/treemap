from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ShopifySurveyIngestRequest(BaseModel):
    shop_domain: str = Field(min_length=3, max_length=255)
    idempotency_key: str = Field(min_length=8, max_length=128)
    shopify_order_id: str | None = Field(default=None, max_length=255)
    order_gid: str | None = Field(default=None, max_length=255)
    customer_reference: str | None = Field(default=None, max_length=255)
    survey_version: str = Field(default="v1", min_length=1, max_length=50)
    answers: dict[str, Any]
    extension_context: dict[str, Any] | None = None
    submitted_at: datetime


class ShopifySurveyIngestResponse(BaseModel):
    id: int
    shop_domain: str
    client_uuid: UUID | None = None
    deduplicated: bool = False
    submitted_at: datetime


class ShopifyStoreConnectionBase(BaseModel):
    shop_domain: str = Field(min_length=3, max_length=255)
    client_uuid: UUID | None = None
    status: str = Field(default="active", min_length=1, max_length=50)
    installed_at: datetime | None = None
    uninstalled_at: datetime | None = None


class ShopifyStoreConnectionCreate(ShopifyStoreConnectionBase):
    pass


class ShopifyStoreConnectionResponse(ShopifyStoreConnectionBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ShopifySurveyRawResponseItem(BaseModel):
    id: int
    shop_domain: str
    idempotency_key: str
    shopify_order_id: str | None = None
    order_gid: str | None = None
    customer_reference: str | None = None
    survey_version: str
    answers_json: dict[str, Any]
    extension_context_json: dict[str, Any] | None = None
    client_uuid: UUID | None = None
    submitted_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class ShopifySurveyRawResponseList(BaseModel):
    items: list[ShopifySurveyRawResponseItem]
    total: int
