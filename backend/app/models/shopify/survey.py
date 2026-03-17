from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.database import Base


class ShopifySurvey(Base):
    __tablename__ = "shopify_surveys"
    __table_args__ = (
        UniqueConstraint("shop_domain", "handle", name="uq_shopify_surveys_shop_handle"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    shop_domain = Column(String(255), nullable=False, index=True)
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


class ShopifySurveyVersion(Base):
    __tablename__ = "shopify_survey_versions"
    __table_args__ = (
        UniqueConstraint("survey_id", "version_number", name="uq_shopify_survey_versions_number"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    shop_domain = Column(String(255), nullable=False, index=True)
    survey_id = Column(Integer, ForeignKey("shopify_surveys.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    status = Column(String(32), nullable=False, default="draft", index=True)
    is_active = Column(Boolean, nullable=False, default=False, index=True)
    template_key = Column(String(64), nullable=True)
    starts_at = Column(DateTime(timezone=True), nullable=True)
    ends_at = Column(DateTime(timezone=True), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    settings_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.current_timestamp(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )


class ShopifySurveyQuestion(Base):
    __tablename__ = "shopify_survey_questions"
    __table_args__ = (
        UniqueConstraint("survey_version_id", "question_key", name="uq_shopify_survey_questions_key"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    shop_domain = Column(String(255), nullable=False, index=True)
    survey_version_id = Column(
        Integer,
        ForeignKey("shopify_survey_versions.id", ondelete="CASCADE"),
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


class ShopifySurveyQuestionOrder(Base):
    __tablename__ = "shopify_survey_question_orders"
    __table_args__ = (
        UniqueConstraint("survey_version_id", "question_id", name="uq_shopify_survey_q_order_question"),
        UniqueConstraint("survey_version_id", "position", name="uq_shopify_survey_q_order_position"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    shop_domain = Column(String(255), nullable=False, index=True)
    survey_version_id = Column(
        Integer,
        ForeignKey("shopify_survey_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_id = Column(
        Integer,
        ForeignKey("shopify_survey_questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.current_timestamp(), nullable=False)


class ShopifySurveyDisplayRule(Base):
    __tablename__ = "shopify_survey_display_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    shop_domain = Column(String(255), nullable=False, index=True)
    survey_version_id = Column(
        Integer,
        ForeignKey("shopify_survey_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_question_id = Column(
        Integer,
        ForeignKey("shopify_survey_questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_question_id = Column(
        Integer,
        ForeignKey("shopify_survey_questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    operator = Column(String(32), nullable=False, default="equals")
    comparison_value = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.current_timestamp(), nullable=False)


class ShopifySurveyResponse(Base):
    __tablename__ = "shopify_survey_responses"
    __table_args__ = (
        UniqueConstraint("shop_domain", "idempotency_key", name="uq_shopify_survey_responses_idempotency"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    shop_domain = Column(String(255), nullable=False, index=True)
    survey_id = Column(Integer, ForeignKey("shopify_surveys.id", ondelete="SET NULL"), nullable=True, index=True)
    survey_version_id = Column(
        Integer,
        ForeignKey("shopify_survey_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    idempotency_key = Column(String(128), nullable=False)
    shopify_order_id = Column(String(255), nullable=True, index=True)
    order_gid = Column(String(255), nullable=True)
    customer_reference = Column(String(255), nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=False)
    extension_context_json = Column(JSONB, nullable=True)
    order_context_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.current_timestamp(), nullable=False)


class ShopifySurveyResponseAnswer(Base):
    __tablename__ = "shopify_survey_response_answers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    shop_domain = Column(String(255), nullable=False, index=True)
    response_id = Column(Integer, ForeignKey("shopify_survey_responses.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("shopify_survey_questions.id", ondelete="SET NULL"), nullable=True, index=True)
    question_key = Column(String(64), nullable=True)
    answer_text = Column(Text, nullable=True)
    answer_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.current_timestamp(), nullable=False)
