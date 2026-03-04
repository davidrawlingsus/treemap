from sqlalchemy import Column, String, DateTime, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class Plan(Base):
    __tablename__ = "plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(50), nullable=False, unique=True)  # basic, pro, enterprise
    display_name = Column(String(100), nullable=False)
    stripe_price_id_monthly = Column(String(255), nullable=True)
    stripe_price_id_annual = Column(String(255), nullable=True)
    price_monthly_cents = Column(Integer, nullable=False, default=0)
    price_annual_cents = Column(Integer, nullable=False, default=0)
    features = Column(JSONB, nullable=False, default={})
    trial_limit = Column(Integer, nullable=False, default=0)
    sort_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    subscriptions = relationship("Subscription", back_populates="plan")

    def __repr__(self):
        return f"<Plan(id={self.id}, name={self.name})>"
