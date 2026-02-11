"""
Context menu groups management for founder admin.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from uuid import UUID
from typing import List

from app.database import get_db
from app.models import User, ContextMenuGroup, Prompt
from app.schemas import (
    ContextMenuGroupSchema,
    ContextMenuGroupCreate,
    ContextMenuGroupUpdate,
    ContextMenuGroupWithCount,
)
from app.auth import get_current_active_founder

router = APIRouter()


@router.get(
    "/api/founder/context-menu-groups",
    response_model=List[ContextMenuGroupSchema],
)
def list_context_menu_groups(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """List all context menu groups for prompt form dropdown."""
    groups = db.query(ContextMenuGroup).order_by(ContextMenuGroup.sort_order, ContextMenuGroup.label).all()
    return [ContextMenuGroupSchema(id=g.id, label=g.label, sort_order=g.sort_order) for g in groups]


@router.get(
    "/api/founder/context-menu-groups/manage",
    response_model=List[ContextMenuGroupWithCount],
)
def list_context_menu_groups_with_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """List all context menu groups with prompt count for manage modal."""
    groups = db.query(ContextMenuGroup).order_by(ContextMenuGroup.sort_order, ContextMenuGroup.label).all()
    result = []
    for g in groups:
        count = db.query(Prompt).filter(
            Prompt.context_menu_group_id == g.id,
            Prompt.client_facing == True,
        ).count()
        result.append(ContextMenuGroupWithCount(
            id=g.id,
            label=g.label,
            sort_order=g.sort_order,
            prompt_count=count,
        ))
    return result


@router.post(
    "/api/founder/context-menu-groups",
    response_model=ContextMenuGroupSchema,
)
def create_context_menu_group(
    payload: ContextMenuGroupCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Create a new context menu group."""
    max_order = db.query(func.coalesce(func.max(ContextMenuGroup.sort_order), -1)).scalar()
    group = ContextMenuGroup(
        label=payload.label.strip(),
        sort_order=payload.sort_order if payload.sort_order is not None else max_order + 1,
    )
    db.add(group)
    db.commit()
    db.refresh(group)
    return ContextMenuGroupSchema(id=group.id, label=group.label, sort_order=group.sort_order)


@router.patch(
    "/api/founder/context-menu-groups/{group_id}",
    response_model=ContextMenuGroupSchema,
)
def update_context_menu_group(
    group_id: UUID,
    payload: ContextMenuGroupUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Update a context menu group."""
    group = db.query(ContextMenuGroup).filter(ContextMenuGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Context menu group not found")

    if payload.label is not None:
        group.label = payload.label.strip()
    if payload.sort_order is not None:
        group.sort_order = payload.sort_order

    db.commit()
    db.refresh(group)
    return ContextMenuGroupSchema(id=group.id, label=group.label, sort_order=group.sort_order)


@router.delete(
    "/api/founder/context-menu-groups/{group_id}",
    status_code=204,
)
def delete_context_menu_group(
    group_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Delete a context menu group. Fails with 409 if group has prompts."""
    group = db.query(ContextMenuGroup).filter(ContextMenuGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Context menu group not found")

    prompt_count = db.query(Prompt).filter(Prompt.context_menu_group_id == group_id).count()
    if prompt_count > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete: {prompt_count} prompt(s) use this group. Reassign or remove them first.",
        )

    db.delete(group)
    db.commit()
    return None
