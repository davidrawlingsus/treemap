"""
Extension webhook endpoints — analytics tracking and lead ingestion.

- POST /api/extension/track — fire-and-forget analytics events (no auth)
- POST /api/extension/lead-webhook — receives leads from Zapier (no auth)
"""
import logging
from typing import Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import get_optional_current_user
from app.database import get_db
from app.models import User, Client, AuthorizedDomain
from app.models.extension_event import ExtensionEvent

router = APIRouter(prefix="/api/extension", tags=["extension-webhook"])
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Analytics tracking
# ---------------------------------------------------------------------------

ALLOWED_EVENTS = {
    "extension_opened",
    "analysis_started",
    "client_matched",
    "gate_shown",
    "email_submitted",
    "magic_link_clicked",
    "gate_lifted",
    "analysis_completed",
    "auto_import_fired",
    "opportunity_shown",
    "calendly_clicked",
}


class TrackEventRequest(BaseModel):
    event: str = Field(..., max_length=50)
    session_id: str = Field(..., max_length=64)
    advertiser_domain: Optional[str] = Field(None, max_length=255)
    metadata: Optional[dict] = None


@router.post("/track", status_code=200)
def track_event(
    body: TrackEventRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """Record an analytics event from the extension. No auth required."""
    if body.event not in ALLOWED_EVENTS:
        raise HTTPException(status_code=400, detail=f"Unknown event: {body.event}")

    event = ExtensionEvent(
        event=body.event,
        session_id=body.session_id,
        user_id=current_user.id if current_user else None,
        advertiser_domain=body.advertiser_domain,
        metadata_json=body.metadata,
    )
    db.add(event)
    db.commit()
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Lead webhook (receives leads from Zapier)
# ---------------------------------------------------------------------------

class LeadWebhookRequest(BaseModel):
    email: str = Field(..., min_length=3, pattern=r".+@.+\..+")
    website_url: str = Field(..., min_length=1)
    name: Optional[str] = None


def _extract_domain(url: str) -> str:
    """Extract clean domain from a URL."""
    try:
        parsed = urlparse(url if "://" in url else f"https://{url}")
        host = (parsed.netloc or "").lower().split(":")[0]
        if host.startswith("www."):
            host = host[4:]
        return host
    except Exception:
        return ""


@router.post("/lead-webhook", status_code=200)
def receive_lead(
    body: LeadWebhookRequest,
    db: Session = Depends(get_db),
):
    """Receive a lead from Zapier (Facebook Lead Ads → Zapier → here)."""
    domain = _extract_domain(body.website_url)
    if not domain:
        raise HTTPException(status_code=400, detail="Could not extract domain from website_url")

    company_name = body.name or domain
    company_url = f"https://{domain}"

    # Check if client already exists for this domain
    from app.models.authorized_domain import AuthorizedDomainClient
    existing = (
        db.query(Client)
        .join(AuthorizedDomainClient, AuthorizedDomainClient.client_id == Client.id)
        .join(AuthorizedDomain, AuthorizedDomain.id == AuthorizedDomainClient.domain_id)
        .filter(AuthorizedDomain.domain == domain)
        .first()
    )

    if existing:
        logger.info("Lead webhook: client already exists for %s (id=%s)", domain, existing.id)
        return {"status": "ok", "client_id": str(existing.id), "created": False}

    # Create new lead client
    from app.services.leadgen_voc_service import (
        _sanitize_slug,
        _unique_name,
        _unique_slug,
        _get_default_founder_id,
        _ensure_authorized_domain,
    )

    founder_id = _get_default_founder_id(db)
    client = Client(
        name=_unique_name(db, company_name),
        slug=_unique_slug(db, _sanitize_slug(domain)),
        client_url=company_url,
        is_lead=True,
        is_active=True,
        founder_user_id=founder_id,
    )
    db.add(client)
    db.flush()

    _ensure_authorized_domain(db, domain, client)

    # Create user record for the email if needed (for magic link auth later)
    from app.models import Membership
    user = db.query(User).filter(User.email == body.email).first()
    if not user:
        user = User(email=body.email, is_active=True)
        db.add(user)
        db.flush()

    # Ensure membership linking user to client
    existing_membership = (
        db.query(Membership)
        .filter(Membership.user_id == user.id, Membership.client_id == client.id)
        .first()
    )
    if not existing_membership:
        membership = Membership(user_id=user.id, client_id=client.id, role="member")
        db.add(membership)

    db.commit()

    logger.info(
        "Lead webhook: created client %s (id=%s) for %s, user=%s",
        client.name, client.id, domain, body.email,
    )

    return {"status": "ok", "client_id": str(client.id), "created": True}
