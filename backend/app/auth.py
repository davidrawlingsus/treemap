"""
Authentication utilities for JWT tokens, password hashing, and magic-link support.
"""
from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from typing import Optional, Tuple
from uuid import UUID

from fastapi import Depends, HTTPException, Header, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import User

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Bearer token schemes for token extraction
security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    settings = get_settings()
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta is not None:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


def _get_user_from_token(token: str, db: Session) -> User:
    """Resolve a user from a Bearer token."""
    settings = get_settings()
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    return user


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """Get the current authenticated user from a Bearer token."""
    return _get_user_from_token(credentials.credentials, db)


def get_optional_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_security),
    db: Session = Depends(get_db),
) -> User | None:
    """Get the current user when a valid Bearer token is present."""
    if credentials is None:
        return None
    return _get_user_from_token(credentials.credentials, db)


def get_current_active_founder(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get the current user if they are a founder."""
    if not current_user.is_founder:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions - founder access required",
        )
    return current_user


def generate_magic_link_token(
    expires_minutes: Optional[int] = None,
) -> Tuple[str, str, datetime]:
    """
    Generate a magic-link token along with its hashed value and expiry timestamp.

    Returns:
        tuple(token, token_hash, expires_at)
    """
    settings = get_settings()
    expiry_minutes = (
        expires_minutes if expires_minutes is not None else settings.magic_link_token_expire_minutes
    )
    token = secrets.token_urlsafe(32)
    token_hash = hash_token(token)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes)
    return token, token_hash, expires_at


def hash_token(raw_token: str) -> str:
    """Hash a token using SHA-256."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def is_magic_link_token_valid(user: User, raw_token: str) -> tuple[bool, str]:
    """
    Validate a raw magic-link token against the stored hash and expiry.
    
    Returns:
        tuple[bool, str]: (is_valid, error_reason)
    """
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"Validating magic link token for user: {user.email}")
    
    if not raw_token:
        logger.warning("No token provided in validation request")
        return False, "no_token_provided"
    
    if not user.magic_link_token:
        logger.warning(f"No stored token found for user {user.email}")
        return False, "no_stored_token"
    
    now = datetime.now(timezone.utc)
    if not user.magic_link_expires_at:
        logger.warning(f"No expiration time set for user {user.email}")
        return False, "no_expiration_time"
    
    if user.magic_link_expires_at < now:
        logger.warning(f"Token expired - expires_at: {user.magic_link_expires_at}, now: {now}")
        time_since_expiry = now - user.magic_link_expires_at
        logger.info(f"Token expired {time_since_expiry.total_seconds()} seconds ago")
        return False, "token_expired"
    
    raw_token_hash = hash_token(raw_token)
    stored_token_hash = user.magic_link_token
    is_valid = raw_token_hash == stored_token_hash
    
    logger.info(f"Token hash comparison - valid: {is_valid}")
    if not is_valid:
        logger.warning(f"Hash mismatch - computed: {raw_token_hash[:10]}..., stored: {stored_token_hash[:10]}...")
        return False, "token_mismatch"
    
    logger.info(f"Token validation successful for {user.email}")
    return True, "valid"


def get_current_user_flexible(
    x_api_key: Optional[str] = Header(default=None),
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_security),
    db: Session = Depends(get_db),
) -> User:
    """Authenticate via X-API-Key header or Bearer JWT. Returns a User either way.

    When authenticated via API key, the user object gets an `_api_key_client_id`
    attribute set to the key's scoped client_id for downstream access enforcement.
    """
    if x_api_key:
        from app.services.api_key_service import validate_api_key
        api_key = validate_api_key(db, x_api_key)
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired API key",
            )
        if not api_key.user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive",
            )
        # Tag user with the API key's client scope for downstream enforcement
        api_key.user._api_key_client_id = api_key.client_id
        return api_key.user

    if credentials:
        return _get_user_from_token(credentials.credentials, db)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required: provide X-API-Key header or Bearer token",
    )


def resolve_site_key(
    x_site_key: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> UUID:
    """Resolve a public site key to a client_id. No user/admin access granted.

    Site keys are non-secret public identifiers safe to embed in client-side JS.
    They only grant access to read published surveys and submit responses.
    """
    if not x_site_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-Site-Key header required",
        )
    from app.models.client import Client
    client = db.query(Client).filter(
        Client.site_key == x_site_key,
        Client.is_active.is_(True),
    ).first()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid site key",
        )
    return client.id


def clear_magic_link_state(user: User) -> None:
    """Remove any stored magic-link data for a user."""
    user.magic_link_token = None
    user.magic_link_expires_at = None
    user.last_magic_link_sent_at = None

