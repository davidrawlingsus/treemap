"""
Authentication utilities for JWT tokens, password hashing, and magic-link support.
"""
from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from typing import Optional, Tuple

from fastapi import Depends, HTTPException, status
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


def is_magic_link_token_valid(user: User, raw_token: str) -> bool:
    """Validate a raw magic-link token against the stored hash and expiry."""
    if not user.magic_link_token or not raw_token:
        return False
    now = datetime.now(timezone.utc)
    if not user.magic_link_expires_at or user.magic_link_expires_at < now:
        return False
    return hash_token(raw_token) == user.magic_link_token


def clear_magic_link_state(user: User) -> None:
    """Remove any stored magic-link data for a user."""
    user.magic_link_token = None
    user.magic_link_expires_at = None
    user.last_magic_link_sent_at = None

