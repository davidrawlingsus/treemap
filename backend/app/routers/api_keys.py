"""API key management endpoints."""
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user
from app.authorization import verify_client_access
from app.models import User
from app.models.api_key import ApiKey
from app.schemas.api_key import ApiKeyCreateRequest, ApiKeyCreateResponse, ApiKeyListItem
from app.services.api_key_service import create_api_key, revoke_api_key

router = APIRouter(prefix="/api/api-keys", tags=["API Keys"])


@router.post("/", response_model=ApiKeyCreateResponse, summary="Create API key")
def create_key(
    request: ApiKeyCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new API key scoped to a specific client.

    The raw key (prefixed `vzd_`) is returned **once** in the response and cannot be retrieved again.
    Store it securely. Use it via the `X-API-Key` header on VOC endpoints.

    Requires JWT auth — API keys cannot create other API keys.
    """
    verify_client_access(request.client_id, current_user, db)
    api_key, raw_key = create_api_key(
        db=db,
        user_id=current_user.id,
        client_id=request.client_id,
        name=request.name,
        expires_at=request.expires_at,
    )
    return ApiKeyCreateResponse(
        id=api_key.id,
        key=raw_key,
        key_prefix=api_key.key_prefix,
        name=api_key.name,
        client_id=api_key.client_id,
        expires_at=api_key.expires_at,
    )


@router.get("/", response_model=List[ApiKeyListItem], summary="List API keys")
def list_keys(
    client_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List active API keys for a client. Returns key prefix (not the full key), name,
    and usage metadata. Requires JWT auth.
    """
    verify_client_access(client_id, current_user, db)
    keys = (
        db.query(ApiKey)
        .filter(ApiKey.client_id == client_id, ApiKey.is_active.is_(True))
        .order_by(ApiKey.created_at.desc())
        .all()
    )
    return keys


@router.delete("/{key_id}", summary="Revoke API key")
def delete_key(
    key_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Revoke an API key. The key is soft-deleted (marked inactive) and can no longer
    be used for authentication. Requires JWT auth.
    """
    try:
        key_uuid = UUID(key_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid key ID")

    success = revoke_api_key(db, key_uuid, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="API key not found")
    return {"detail": "API key revoked"}
