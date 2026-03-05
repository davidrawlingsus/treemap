"""
Usage tracking and trial limit enforcement for subscription tiers.
"""
import logging
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import UsageRecord, Subscription, Plan

logger = logging.getLogger(__name__)


def record_usage(
    client_id: UUID,
    user_id: UUID,
    action_type: str,
    db: Session,
    prompt_id: UUID = None,
    metadata: dict = None,
) -> UsageRecord:
    """Record a usage event (e.g. prompt execution) for a client."""
    record = UsageRecord(
        client_id=client_id,
        user_id=user_id,
        action_type=action_type,
        prompt_id=prompt_id,
        usage_metadata=metadata,
    )
    db.add(record)
    db.commit()
    logger.info(f"Usage recorded: client={client_id} action={action_type}")
    return record


def get_usage_count(client_id: UUID, action_type: str, db: Session) -> int:
    """Count usage records for a client and action type."""
    return (
        db.query(func.count(UsageRecord.id))
        .filter(
            UsageRecord.client_id == client_id,
            UsageRecord.action_type == action_type,
        )
        .scalar()
    )


def check_trial_limit(client_id: UUID, db: Session) -> dict:
    """
    Check if a client is allowed to execute a prompt based on their plan's trial limit.

    Returns:
        dict with keys:
            - allowed (bool): whether the action is permitted
            - remaining (int): how many trial uses are left (None if unlimited)
            - limit (int): the plan's trial limit (0 means unlimited)
            - used (int): how many have been used
            - plan_name (str|None): the client's plan name
    """
    subscription = (
        db.query(Subscription)
        .filter(Subscription.client_id == client_id, Subscription.status == "active")
        .first()
    )

    if not subscription:
        return {"allowed": True, "remaining": None, "limit": 0, "used": 0, "plan_name": None}

    plan = db.query(Plan).filter(Plan.id == subscription.plan_id).first()
    if not plan:
        return {"allowed": True, "remaining": None, "limit": 0, "used": 0, "plan_name": None}

    if plan.trial_limit <= 0:
        return {"allowed": True, "remaining": None, "limit": 0, "used": 0, "plan_name": plan.name}

    used = get_usage_count(client_id, "prompt_execution", db)
    remaining = max(0, plan.trial_limit - used)

    return {
        "allowed": remaining > 0,
        "remaining": remaining,
        "limit": plan.trial_limit,
        "used": used,
        "plan_name": plan.name,
    }
