from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# ── Draft / Upsert schemas ──────────────────────────────────────────


class WidgetSurveyQuestionDraft(BaseModel):
    question_key: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1)
    answer_type: str = Field(default="single_line_text", min_length=1, max_length=32)
    is_required: bool = False
    is_enabled: bool = True
    position: int = Field(default=0, ge=0)
    options: list[str] = Field(default_factory=list)
    settings: dict[str, Any] = Field(default_factory=dict)


class WidgetSurveyDisplayRuleDraft(BaseModel):
    target_question_key: str = Field(min_length=1, max_length=64)
    source_question_key: str = Field(min_length=1, max_length=64)
    operator: str = Field(default="equals", min_length=1, max_length=32)
    comparison_value: str = Field(min_length=1, max_length=255)


class WidgetSurveyUrlTargeting(BaseModel):
    mode: str = Field(default="contains", pattern=r"^(contains|regex)$")
    patterns: list[str] = Field(default_factory=list)


class WidgetSurveyTriggerRules(BaseModel):
    type: str = Field(default="immediate", pattern=r"^(immediate|delay|exit_intent)$")
    delay_ms: int | None = Field(default=None, ge=0)


class WidgetSurveyFrequency(BaseModel):
    mode: str = Field(default="until_answered", pattern=r"^(once|until_answered|every_n_days)$")
    days: int | None = Field(default=None, ge=1)


class WidgetSurveyDraftVersionPayload(BaseModel):
    template_key: str | None = Field(default=None, max_length=64)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    settings: dict[str, Any] = Field(default_factory=dict)
    url_targeting: WidgetSurveyUrlTargeting = Field(default_factory=WidgetSurveyUrlTargeting)
    trigger_rules: WidgetSurveyTriggerRules = Field(default_factory=WidgetSurveyTriggerRules)
    frequency: WidgetSurveyFrequency = Field(default_factory=WidgetSurveyFrequency)
    questions: list[WidgetSurveyQuestionDraft] = Field(default_factory=list)
    display_rules: list[WidgetSurveyDisplayRuleDraft] = Field(default_factory=list)


class WidgetSurveyUpsertRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    status: str = Field(default="active", min_length=1, max_length=32)
    draft_version: WidgetSurveyDraftVersionPayload


# ── Response schemas (admin) ─────────────────────────────────────────


class WidgetSurveyQuestionResponse(BaseModel):
    id: int
    question_key: str
    title: str
    answer_type: str
    is_required: bool
    is_enabled: bool
    position: int
    options: list[str] = Field(default_factory=list)
    settings: dict[str, Any] = Field(default_factory=dict)


class WidgetSurveyDisplayRuleResponse(BaseModel):
    id: int
    target_question_id: int
    target_question_key: str
    source_question_id: int
    source_question_key: str
    operator: str
    comparison_value: str


