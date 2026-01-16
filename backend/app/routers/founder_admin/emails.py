"""
Authorized email management routes for founder admin.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from uuid import UUID
from typing import List

from app.database import get_db
from app.models import User, Client, AuthorizedEmail, AuthorizedEmailClient
from app.schemas import AuthorizedEmailResponse, AuthorizedEmailCreate, AuthorizedEmailUpdate
from app.auth import get_current_active_founder
from app.utils import serialize_authorized_email

router = APIRouter()


@router.get(
    "/api/founder/authorized-emails",
    response_model=List[AuthorizedEmailResponse],
)
def list_authorized_emails_for_founder(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """List authorized emails with associated clients for founder tooling."""
    emails = (
        db.query(AuthorizedEmail)
        .options(
            joinedload(AuthorizedEmail.client_links).joinedload(
                AuthorizedEmailClient.client
            )
        )
        .order_by(func.lower(AuthorizedEmail.email))
        .all()
    )

    return [serialize_authorized_email(email) for email in emails]


@router.post(
    "/api/founder/authorized-emails",
    response_model=AuthorizedEmailResponse,
    status_code=201,
)
def create_authorized_email_for_founder(
    payload: AuthorizedEmailCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Create a new authorized email and associate it with clients."""
    normalized_email = payload.email.strip().lower()
    if not normalized_email or "@" not in normalized_email:
        raise HTTPException(status_code=400, detail="A valid email address is required.")

    existing = (
        db.query(AuthorizedEmail)
        .filter(func.lower(AuthorizedEmail.email) == normalized_email)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=400, detail="An authorized email with this address already exists."
        )

    client_ids = set(payload.client_ids or [])
    clients: List[Client] = []
    if client_ids:
        clients = db.query(Client).filter(Client.id.in_(client_ids)).all()
        found_ids = {client.id for client in clients}
        missing = client_ids - found_ids
        if missing:
            raise HTTPException(
                status_code=404,
                detail="One or more selected clients were not found.",
            )

    authorized_email = AuthorizedEmail(
        email=normalized_email,
        description=payload.description.strip() if payload.description else None,
    )
    authorized_email.clients = clients

    try:
        db.add(authorized_email)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400, detail="An authorized email with this address already exists."
        )
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))

    created_email = (
        db.query(AuthorizedEmail)
        .options(
            joinedload(AuthorizedEmail.client_links).joinedload(
                AuthorizedEmailClient.client
            )
        )
        .filter(AuthorizedEmail.id == authorized_email.id)
        .one()
    )

    return serialize_authorized_email(created_email)


@router.put(
    "/api/founder/authorized-emails/{email_id}",
    response_model=AuthorizedEmailResponse,
)
def update_authorized_email_for_founder(
    email_id: UUID,
    payload: AuthorizedEmailUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Update an existing authorized email and its client associations."""
    authorized_email = (
        db.query(AuthorizedEmail)
        .options(joinedload(AuthorizedEmail.client_links))
        .filter(AuthorizedEmail.id == email_id)
        .first()
    )

    if not authorized_email:
        raise HTTPException(status_code=404, detail="Authorized email not found.")

    normalized_email = payload.email.strip().lower()
    if not normalized_email or "@" not in normalized_email:
        raise HTTPException(status_code=400, detail="A valid email address is required.")

    if normalized_email != authorized_email.email:
        duplicate = (
            db.query(AuthorizedEmail)
            .filter(func.lower(AuthorizedEmail.email) == normalized_email)
            .filter(AuthorizedEmail.id != email_id)
            .first()
        )
        if duplicate:
            raise HTTPException(
                status_code=400,
                detail="Another authorized email with this address already exists.",
            )
        authorized_email.email = normalized_email

    authorized_email.description = (
        payload.description.strip() if payload.description else None
    )

    if payload.client_ids is not None:
        client_ids = set(payload.client_ids)
        clients: List[Client] = []
        if client_ids:
            clients = db.query(Client).filter(Client.id.in_(client_ids)).all()
            found_ids = {client.id for client in clients}
            missing = client_ids - found_ids
            if missing:
                raise HTTPException(
                    status_code=404,
                    detail="One or more selected clients were not found.",
                )
        authorized_email.clients = clients

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400, detail="An authorized email with this address already exists."
        )
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))

    updated_email = (
        db.query(AuthorizedEmail)
        .options(
            joinedload(AuthorizedEmail.client_links).joinedload(
                AuthorizedEmailClient.client
            )
        )
        .filter(AuthorizedEmail.id == email_id)
        .one()
    )

    return serialize_authorized_email(updated_email)

