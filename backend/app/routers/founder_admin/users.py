"""
User management routes for founder admin.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, func
from uuid import UUID
from typing import List, Optional

from app.database import get_db
from app.models import User, Membership, Client
from app.schemas import FounderUserSummary, FounderUserMembership, ClientResponse
from app.auth import get_current_active_founder

router = APIRouter()


def build_founder_user_summary(user: User) -> FounderUserSummary:
    """Build a founder-oriented view of a user record."""
    email_domain = user.email.split("@")[-1].lower() if "@" in user.email else ""
    membership_summaries: List[FounderUserMembership] = []
    for membership in user.memberships:
        if membership.client is None:
            continue
        membership_summaries.append(
            FounderUserMembership(
                client=ClientResponse.model_validate(membership.client),
                role=membership.role,
                status=membership.status,
                provisioned_at=membership.provisioned_at,
                provisioning_method=membership.provisioning_method,
                joined_at=membership.joined_at,
            )
        )

    return FounderUserSummary(
        id=user.id,
        email=user.email,
        name=user.name,
        is_founder=user.is_founder,
        is_active=user.is_active,
        last_login_at=user.last_login_at,
        email_verified_at=user.email_verified_at,
        last_magic_link_sent_at=user.last_magic_link_sent_at,
        created_at=user.created_at,
        updated_at=user.updated_at,
        email_domain=email_domain,
        memberships=membership_summaries,
    )


@router.get("/api/founder/users", response_model=List[FounderUserSummary])
def list_founder_users(
    search: Optional[str] = None,
    domain: Optional[str] = None,
    client_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """List users with membership metadata for founder tooling."""
    query = db.query(User)

    if client_id:
        query = query.join(Membership, Membership.user_id == User.id).filter(
            Membership.client_id == client_id
        )

    if search:
        normalized = f"%{search.lower()}%"
        query = query.filter(
            or_(
                func.lower(User.email).like(normalized),
                func.lower(User.name).like(normalized),
            )
        )

    if domain:
        normalized_domain = domain.lower()
        query = query.filter(
            func.lower(User.email).like(f"%@{normalized_domain}")
        )

    users = (
        query.options(
            joinedload(User.memberships).joinedload(Membership.client)
        )
        .order_by(func.lower(User.email))
        .all()
    )

    # Deduplicate in case joins introduced duplicates
    unique_users = {user.id: user for user in users}.values()

    return [build_founder_user_summary(user) for user in unique_users]

