"""
Saved Emails management routes.
Access: any authenticated user with access to the client (membership or founder).
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional, List
import logging
import copy

from app.database import get_db
from app.models import User, SavedEmail, Client
from app.schemas import (
    SavedEmailCreate, 
    SavedEmailUpdate, 
    SavedEmailResponse, 
    SavedEmailListResponse,
    BatchReorderRequest,
    BatchReorderResponse,
)
from app.auth import get_current_user
from app.authorization import verify_client_access

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/api/clients/{client_id}/saved-emails",
    response_model=SavedEmailListResponse,
)
def list_saved_emails(
    client_id: UUID,
    email_type: Optional[str] = Query(None, description="Filter by email type"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all saved emails for a client, optionally filtered by email_type."""
    verify_client_access(client_id, current_user, db)
    query = db.query(SavedEmail).filter(SavedEmail.client_id == client_id)
    
    # Apply email_type filter if provided
    if email_type:
        query = query.filter(SavedEmail.email_type == email_type)
    
    emails = query.order_by(SavedEmail.created_at.desc()).all()
    
    return SavedEmailListResponse(
        items=[SavedEmailResponse.model_validate(email) for email in emails],
        total=len(emails)
    )


@router.post(
    "/api/clients/{client_id}/saved-emails",
    response_model=SavedEmailResponse,
    status_code=201,
)
def create_saved_email(
    client_id: UUID,
    email_data: SavedEmailCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new saved email."""
    verify_client_access(client_id, current_user, db)
    # Create the email
    email = SavedEmail(
        client_id=client_id,
        email_type=email_data.email_type,
        subject_line=email_data.subject_line,
        preview_text=email_data.preview_text,
        from_name=email_data.from_name,
        headline=email_data.headline,
        body_text=email_data.body_text,
        discount_code=email_data.discount_code,
        social_proof=email_data.social_proof,
        cta_text=email_data.cta_text,
        cta_url=email_data.cta_url,
        sequence_position=email_data.sequence_position,
        send_delay_hours=email_data.send_delay_hours,
        voc_evidence=email_data.voc_evidence or [],
        strategic_intent=email_data.strategic_intent,
        full_json=email_data.full_json,
        action_id=email_data.action_id,
        status=email_data.status or 'draft',
        created_by=current_user.id,
    )
    
    db.add(email)
    db.commit()
    db.refresh(email)
    
    logger.info(f"Created saved email {email.id} for client {client_id}")
    return SavedEmailResponse.model_validate(email)


@router.get(
    "/api/saved-emails/{email_id}",
    response_model=SavedEmailResponse,
)
def get_saved_email(
    email_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single saved email by ID."""
    email = db.query(SavedEmail).filter(SavedEmail.id == email_id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Saved email not found")
    verify_client_access(email.client_id, current_user, db)
    return SavedEmailResponse.model_validate(email)


@router.patch(
    "/api/saved-emails/{email_id}",
    response_model=SavedEmailResponse,
)
def update_saved_email(
    email_id: UUID,
    email_data: SavedEmailUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a saved email (e.g., change status, edit content, or set image_url)."""
    email = db.query(SavedEmail).filter(SavedEmail.id == email_id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Saved email not found")
    verify_client_access(email.client_id, current_user, db)
    # Update only provided fields
    update_data = email_data.model_dump(exclude_unset=True)
    
    # Handle fields stored in full_json (same pattern as FacebookAd)
    full_json_fields = ['image_url', 'sequence_badge_text']
    full_json_updates = {}
    
    for field in full_json_fields:
        value = update_data.pop(field, None)
        if value is not None:
            full_json_updates[field] = value
    
    # Update full_json if any fields need to be stored there
    if full_json_updates:
        full_json = copy.deepcopy(email.full_json) if email.full_json else {}
        for field, value in full_json_updates.items():
            if value:
                full_json[field] = value
            else:
                # Remove field if set to null/empty
                full_json.pop(field, None)
        email.full_json = full_json
    
    # Update other fields
    for field, value in update_data.items():
        setattr(email, field, value)
    
    db.commit()
    db.refresh(email)
    
    logger.info(f"Updated saved email {email_id}")
    return SavedEmailResponse.model_validate(email)


@router.delete(
    "/api/saved-emails/{email_id}",
    status_code=204,
)
def delete_saved_email(
    email_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a saved email."""
    email = db.query(SavedEmail).filter(SavedEmail.id == email_id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Saved email not found")
    verify_client_access(email.client_id, current_user, db)
    db.delete(email)
    db.commit()
    
    logger.info(f"Deleted saved email {email_id}")
    return None


@router.patch(
    "/api/clients/{client_id}/saved-emails/reorder",
    response_model=BatchReorderResponse,
)
def batch_reorder_emails(
    client_id: UUID,
    reorder_request: BatchReorderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Batch update email sequence positions and send delays.
    Used for drag-and-drop reordering in the UI.
    Updates all provided emails in a single transaction.
    """
    verify_client_access(client_id, current_user, db)
    updated_emails = []
    
    for update in reorder_request.updates:
        email = db.query(SavedEmail).filter(
            SavedEmail.id == update.id,
            SavedEmail.client_id == client_id
        ).first()
        
        if not email:
            logger.warning(f"Email {update.id} not found for client {client_id}, skipping")
            continue
        
        # Update sequence position
        email.sequence_position = update.sequence_position
        
        # Update send delay if provided
        if update.send_delay_hours is not None:
            email.send_delay_hours = update.send_delay_hours
        
        updated_emails.append(email)
    
    # Commit all updates in a single transaction
    db.commit()
    
    # Refresh all emails to get updated values
    for email in updated_emails:
        db.refresh(email)
    
    logger.info(f"Batch reordered {len(updated_emails)} emails for client {client_id}")
    
    return BatchReorderResponse(
        updated_count=len(updated_emails),
        emails=[SavedEmailResponse.model_validate(email) for email in updated_emails]
    )
