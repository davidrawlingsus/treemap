"""
Founder admin routes for lead email series management.

View, pause, resume, edit, and cancel scheduled email series
generated from VoC analysis for lead clients.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_active_founder
from app.database import get_db
from app.models import User
from app.models.lead_email import LeadEmail
from app.models.leadgen_voc import LeadgenVocRun
from app.models.client import Client
from app.models.leadgen_pipeline_output import LeadgenPipelineOutput

router = APIRouter()


# ---------------------------------------------------------------------------
# List all email series
# ---------------------------------------------------------------------------

@router.get("/api/founder-admin/lead-emails")
def list_lead_email_series(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """List all lead email series grouped by run/client."""
    from sqlalchemy import func

    series = (
        db.query(
            LeadEmail.run_id,
            LeadEmail.client_id,
            LeadEmail.email_address,
            func.count(LeadEmail.id).label("total_emails"),
            func.count(LeadEmail.id).filter(LeadEmail.status == "sent").label("sent_count"),
            func.count(LeadEmail.id).filter(LeadEmail.status == "queued").label("queued_count"),
            func.count(LeadEmail.id).filter(LeadEmail.status == "paused").label("paused_count"),
            func.min(LeadEmail.created_at).label("created_at"),
        )
        .group_by(LeadEmail.run_id, LeadEmail.client_id, LeadEmail.email_address)
        .order_by(func.min(LeadEmail.created_at).desc())
        .all()
    )

    results = []
    for row in series:
        client = db.query(Client).filter(Client.id == row.client_id).first()
        results.append({
            "run_id": row.run_id,
            "client_id": str(row.client_id),
            "client_name": client.name if client else "Unknown",
            "email_address": row.email_address,
            "total_emails": row.total_emails,
            "sent_count": row.sent_count,
            "queued_count": row.queued_count,
            "paused_count": row.paused_count,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        })

    return results


# ---------------------------------------------------------------------------
# Get email series for a specific run
# ---------------------------------------------------------------------------

@router.get("/api/founder-admin/lead-emails/{run_id}")
def get_lead_email_series(
    run_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Get all emails in a series with their content and status."""
    emails = (
        db.query(LeadEmail)
        .filter(LeadEmail.run_id == run_id)
        .order_by(LeadEmail.sequence_number.asc())
        .all()
    )
    if not emails:
        raise HTTPException(status_code=404, detail="No emails found for this run")

    # Get the run and client info
    run = db.query(LeadgenVocRun).filter(LeadgenVocRun.run_id == run_id).first()
    client = db.query(Client).filter(Client.id == emails[0].client_id).first() if emails else None

    # Get pipeline outputs (markdown + JSON + gamma)
    outputs = db.query(LeadgenPipelineOutput).filter(
        LeadgenPipelineOutput.run_id == run_id
    ).order_by(LeadgenPipelineOutput.step_order).all()

    deck_markdown = None
    voc_markdown = None
    gamma_url = None
    for out in outputs:
        if out.step_type == "voc_analysis_markdown":
            voc_markdown = (out.output or {}).get("markdown")
        elif out.step_type == "voc_analysis_json":
            deck_markdown = (out.output or {}).get("deck_markdown")
        # gamma_url would be stored in run payload
    pdf_url = None
    if run and run.payload:
        gamma_url = run.payload.get("gamma_url")
        pdf_url = run.payload.get("pdf_url")

    return {
        "run_id": run_id,
        "client_name": client.name if client else "Unknown",
        "client_id": str(client.id) if client else None,
        "email_address": run.work_email if run else emails[0].email_address,
        "company_name": run.company_name if run else None,
        "voc_markdown": voc_markdown,
        "deck_markdown": deck_markdown,
        "gamma_url": gamma_url,
        "pdf_url": pdf_url,
        "emails": [
            {
                "id": str(e.id),
                "sequence_number": e.sequence_number,
                "subject": e.subject,
                "preview_text": e.preview_text,
                "template_data": e.template_data,
                "scheduled_for": e.scheduled_for.isoformat() if e.scheduled_for else None,
                "status": e.status,
                "sent_at": e.sent_at.isoformat() if e.sent_at else None,
                "opened_at": e.opened_at.isoformat() if e.opened_at else None,
                "clicked_at": e.clicked_at.isoformat() if e.clicked_at else None,
                "error_message": e.error_message,
                "extra_data": e.extra_data,
            }
            for e in emails
        ],
    }


# ---------------------------------------------------------------------------
# Pause / Resume / Cancel
# ---------------------------------------------------------------------------

@router.post("/api/founder-admin/lead-emails/{run_id}/pause")
def pause_series(
    run_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Pause all queued emails for a run."""
    from app.services.lead_email_service import pause_email_series
    count = pause_email_series(db, run_id)
    return {"paused": count}


@router.post("/api/founder-admin/lead-emails/{run_id}/resume")
def resume_series(
    run_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Resume paused emails, recalculating schedule from today."""
    from app.services.lead_email_service import resume_email_series
    count = resume_email_series(db, run_id)
    return {"resumed": count}


@router.post("/api/founder-admin/lead-emails/{email_id}/cancel")
def cancel_single_email(
    email_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Cancel a single unsent email."""
    from app.services.lead_email_service import cancel_email
    email = cancel_email(db, email_id)
    if not email:
        raise HTTPException(status_code=404, detail="Email not found or already sent")
    return {"cancelled": True, "id": str(email.id)}


# ---------------------------------------------------------------------------
# Edit unsent email
# ---------------------------------------------------------------------------

class EmailUpdateRequest(BaseModel):
    subject: Optional[str] = None
    template_data: Optional[dict] = None


@router.patch("/api/founder-admin/lead-emails/{email_id}")
def update_email(
    email_id: UUID,
    body: EmailUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Update content of an unsent email."""
    from app.services.lead_email_service import update_email_content
    email = update_email_content(
        db, email_id,
        subject=body.subject,
        template_data=body.template_data,
    )
    if not email:
        raise HTTPException(status_code=404, detail="Email not found or already sent")
    return {"updated": True, "id": str(email.id)}


# ---------------------------------------------------------------------------
# Test send — send all emails to founder immediately
# ---------------------------------------------------------------------------

class TestSendRequest(BaseModel):
    test_email: str


@router.post("/api/founder-admin/lead-emails/{run_id}/test-send")
def test_send_series(
    run_id: str,
    body: TestSendRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Send all emails in a series to a test address immediately."""
    from app.services.lead_email_service import test_send_all
    from app.config import get_settings
    settings = get_settings()
    sent = test_send_all(settings, db, run_id, body.test_email)
    return {"sent": sent, "test_email": body.test_email}
