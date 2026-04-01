from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth import get_current_user, get_current_user_flexible, resolve_site_key
from app.database import get_db
from app.models import User
from app.schemas.widget_survey import (
    WidgetRuntimeSurveyEnvelope,
    WidgetSurveyDetailResponse,
    WidgetSurveyHeartbeatRequest,
    WidgetSurveyImpressionRequest,
    WidgetSurveyInstallationStatus,
    WidgetSurveyListItem,
    WidgetSurveyResponseIngestRequest,
    WidgetSurveyResponseIngestResponse,
    WidgetSurveyResponseList,
    WidgetSurveyStats,
    WidgetSurveyUpsertRequest,
)
from app.services import widget_survey_service as svc

router = APIRouter(prefix="/api/widget-surveys", tags=["widget-surveys"])


# ── Helpers ──────────────────────────────────────────────────────────


def _get_api_key_client_id(user: User) -> UUID:
    """Extract the client_id from an API-key-authenticated user."""
    client_id = getattr(user, "_api_key_client_id", None)
    if client_id is None:
        raise HTTPException(status_code=403, detail="API key authentication required for this endpoint")
    return client_id


def _resolve_client_id(user: User, client_id: UUID | None) -> UUID:
    """For admin endpoints: use explicit client_id or fall back to API key scope."""
    scoped = getattr(user, "_api_key_client_id", None)
    if scoped:
        if client_id and client_id != scoped:
            raise HTTPException(status_code=403, detail="API key is scoped to a different client")
        return scoped
    if client_id is None:
        raise HTTPException(status_code=400, detail="client_id query parameter is required")
    return client_id


# ── Public endpoints (site key auth — safe to embed in client-side JS) ──


@router.get("/active", response_model=WidgetRuntimeSurveyEnvelope)
def get_active_survey(
    client_id: UUID = Depends(resolve_site_key),
    db: Session = Depends(get_db),
):
    """Fetch the active survey config for the widget to render."""
    survey = svc.get_active_runtime_survey(db, client_id)
    return WidgetRuntimeSurveyEnvelope(survey=survey)


@router.post("/responses", response_model=WidgetSurveyResponseIngestResponse, status_code=201)
def submit_response(
    payload: WidgetSurveyResponseIngestRequest,
    client_id: UUID = Depends(resolve_site_key),
    db: Session = Depends(get_db),
):
    """Submit a survey response from the widget."""
    return svc.ingest_survey_response(db, client_id, payload)


@router.post("/heartbeat", status_code=204)
def record_heartbeat(
    payload: WidgetSurveyHeartbeatRequest,
    client_id: UUID = Depends(resolve_site_key),
    db: Session = Depends(get_db),
):
    """Record that the widget script is installed on a page."""
    svc.record_heartbeat(db, client_id, payload.page_url)


@router.post("/impression", status_code=204)
def record_impression(
    payload: WidgetSurveyImpressionRequest,
    client_id: UUID = Depends(resolve_site_key),
    db: Session = Depends(get_db),
):
    """Record a survey impression (popup was shown)."""
    svc.record_impression(db, payload.survey_version_id)


# ── Admin endpoints (JWT auth) ───────────────────────────────────────


@router.get("/site-key")
def get_site_key(
    client_id: UUID = Query(...),
    user: User = Depends(get_current_user_flexible),
    db: Session = Depends(get_db),
):
    """Get the public site key for a client (for embedding in widget snippet)."""
    resolved = _resolve_client_id(user, client_id)
    from app.models.client import Client
    client = db.query(Client).filter(Client.id == resolved).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    # Auto-generate site key if missing
    if not client.site_key:
        import secrets
        client.site_key = "site_" + secrets.token_urlsafe(16)
        db.commit()
        db.refresh(client)
    return {"site_key": client.site_key, "client_id": str(client.id), "client_name": client.name}


