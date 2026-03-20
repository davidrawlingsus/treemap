import hashlib
import secrets
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from app.models.api_key import ApiKey


def generate_api_key() -> tuple[str, str]:
    """Generate a raw API key and its SHA-256 hash."""
    raw = "vzd_" + secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return raw, key_hash


def create_api_key(
    db: Session,
    user_id: UUID,
    client_id: UUID,
    name: str,
    expires_at: datetime | None = None,
) -> tuple[ApiKey, str]:
    """Create an API key scoped to a client. Returns (ApiKey, raw_key). Raw key is shown once."""
    raw_key, key_hash = generate_api_key()
    api_key = ApiKey(
        user_id=user_id,
        client_id=client_id,
        key_hash=key_hash,
        key_prefix=raw_key[:12],
        name=name,
        expires_at=expires_at,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    return api_key, raw_key


def validate_api_key(db: Session, raw_key: str) -> ApiKey | None:
    """Validate a raw API key. Returns the ApiKey with user loaded, or None."""
    key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
    api_key = (
        db.query(ApiKey)
        .options(joinedload(ApiKey.user))
        .filter(
            ApiKey.key_hash == key_hash,
            ApiKey.is_active.is_(True),
            ApiKey.revoked_at.is_(None),
        )
        .first()
    )
    if not api_key:
        return None
    if api_key.expires_at and api_key.expires_at < datetime.now(timezone.utc):
        return None
    # Update last_used_at
    api_key.last_used_at = datetime.now(timezone.utc)
    db.commit()
    return api_key


def revoke_api_key(db: Session, key_id: UUID, user_id: UUID) -> bool:
    """Revoke an API key. Only the owning user can revoke."""
    api_key = db.query(ApiKey).filter(ApiKey.id == key_id, ApiKey.user_id == user_id).first()
    if not api_key:
        return False
    api_key.is_active = False
    api_key.revoked_at = datetime.now(timezone.utc)
    db.commit()
    return True
