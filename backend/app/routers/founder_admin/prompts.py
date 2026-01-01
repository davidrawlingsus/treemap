"""
Prompt management routes for founder admin.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from uuid import UUID
from typing import List, Optional

from app.database import get_db
from app.models import User, Prompt
from app.schemas import PromptResponse, PromptCreate, PromptUpdate
from app.auth import get_current_active_founder

router = APIRouter()


@router.get(
    "/api/founder/prompts",
    response_model=List[PromptResponse],
)
def list_prompts_for_founder(
    status: Optional[str] = None,
    prompt_purpose: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """List all prompts with optional filtering by status and purpose."""
    query = db.query(Prompt)
    
    if status:
        query = query.filter(Prompt.status == status)
    if prompt_purpose:
        query = query.filter(Prompt.prompt_purpose == prompt_purpose)
    
    prompts = query.order_by(Prompt.name, Prompt.version.desc()).all()
    return prompts


@router.get(
    "/api/founder/prompts/{prompt_id}",
    response_model=PromptResponse,
)
def get_prompt_for_founder(
    prompt_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Get a single prompt by ID."""
    prompt = db.query(Prompt).filter(Prompt.id == prompt_id).first()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found.")
    return prompt


@router.post(
    "/api/founder/prompts",
    response_model=PromptResponse,
    status_code=201,
)
def create_prompt_for_founder(
    payload: PromptCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Create a new prompt."""
    try:
        prompt = Prompt(
            name=payload.name,
            version=payload.version,
            prompt_text=payload.prompt_text,
            prompt_purpose=payload.prompt_purpose,
            status=payload.status,
            llm_model=payload.llm_model,
        )
        db.add(prompt)
        db.commit()
        db.refresh(prompt)
        return prompt
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="A prompt with this name and version already exists.",
        )
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))


@router.put(
    "/api/founder/prompts/{prompt_id}",
    response_model=PromptResponse,
)
def update_prompt_for_founder(
    prompt_id: UUID,
    payload: PromptUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Update an existing prompt."""
    prompt = db.query(Prompt).filter(Prompt.id == prompt_id).first()
    
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found.")
    
    # Update fields if provided
    if payload.name is not None:
        prompt.name = payload.name
    if payload.version is not None:
        prompt.version = payload.version
    if payload.prompt_text is not None:
        prompt.prompt_text = payload.prompt_text
    if payload.prompt_purpose is not None:
        prompt.prompt_purpose = payload.prompt_purpose
    if payload.status is not None:
        prompt.status = payload.status
    if payload.llm_model is not None:
        prompt.llm_model = payload.llm_model
    
    try:
        db.commit()
        db.refresh(prompt)
        return prompt
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="A prompt with this name and version already exists.",
        )
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete(
    "/api/founder/prompts/{prompt_id}",
    status_code=204,
)
def delete_prompt_for_founder(
    prompt_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Delete a prompt (sets status to archived or actually deletes)."""
    prompt = db.query(Prompt).filter(Prompt.id == prompt_id).first()
    
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found.")
    
    try:
        db.delete(prompt)
        db.commit()
        return None
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))

