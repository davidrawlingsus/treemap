"""
Authorized domain management routes for founder admin.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from uuid import UUID
from typing import List

from app.database import get_db
from app.models import User, Client, AuthorizedDomain, AuthorizedDomainClient
from app.schemas import AuthorizedDomainResponse, AuthorizedDomainCreate, AuthorizedDomainUpdate
from app.auth import get_current_active_founder_with_password
from app.utils import serialize_authorized_domain

router = APIRouter()


@router.get(
    "/api/founder/authorized-domains",
    response_model=List[AuthorizedDomainResponse],
)
def list_authorized_domains_for_founder(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder_with_password),
):
    """List authorized domains with associated clients for founder tooling."""
    domains = (
        db.query(AuthorizedDomain)
        .options(
            joinedload(AuthorizedDomain.client_links).joinedload(
                AuthorizedDomainClient.client
            )
        )
        .order_by(func.lower(AuthorizedDomain.domain))
        .all()
    )

    return [serialize_authorized_domain(domain) for domain in domains]


@router.post(
    "/api/founder/authorized-domains",
    response_model=AuthorizedDomainResponse,
    status_code=201,
)
def create_authorized_domain_for_founder(
    payload: AuthorizedDomainCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder_with_password),
):
    """Create a new authorized domain and associate it with clients."""
    normalized_domain = payload.domain.strip().lower()
    if not normalized_domain:
        raise HTTPException(status_code=400, detail="Domain is required.")

    existing = (
        db.query(AuthorizedDomain)
        .filter(func.lower(AuthorizedDomain.domain) == normalized_domain)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=400, detail="An authorized domain with this name already exists."
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

    authorized_domain = AuthorizedDomain(
        domain=normalized_domain,
        description=payload.description.strip() if payload.description else None,
    )
    authorized_domain.clients = clients

    try:
        db.add(authorized_domain)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400, detail="An authorized domain with this name already exists."
        )
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))

    created_domain = (
        db.query(AuthorizedDomain)
        .options(
            joinedload(AuthorizedDomain.client_links).joinedload(
                AuthorizedDomainClient.client
            )
        )
        .filter(AuthorizedDomain.id == authorized_domain.id)
        .one()
    )

    return serialize_authorized_domain(created_domain)


@router.put(
    "/api/founder/authorized-domains/{domain_id}",
    response_model=AuthorizedDomainResponse,
)
def update_authorized_domain_for_founder(
    domain_id: UUID,
    payload: AuthorizedDomainUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder_with_password),
):
    """Update an existing authorized domain and its client associations."""
    authorized_domain = (
        db.query(AuthorizedDomain)
        .options(joinedload(AuthorizedDomain.client_links))
        .filter(AuthorizedDomain.id == domain_id)
        .first()
    )

    if not authorized_domain:
        raise HTTPException(status_code=404, detail="Authorized domain not found.")

    normalized_domain = payload.domain.strip().lower()
    if not normalized_domain:
        raise HTTPException(status_code=400, detail="Domain is required.")

    if normalized_domain != authorized_domain.domain:
        duplicate = (
            db.query(AuthorizedDomain)
            .filter(func.lower(AuthorizedDomain.domain) == normalized_domain)
            .filter(AuthorizedDomain.id != domain_id)
            .first()
        )
        if duplicate:
            raise HTTPException(
                status_code=400,
                detail="Another authorized domain with this name already exists.",
            )
        authorized_domain.domain = normalized_domain

    authorized_domain.description = (
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
        authorized_domain.clients = clients

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400, detail="An authorized domain with this name already exists."
        )
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))

    updated_domain = (
        db.query(AuthorizedDomain)
        .options(
            joinedload(AuthorizedDomain.client_links).joinedload(
                AuthorizedDomainClient.client
            )
        )
        .filter(AuthorizedDomain.id == domain_id)
        .one()
    )

    return serialize_authorized_domain(updated_domain)