class WidgetSurveyVersionResponse(BaseModel):
    id: int
    version_number: int
    status: str
    is_active: bool
    template_key: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    published_at: datetime | None = None
    settings: dict[str, Any] = Field(default_factory=dict)
    url_targeting: WidgetSurveyUrlTargeting = Field(default_factory=WidgetSurveyUrlTargeting)
    trigger_rules: WidgetSurveyTriggerRules = Field(default_factory=WidgetSurveyTriggerRules)
    frequency: WidgetSurveyFrequency = Field(default_factory=WidgetSurveyFrequency)
    questions: list[WidgetSurveyQuestionResponse] = Field(default_factory=list)
    display_rules: list[WidgetSurveyDisplayRuleResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class WidgetSurveyListItem(BaseModel):
    id: int
    client_id: UUID
    handle: str
    title: str
    status: str
    description: str | None = None
    active_version_id: int | None = None
    active_version_number: int | None = None
    impression_count: int = 0
    response_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WidgetSurveyDetailResponse(BaseModel):
    id: int
    client_id: UUID
    handle: str
    title: str
    status: str
    description: str | None = None
    draft_version: WidgetSurveyVersionResponse | None = None
    active_version: WidgetSurveyVersionResponse | None = None
    created_at: datetime
    updated_at: datetime


# ── Runtime schemas (widget JS fetches these) ────────────────────────


class WidgetRuntimeSurveyResponse(BaseModel):
    survey_id: int
    survey_title: str
    survey_description: str | None = None
    widget_title: str | None = None
    submit_label: str | None = None
    survey_version_id: int
    survey_version_number: int
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    settings: dict[str, Any] = Field(default_factory=dict)
    url_targeting: WidgetSurveyUrlTargeting = Field(default_factory=WidgetSurveyUrlTargeting)
    trigger_rules: WidgetSurveyTriggerRules = Field(default_factory=WidgetSurveyTriggerRules)
    frequency: WidgetSurveyFrequency = Field(default_factory=WidgetSurveyFrequency)
    clarity_project_id: str | None = None
    questions: list[WidgetSurveyQuestionResponse] = Field(default_factory=list)
    display_rules: list[WidgetSurveyDisplayRuleResponse] = Field(default_factory=list)


class WidgetRuntimeSurveyEnvelope(BaseModel):
    survey: WidgetRuntimeSurveyResponse | None = None


# ── Response ingest schemas (widget submits these) ───────────────────


class WidgetResponseAnswerIn(BaseModel):
    question_id: int | None = None
    question_key: str | None = Field(default=None, max_length=64)
    answer_text: str | None = None
    answer_json: dict[str, Any] | list[Any] | str | int | float | bool | None = None


class WidgetSurveyResponseIngestRequest(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=128)
    survey_id: int | None = None
    survey_version_id: int | None = None
    site_domain: str | None = Field(default=None, max_length=255)
    page_url: str | None = None
    customer_reference: str | None = Field(default=None, max_length=255)
    clarity_session_id: str | None = Field(default=None, max_length=128)
    clarity_project_id: str | None = Field(default=None, max_length=64)
    clarity_project_id_source: str | None = Field(default=None, pattern=r"^(configured|detected)$")
    clarity_replay_url: str | None = Field(default=None, max_length=512)
    answers: list[WidgetResponseAnswerIn] = Field(default_factory=list)
    submitted_at: datetime


class WidgetSurveyResponseIngestResponse(BaseModel):
    id: int
    survey_id: int | None = None
    survey_version_id: int | None = None
    deduplicated: bool = False
    submitted_at: datetime


# ── Response listing schemas ─────────────────────────────────────────


class WidgetSurveyResponseAnswerItem(BaseModel):
    id: int
    question_id: int | None = None
    question_key: str | None = None
    answer_text: str | None = None
    answer_json: Any = None


class WidgetSurveyResponseItem(BaseModel):
    id: int
    survey_id: int | None = None
    survey_version_id: int | None = None
    site_domain: str | None = None
    page_url: str | None = None
    customer_reference: str | None = None
    clarity_session_id: str | None = None
    clarity_project_id: str | None = None
    clarity_replay_url: str | None = None
    submitted_at: datetime
    answers: list[WidgetSurveyResponseAnswerItem] = Field(default_factory=list)


class WidgetSurveyResponseList(BaseModel):
    items: list[WidgetSurveyResponseItem]
    total: int


# ── Heartbeat / impression / stats schemas ───────────────────────────


class WidgetSurveyHeartbeatRequest(BaseModel):
    page_url: str = Field(min_length=1)


class WidgetSurveyImpressionRequest(BaseModel):
    survey_id: int
    survey_version_id: int
    page_url: str | None = None


class WidgetSurveyHeartbeatItem(BaseModel):
    page_url: str
    last_seen_at: datetime


class WidgetSurveyInstallationStatus(BaseModel):
    is_installed: bool
    pages: list[WidgetSurveyHeartbeatItem] = Field(default_factory=list)


class WidgetSurveyStats(BaseModel):
    impression_count: int = 0
    response_count: int = 0
    response_rate: float | None = None
    detected_clarity_project_id: str | None = None
