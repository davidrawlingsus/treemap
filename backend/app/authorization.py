"""
Centralized authorization logic for access control across the application.
"""
from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload
from uuid import UUID
from typing import List

from app.models import Client, Membership, User


def verify_client_access(client_id: UUID, current_user: User, db: Session) -> Client:
    """
    Verify that the current user has access to the specified client.
    
    Access is granted if:
    1. User has an active membership to the client, OR
    2. User is the founder of the client
    
    Args:
        client_id: UUID of the client to check access for
        current_user: The authenticated user
        db: Database session
        
    Returns:
        Client object if access is granted
        
    Raises:
        HTTPException: 404 if client not found, 403 if access denied
    """
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Check if user has access via active membership
    membership = db.query(Membership).filter(
        Membership.user_id == current_user.id,
        Membership.client_id == client_id,
        Membership.status == 'active'
    ).first()
    
    if membership:
        return client
    
    # If user is founder, check if they founded this client
    if current_user.is_founder and client.founder_user_id == current_user.id:
        return client
    
    raise HTTPException(
        status_code=403,
        detail="You do not have access to this client"
    )


def verify_membership(user_id: UUID, client_id: UUID, db: Session) -> Membership:
    """
    Get an active membership or raise an error.
    
    Args:
        user_id: UUID of the user
        client_id: UUID of the client
        db: Database session
        
    Returns:
        Membership object if found and active
        
    Raises:
        HTTPException: 403 if no active membership found
    """
    membership = db.query(Membership).filter(
        Membership.user_id == user_id,
        Membership.client_id == client_id,
        Membership.status == 'active'
    ).first()
    
    if not membership:
        raise HTTPException(
            status_code=403,
            detail="No active membership found for this client"
        )
    
    return membership


def get_user_clients(user: User, db: Session) -> List[Client]:
    """
    Get all clients accessible to a user.
    
    Returns clients where user either:
    1. Has an active membership, OR
    2. Is the founder (created the client)
    
    Args:
        user: The user to get clients for
        db: Database session
        
    Returns:
        List of Client objects the user can access
    """
    # Get clients user has access to via memberships
    memberships = db.query(Membership).filter(
        Membership.user_id == user.id,
        Membership.status == 'active'
    ).options(joinedload(Membership.client)).all()
    
    accessible_clients = [m.client for m in memberships if m.client]
    
    # If user is founder, also include clients they founded
    if user.is_founder:
        founded_clients = db.query(Client).filter(
            Client.founder_user_id == user.id
        ).all()
        # Merge and deduplicate
        client_ids = {c.id for c in accessible_clients}
        for client in founded_clients:
            if client.id not in client_ids:
                accessible_clients.append(client)
    
    return accessible_clients


def check_client_access(client_id: UUID, user_id: UUID, db: Session) -> bool:
    """
    Check if a user has access to a client (without raising exceptions).
    
    Useful for conditional logic where you need to check access without
    halting execution.
    
    Args:
        client_id: UUID of the client
        user_id: UUID of the user
        db: Database session
        
    Returns:
        True if user has access, False otherwise
    """
    # Check for active membership
    membership = db.query(Membership).filter(
        Membership.user_id == user_id,
        Membership.client_id == client_id,
        Membership.status == 'active'
    ).first()
    
    if membership:
        return True
    
    # Check if user is founder of this client
    client = db.query(Client).filter(
        Client.id == client_id,
        Client.founder_user_id == user_id
    ).first()
    
    return bool(client)