@router.get("/", response_model=list[WidgetSurveyListItem])
def list_surveys(
    client_id: UUID | None = Query(default=None),
    user: User = Depends(get_current_user_flexible),
    db: Session = Depends(get_db),
):
    """List all widget surveys for a client."""
    resolved = _resolve_client_id(user, client_id)
    return svc.list_surveys(db, resolved)


@router.post("/", response_model=WidgetSurveyDetailResponse, status_code=201)
def create_survey(
    payload: WidgetSurveyUpsertRequest,
    client_id: UUID | None = Query(default=None),
    user: User = Depends(get_current_user_flexible),
    db: Session = Depends(get_db),
):
    """Create a new widget survey with a draft version."""
    resolved = _resolve_client_id(user, client_id)
    try:
        return svc.upsert_survey_draft(db, resolved, payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/installation-status", response_model=WidgetSurveyInstallationStatus)
def get_installation_status(
    client_id: UUID | None = Query(default=None),
    user: User = Depends(get_current_user_flexible),
    db: Session = Depends(get_db),
):
    """Check if the widget script is installed (based on heartbeats)."""
    resolved = _resolve_client_id(user, client_id)
    return svc.get_installation_status(db, resolved)


@router.get("/{survey_id}", response_model=WidgetSurveyDetailResponse)
def get_survey_detail(
    survey_id: int,
    client_id: UUID | None = Query(default=None),
    user: User = Depends(get_current_user_flexible),
    db: Session = Depends(get_db),
):
    """Get full survey detail including draft and active versions."""
    resolved = _resolve_client_id(user, client_id)
    try:
        return svc.get_survey_detail(db, resolved, survey_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{survey_id}", response_model=WidgetSurveyDetailResponse)
def update_survey(
    survey_id: int,
    payload: WidgetSurveyUpsertRequest,
    client_id: UUID | None = Query(default=None),
    user: User = Depends(get_current_user_flexible),
    db: Session = Depends(get_db),
):
    """Update a survey's draft version."""
    resolved = _resolve_client_id(user, client_id)
    try:
        return svc.upsert_survey_draft(db, resolved, payload, survey_id=survey_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{survey_id}/publish", response_model=WidgetSurveyDetailResponse)
def publish_survey(
    survey_id: int,
    client_id: UUID | None = Query(default=None),
    user: User = Depends(get_current_user_flexible),
    db: Session = Depends(get_db),
):
    """Publish the draft version, making it the active survey."""
    resolved = _resolve_client_id(user, client_id)
    try:
        return svc.publish_survey(db, resolved, survey_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{survey_id}/unpublish", response_model=WidgetSurveyDetailResponse)
def unpublish_survey(
    survey_id: int,
    client_id: UUID | None = Query(default=None),
    user: User = Depends(get_current_user_flexible),
    db: Session = Depends(get_db),
):
    """Deactivate the currently active version."""
    resolved = _resolve_client_id(user, client_id)
    try:
        return svc.unpublish_survey(db, resolved, survey_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{survey_id}", status_code=204)
def delete_survey(
    survey_id: int,
    client_id: UUID | None = Query(default=None),
    user: User = Depends(get_current_user_flexible),
    db: Session = Depends(get_db),
):
    """Delete a survey and all associated data."""
    resolved = _resolve_client_id(user, client_id)
    try:
        svc.delete_survey(db, resolved, survey_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{survey_id}/responses", response_model=WidgetSurveyResponseList)
def list_responses(
    survey_id: int,
    client_id: UUID | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user_flexible),
    db: Session = Depends(get_db),
):
    """List survey responses with answers and Clarity session data."""
    resolved = _resolve_client_id(user, client_id)
    return svc.list_survey_responses(db, resolved, survey_id, limit, offset)


@router.get("/{survey_id}/stats", response_model=WidgetSurveyStats)
def get_stats(
    survey_id: int,
    client_id: UUID | None = Query(default=None),
    user: User = Depends(get_current_user_flexible),
    db: Session = Depends(get_db),
):
    """Get impression/response stats for a survey."""
    resolved = _resolve_client_id(user, client_id)
    try:
        return svc.get_survey_stats(db, resolved, survey_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
