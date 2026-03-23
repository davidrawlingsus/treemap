from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from app.database import Base


class WidgetSurvey(Base):
    __tablename__ = "widget_surveys"
    __table_args__ = (
        UniqueConstraint("client_id", "handle", name="uq_widget_surveys_client_handle"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    handle = Column(String(128), nullable=False)
    title = Column(String(255), nullable=False)
    status = Column(String(32), nullable=False, default="active", index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.current_timestamp(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )


class WidgetSurveyVersion(Base):
    __tablename__ = "widget_survey_versions"
    __table_args__ = (
        UniqueConstraint("survey_id", "version_number", name="uq_widget_survey_versions_number"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    survey_id = Column(Integer, ForeignKey("widget_surveys.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    status = Column(String(32), nullable=False, default="draft", index=True)
    is_active = Column(Boolean, nullable=False, default=False, index=True)
    template_key = Column(String(64), nullable=True)
    starts_at = Column(DateTime(timezone=True), nullable=True)
    ends_at = Column(DateTime(timezone=True), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    settings_json = Column(JSONB, nullable=True)  # stores trigger_rules, url_targeting, frequency
    created_at = Column(DateTime(timezone=True), server_default=func.current_timestamp(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )


class WidgetSurveyQuestion(Base):
    __tablename__ = "widget_survey_questions"
    __table_args__ = (
        UniqueConstraint("survey_version_id", "question_key", name="uq_widget_survey_questions_key"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    survey_version_id = Column(
        Integer,
        ForeignKey("widget_survey_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_key = Column(String(64), nullable=False)
    title = Column(Text, nullable=False)
    answer_type = Column(String(32), nullable=False, default="single_line_text")
    is_required = Column(Boolean, nullable=False, default=False)
    is_enabled = Column(Boolean, nullable=False, default=True)
    options_json = Column(JSONB, nullable=True)
    settings_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.current_timestamp(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )


class WidgetSurveyQuestionOrder(Base):
    __tablename__ = "widget_survey_question_orders"
    __table_args__ = (
        UniqueConstraint("survey_version_id", "question_id", name="uq_widget_survey_q_order_question"),
        UniqueConstraint("survey_version_id", "position", name="uq_widget_survey_q_order_position"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    survey_version_id = Column(
        Integer,
        ForeignKey("widget_survey_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_id = Column(
        Integer,
        ForeignKey("widget_survey_questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.current_timestamp(), nullable=False)


class WidgetSurveyDisplayRule(Base):
    __tablename__ = "widget_survey_display_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    survey_version_id = Column(
        Integer,
        ForeignKey("widget_survey_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_question_id = Column(
        Integer,
        ForeignKey("widget_survey_questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_question_id = Column(
        Integer,
        ForeignKey("widget_survey_questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    operator = Column(String(32), nullable=False, default="equals")
    comparison_value = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.current_timestamp(), nullable=False)


class WidgetSurveyResponse(Base):
    __tablename__ = "widget_survey_responses"
    __table_args__ = (
        UniqueConstraint("client_id", "idempotency_key", name="uq_widget_survey_responses_idempotency"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    survey_id = Column(Integer, ForeignKey("widget_surveys.id", ondelete="SET NULL"), nullable=True, index=True)
    survey_version_id = Column(
        Integer,
        ForeignKey("widget_survey_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    idempotency_key = Column(String(128), nullable=False)
    site_domain = Column(String(255), nullable=True, index=True)
    page_url = Column(Text, nullable=True)
    customer_reference = Column(String(255), nullable=True)
    clarity_session_id = Column(String(128), nullable=True)
    clarity_project_id = Column(String(64), nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.current_timestamp(), nullable=False)


class WidgetSurveyResponseAnswer(Base):
    __tablename__ = "widget_survey_response_answers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    response_id = Column(Integer, ForeignKey("widget_survey_responses.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("widget_survey_questions.id", ondelete="SET NULL"), nullable=True, index=True)
    question_key = Column(String(64), nullable=True)
    answer_text = Column(Text, nullable=True)
    answer_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.current_timestamp(), nullable=False)


class WidgetSurveyHeartbeat(Base):
    __tablename__ = "widget_survey_heartbeats"
    __table_args__ = (
        UniqueConstraint("client_id", "page_url_hash", name="uq_widget_survey_heartbeats_client_page"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    page_url = Column(Text, nullable=False)
    page_url_hash = Column(String(64), nullable=False)  # SHA-256 of page_url for unique constraint
    last_seen_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.current_timestamp(), nullable=False)


class WidgetSurveyImpression(Base):
    __tablename__ = "widget_survey_impressions"
    __table_args__ = (
        UniqueConstraint("survey_version_id", "date", name="uq_widget_survey_impressions_version_date"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    survey_version_id = Column(
        Integer,
        ForeignKey("widget_survey_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    date = Column(Date, nullable=False)
    impression_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.current_timestamp(), nullable=False)
