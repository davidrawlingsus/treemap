"""
Authentication utilities for JWT tokens, password hashing, and magic-link support.
"""
from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from typing import Optional, Tuple

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

# Bearer token scheme for token extraction
security = HTTPBearer()


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


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """Get the current authenticated user from a Bearer token."""
    settings = get_settings()
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token = credentials.credentials
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


def validate_founder_password(
    password: str | None, 
    expected_password: str, 
    is_production: bool,
    status_code: int = status.HTTP_403_FORBIDDEN
) -> None:
    """
    Validate founder password.
    
    In production, password must match. In development, validation is skipped for convenience.
    
    Args:
        password: The password to validate
        expected_password: The expected password from config
        is_production: Whether running in production environment
        status_code: HTTP status code to use for password mismatch (default: 403)
        
    Raises:
        HTTPException: If password is incorrect in production
    """
    if is_production and password != expected_password:
        raise HTTPException(
            status_code=status_code,
            detail="Incorrect founder admin password",
        )


def get_current_active_founder_with_password(
    current_user: User = Depends(get_current_user),
    password_header: str | None = Header(None, alias="X-Founder-Admin-Password"),
) -> User:
    """
    Get the current user if they are a founder AND provide the correct admin password.
    
    This adds an additional layer of security for founder admin routes by requiring
    both a valid JWT token (proving founder status) and a password header.
    
    NOTE: Password check is skipped in development mode for convenience.
    In production, the password is always required.
    
    Args:
        current_user: The authenticated user from JWT token
        password_header: Password provided in X-Founder-Admin-Password header
        
    Returns:
        User object if both checks pass
        
    Raises:
        HTTPException: 403 if not a founder or password is incorrect
    """
    # First check if user is a founder
    if not current_user.is_founder:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions - founder access required",
        )
    
    # Validate password (skipped in development mode for convenience)
    settings = get_settings()
    validate_founder_password(
        password=password_header,
        expected_password=settings.founder_admin_password,
        is_production=settings.is_production()
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


def clear_magic_link_state(user: User) -> None:
    """Remove any stored magic-link data for a user."""
    user.magic_link_token = None
    user.magic_link_expires_at = None
    user.last_magic_link_sent_at = None

