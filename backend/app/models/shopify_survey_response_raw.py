from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class ShopifySurveyResponseRaw(Base):
    __tablename__ = "shopify_survey_responses_raw"
    __table_args__ = (
        UniqueConstraint(
            "shop_domain",
            "shopify_order_id",
            "survey_version",
            name="uq_shopify_survey_responses_shop_order_version",
        ),
        UniqueConstraint(
            "shop_domain",
            "idempotency_key",
            name="uq_shopify_survey_responses_shop_idempotency",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    shop_domain = Column(String(255), nullable=False, index=True)
    idempotency_key = Column(String(128), nullable=False)
    shopify_order_id = Column(String(255), nullable=True, index=True)
    order_gid = Column(String(255), nullable=True)
    customer_reference = Column(String(255), nullable=True)
    survey_version = Column(String(50), nullable=False, default="v1")
    answers_json = Column(JSONB, nullable=False)
    extension_context_json = Column(JSONB, nullable=True)
    client_uuid = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=True, index=True)
    submitted_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.current_timestamp(), nullable=False)

    client = relationship("Client", foreign_keys=[client_uuid])

    def __repr__(self):
        return (
            f"<ShopifySurveyResponseRaw(id={self.id}, shop_domain={self.shop_domain}, "
            f"shopify_order_id={self.shopify_order_id}, survey_version={self.survey_version})>"
        )
