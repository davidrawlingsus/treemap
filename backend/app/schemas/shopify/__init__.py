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


class ShopifyStoreConnectionSyncRequest(BaseModel):
    shop_domain: str = Field(min_length=3, max_length=255)
    status: str = Field(default="active", min_length=1, max_length=50)
    installed_at: datetime | None = None
    uninstalled_at: datetime | None = None
    offline_access_token: str | None = Field(default=None, max_length=512)
    offline_access_scopes: str | None = Field(default=None, max_length=512)
    clear_offline_token: bool = False


class ShopifyStoreTokenResponse(BaseModel):
    shop_domain: str
    has_offline_access_token: bool
    offline_access_token: str | None = None
    offline_access_scopes: str | None = None


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


class ShopifySurveyQuestionDraft(BaseModel):
    question_key: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1)
    answer_type: str = Field(default="single_line_text", min_length=1, max_length=32)
    is_required: bool = False
    is_enabled: bool = True
    position: int = Field(default=0, ge=0)
    options: list[str] = Field(default_factory=list)
    settings: dict[str, Any] = Field(default_factory=dict)


class ShopifySurveyDisplayRuleDraft(BaseModel):
    target_question_key: str = Field(min_length=1, max_length=64)
    source_question_key: str = Field(min_length=1, max_length=64)
    operator: str = Field(default="equals", min_length=1, max_length=32)
    comparison_value: str = Field(min_length=1, max_length=255)


class ShopifySurveyDraftVersionPayload(BaseModel):
    template_key: str | None = Field(default=None, max_length=64)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    settings: dict[str, Any] = Field(default_factory=dict)
    questions: list[ShopifySurveyQuestionDraft] = Field(default_factory=list)
    display_rules: list[ShopifySurveyDisplayRuleDraft] = Field(default_factory=list)


class ShopifySurveyUpsertRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    status: str = Field(default="active", min_length=1, max_length=32)
    draft_version: ShopifySurveyDraftVersionPayload


class ShopifySurveyListItem(BaseModel):
    id: int
    shop_domain: str
    handle: str
    title: str
    status: str
    description: str | None = None
    active_version_id: int | None = None
    active_version_number: int | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ShopifySurveyQuestionResponse(BaseModel):
    id: int
    question_key: str
    title: str
    answer_type: str
    is_required: bool
    is_enabled: bool
    position: int
    options: list[str] = Field(default_factory=list)
    settings: dict[str, Any] = Field(default_factory=dict)


class ShopifySurveyDisplayRuleResponse(BaseModel):
    id: int
    target_question_id: int
    target_question_key: str
    source_question_id: int
    source_question_key: str
    operator: str
    comparison_value: str


class ShopifySurveyVersionResponse(BaseModel):
    id: int
    version_number: int
    status: str
    is_active: bool
    template_key: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    published_at: datetime | None = None
    settings: dict[str, Any] = Field(default_factory=dict)
    questions: list[ShopifySurveyQuestionResponse] = Field(default_factory=list)
    display_rules: list[ShopifySurveyDisplayRuleResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ShopifySurveyDetailResponse(BaseModel):
    id: int
    shop_domain: str
    handle: str
    title: str
    status: str
    description: str | None = None
    draft_version: ShopifySurveyVersionResponse | None = None
    active_version: ShopifySurveyVersionResponse | None = None
    created_at: datetime
    updated_at: datetime


class ShopifySurveyTemplateQuestion(BaseModel):
    question_key: str
    title: str
    answer_type: str
    is_required: bool = False
    options: list[str] = Field(default_factory=list)


class ShopifySurveyTemplateItem(BaseModel):
    key: str
    name: str
    description: str
    questions: list[ShopifySurveyTemplateQuestion]
    settings: dict = Field(default_factory=dict)


class ShopifyRuntimeSurveyResponse(BaseModel):
    survey_id: int
    survey_title: str
    survey_description: str | None = None
    survey_version_id: int
    survey_version_number: int
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    settings: dict[str, Any] = Field(default_factory=dict)
    questions: list[ShopifySurveyQuestionResponse] = Field(default_factory=list)
    display_rules: list[ShopifySurveyDisplayRuleResponse] = Field(default_factory=list)


class ShopifyRuntimeSurveyEnvelope(BaseModel):
    survey: ShopifyRuntimeSurveyResponse | None = None


class ShopifyResponseAnswerIn(BaseModel):
    question_id: int | None = None
    question_key: str | None = Field(default=None, max_length=64)
    answer_text: str | None = None
    answer_json: dict[str, Any] | list[Any] | str | int | float | bool | None = None


class ShopifySurveyResponseIngestRequest(BaseModel):
    shop_domain: str = Field(min_length=3, max_length=255)
    idempotency_key: str = Field(min_length=8, max_length=128)
    survey_id: int | None = None
    survey_version_id: int | None = None
    shopify_order_id: str | None = Field(default=None, max_length=255)
    order_gid: str | None = Field(default=None, max_length=255)
    customer_reference: str | None = Field(default=None, max_length=255)
    answers: list[ShopifyResponseAnswerIn] = Field(default_factory=list)
    extension_context: dict[str, Any] | None = None
    order_context: dict[str, Any] | None = None
    submitted_at: datetime


class ShopifySurveyResponseIngestResponse(BaseModel):
    id: int
    shop_domain: str
    survey_id: int | None = None
    survey_version_id: int | None = None
    deduplicated: bool = False
    submitted_at: datetime


class ShopifySurveyResponseAnswerItem(BaseModel):
    id: int
    question_id: int | None = None
    question_key: str | None = None
    answer_text: str | None = None
    answer_json: Any = None


class ShopifySurveyResponseItem(BaseModel):
    id: int
    survey_id: int | None = None
    survey_version_id: int | None = None
    shopify_order_id: str | None = None
    customer_reference: str | None = None
    submitted_at: datetime
    answers: list[ShopifySurveyResponseAnswerItem] = Field(default_factory=list)
    order_context: dict[str, Any] | None = None


class ShopifySurveyResponseList(BaseModel):
    items: list[ShopifySurveyResponseItem]
    total: int


__all__ = [
    "ShopifySurveyIngestRequest",
    "ShopifySurveyIngestResponse",
    "ShopifyStoreConnectionSyncRequest",
    "ShopifyStoreTokenResponse",
    "ShopifyStoreConnectionBase",
    "ShopifyStoreConnectionCreate",
    "ShopifyStoreConnectionResponse",
    "ShopifySurveyRawResponseItem",
    "ShopifySurveyRawResponseList",
    "ShopifySurveyQuestionDraft",
    "ShopifySurveyDisplayRuleDraft",
    "ShopifySurveyDraftVersionPayload",
    "ShopifySurveyUpsertRequest",
    "ShopifySurveyListItem",
    "ShopifySurveyQuestionResponse",
    "ShopifySurveyDisplayRuleResponse",
    "ShopifySurveyVersionResponse",
    "ShopifySurveyDetailResponse",
    "ShopifySurveyTemplateQuestion",
    "ShopifySurveyTemplateItem",
    "ShopifyRuntimeSurveyResponse",
    "ShopifyRuntimeSurveyEnvelope",
    "ShopifyResponseAnswerIn",
    "ShopifySurveyResponseIngestRequest",
    "ShopifySurveyResponseIngestResponse",
    "ShopifySurveyResponseAnswerItem",
    "ShopifySurveyResponseItem",
    "ShopifySurveyResponseList",
]
