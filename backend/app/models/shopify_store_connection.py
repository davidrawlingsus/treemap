from sqlalchemy import Column, String, DateTime, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class ShopifyStoreConnection(Base):
    __tablename__ = "shopify_store_connections"

    id = Column(Integer, primary_key=True, autoincrement=True)
    shop_domain = Column(String(255), nullable=False, unique=True, index=True)
    client_uuid = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=True, index=True)
    status = Column(String(50), nullable=False, default="active")
    installed_at = Column(DateTime(timezone=True), nullable=True)
    uninstalled_at = Column(DateTime(timezone=True), nullable=True)
    offline_access_token = Column(String(512), nullable=True)
    offline_access_scopes = Column(String(512), nullable=True)
    token_updated_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.current_timestamp(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

    client = relationship("Client", foreign_keys=[client_uuid])

    def __repr__(self):
        return (
            f"<ShopifyStoreConnection(id={self.id}, shop_domain={self.shop_domain}, "
            f"client_uuid={self.client_uuid}, status={self.status})>"
        )
