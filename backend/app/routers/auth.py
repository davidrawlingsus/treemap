"""
Authentication routes.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from datetime import datetime, timedelta, timezone
from urllib.parse import quote
import logging

from app.database import get_db
from app.models import User, Membership, AuthorizedDomain, AuthorizedEmail, Client
from app.schemas import Token, UserLogin, MagicLinkRequest, MagicLinkVerifyRequest, ImpersonateRequest, UserWithClients, ClientResponse
from app.config import get_settings
from app.auth import (
    get_current_user,
    get_current_active_founder,
    create_access_token,
    generate_magic_link_token,
    is_magic_link_token_valid,
)
from app.services import MagicLinkEmailParams
from app.utils import build_email_service
from app.authorization import get_user_clients

router = APIRouter(prefix="/api/auth", tags=["auth"])
logger = logging.getLogger(__name__)


@router.post("/login", response_model=Token)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Login endpoint - validates email and returns JWT token.
    
    NOTE: Password is optional/ignored. This endpoint is kept for backward compatibility.
    All authentication should use magic link authentication via /api/auth/magic-link/request.
    """
    settings = get_settings()
    is_production = settings.is_production()
    
    # Normalize email input
    email_input = credentials.email.strip().lower()
    searched_email = credentials.email.strip()
    
    # Log the search attempt (always log for debugging)
    print(f"LOGIN DEBUG: Attempt for email: '{searched_email}' (normalized: '{email_input}')")
    
    # Try case-insensitive email lookup
    user = None
    try:
        user = db.query(User).filter(
            func.lower(User.email) == email_input
        ).first()
        
        # If not found, try ilike as fallback
        if not user:
            print(f"LOGIN DEBUG: First lookup failed, trying ilike...")
            user = db.query(User).filter(
                User.email.ilike(f"%{email_input}%")
            ).first()
        
        if user:
            print(f"LOGIN DEBUG: User found: {user.email} (active: {user.is_active}, founder: {user.is_founder})")
        else:
            print(f"LOGIN DEBUG: User not found after both lookup attempts")
            
    except Exception as e:
        # Database error - show helpful message
        print(f"LOGIN DEBUG: Database error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Database error during login: {str(e)}"
        )
    
    if not user:
        # Always show helpful debug info
        try:
            all_users = db.query(User).all()
            available_emails = [u.email for u in all_users]
            user_count = len(available_emails)
            
            print(f"LOGIN DEBUG: No user found. Total users in DB: {user_count}")
            if user_count > 0:
                print(f"LOGIN DEBUG: Available emails: {', '.join(available_emails[:10])}")
            
            if user_count == 0:
                detail = f"Incorrect email or password. No users found in database. Searched for: '{searched_email}'. Please run: railway run python fix_dev_database.py"
            else:
                detail = f"Incorrect email or password. Searched for: '{searched_email}'. Available emails ({user_count}): {', '.join(available_emails[:10])}"
            
            print(f"LOGIN DEBUG: Raising error with detail: {detail}")
            raise HTTPException(status_code=401, detail=detail)
        except HTTPException:
            raise  # Re-raise HTTP exceptions
        except Exception as e:
            # Error getting user list - still show helpful message
            print(f"LOGIN DEBUG: Error listing users: {e}")
            import traceback
            traceback.print_exc()
            detail = f"Incorrect email or password. Searched for: '{searched_email}'. Error listing users: {str(e)}"
            raise HTTPException(status_code=401, detail=detail)
    
    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="User account is inactive"
        )
    
    # Update last login
    try:
        user.last_login_at = datetime.now(timezone.utc)
        db.commit()
    except Exception as e:
        db.rollback()
        if not is_production:
            print(f"Warning: Failed to update last_login_at: {e}")
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/magic-link/request")
def request_magic_link(payload: MagicLinkRequest, db: Session = Depends(get_db)):
    """
    Request a passwordless magic-link for the given email address.
    The email must either:
    1. Belong to an authorized domain mapped to at least one client, OR
    2. Be an individually authorized email mapped to at least one client
    """
    settings = get_settings()
    email = payload.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="A valid email address is required")

    domain = email.split("@")[-1]
    clients = []

    # First, check if the email domain is authorized
    authorized_domain = (
        db.query(AuthorizedDomain)
        .options(joinedload(AuthorizedDomain.clients))
        .filter(func.lower(AuthorizedDomain.domain) == domain.lower())
        .first()
    )

    if authorized_domain:
        clients = [client for client in authorized_domain.clients if client.is_active]
    
    # If no authorized domain or no clients, check for individually authorized email
    if not clients:
        authorized_email = (
            db.query(AuthorizedEmail)
            .options(joinedload(AuthorizedEmail.clients))
            .filter(func.lower(AuthorizedEmail.email) == email)
            .first()
        )
        
        if authorized_email:
            clients = [client for client in authorized_email.clients if client.is_active]
    
    # If still no clients found, reject the request
    if not clients:
        if authorized_domain or authorized_email:
            logger.warning(
                "Email %s is authorized but has no active client associations", email
            )
            raise HTTPException(
                status_code=403,
                detail="No active clients are linked to your email yet. Please contact support.",
            )
        else:
            logger.info("Magic-link denied for unauthorized email: %s", email)
            raise HTTPException(
                status_code=403,
                detail="This email is not authorized. Please contact support.",
            )

    user = (
        db.query(User)
        .filter(func.lower(User.email) == email)
        .first()
    )
    now = datetime.now(timezone.utc)

    if user:
        if (
            user.last_magic_link_sent_at
            and now - user.last_magic_link_sent_at
            < timedelta(seconds=settings.magic_link_rate_limit_seconds)
        ):
            raise HTTPException(
                status_code=429,
                detail="We recently sent you a link. Please check your inbox.",
            )
    else:
        user = User(
            email=email,
            is_active=True,
        )
        db.add(user)
        db.flush()

    token, token_hash, expires_at = generate_magic_link_token()
    logger.info(f"Generated magic link token for {email}")
    
    user.magic_link_token = token_hash
    user.magic_link_expires_at = expires_at
    user.last_magic_link_sent_at = now
    user.is_active = True
    
    db.flush()

    # Ensure memberships exist for all linked clients
    for client in clients:
        membership = (
            db.query(Membership)
            .filter(
                Membership.user_id == user.id,
                Membership.client_id == client.id,
            )
            .first()
        )

        if not membership:
            membership = Membership(
                user_id=user.id,
                client_id=client.id,
                role="viewer",
                status="active",
                provisioned_at=now,
                provisioned_by=user.id,
                provisioning_method="magic_link",
                joined_at=now,
            )
            db.add(membership)
        else:
            membership.status = "active"
            membership.provisioned_at = membership.provisioned_at or now
            membership.provisioned_by = membership.provisioned_by or user.id
            membership.provisioning_method = membership.provisioning_method or "magic_link"
            membership.joined_at = membership.joined_at or now

    email_service = build_email_service(settings)
    if not email_service.is_configured():
        missing_config = []
        if not settings.resend_api_key:
            missing_config.append("RESEND_API_KEY")
        if not settings.resend_from_email:
            missing_config.append("RESEND_FROM_EMAIL")
        logger.error(
            "Resend is not configured. Missing configuration: %s",
            ", ".join(missing_config) if missing_config else "unknown",
        )
        raise HTTPException(
            status_code=500,
            detail="Email service is not configured. Please contact support.",
        )

    redirect_path = settings.magic_link_redirect_path.lstrip("/")
    base_url = settings.frontend_base_url.rstrip("/")
    logger.info(f"Magic link config - frontend_base_url: {settings.frontend_base_url}, base_url: {base_url}")
    if redirect_path:
        magic_link_url = f"{base_url}/{redirect_path}?token={quote(token)}&email={quote(email)}"
    else:
        magic_link_url = f"{base_url}?token={quote(token)}&email={quote(email)}"

    try:
        db.commit()
        logger.info(f"Committed magic link state for {email}")
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to persist magic-link state for %s", email)
        raise HTTPException(
            status_code=500,
            detail="Failed to generate magic link. Please try again.",
        ) from exc

    email_params = MagicLinkEmailParams(
        to_email=email,
        magic_link=magic_link_url,
        client_names=[client.name for client in clients],
        expires_at=expires_at,
    )

    try:
        email_service.send_magic_link_email(email_params)
    except RuntimeError as exc:
        logger.exception("Unable to send magic-link email to %s", email)
        raise HTTPException(
            status_code=502,
            detail="Unable to send the magic link email. Please try again later.",
        ) from exc

    return {
        "message": "Magic link sent. Please check your email.",
        "expires_at": expires_at,
    }


@router.post("/magic-link/verify", response_model=Token)
def verify_magic_link(payload: MagicLinkVerifyRequest, db: Session = Depends(get_db)):
    """Verify a magic-link token and issue a JWT."""
    email = payload.email.strip().lower()
    token = payload.token.strip()
    
    logger.info(f"Magic link verification attempt for email: {email}")
    logger.debug(f"Token (first 10 chars): {token[:10]}...")

    if not email or "@" not in email:
        logger.warning(f"Invalid email format: {email}")
        raise HTTPException(status_code=400, detail="A valid email address is required")
    if not token:
        logger.warning("Missing token in verification request")
        raise HTTPException(status_code=400, detail="Magic-link token is required")

    user = (
        db.query(User)
        .options(
            joinedload(User.memberships).joinedload(Membership.client)
        )
        .filter(func.lower(User.email) == email)
        .first()
    )

    if not user:
        logger.warning(f"User not found for email: {email}")
        raise HTTPException(status_code=400, detail="Invalid or expired magic link")
    
    logger.info(f"Found user: {user.email}, checking token validity")
    logger.debug(f"User has stored token: {bool(user.magic_link_token)}, expires_at: {user.magic_link_expires_at}")
    
    is_valid, error_reason = is_magic_link_token_valid(user, token)
    if not is_valid:
        logger.warning(f"Invalid magic-link token for {email} - reason: {error_reason}")
        
        # Provide more specific error messages based on the failure reason
        error_messages = {
            "no_token_provided": "No authentication token provided",
            "no_stored_token": "No magic link was requested for this email",
            "no_expiration_time": "Invalid magic link state",
            "token_expired": "This magic link has expired. Please request a new one",
            "token_mismatch": "Invalid magic link. The token may have been used or is incorrect",
        }
        
        detail = error_messages.get(error_reason, "Invalid or expired magic link")
        raise HTTPException(status_code=400, detail=detail)

    now = datetime.now(timezone.utc)
    
    # DON'T clear the token immediately - allow reuse within expiry window
    # This protects against email link scanners that pre-fetch URLs
    # Token will naturally expire based on magic_link_expires_at
    logger.info(f"Magic link verified for {email} - token remains valid until expiry")
    
    user.email_verified_at = user.email_verified_at or now
    user.last_login_at = now

    try:
        logger.info(f"Updating user login timestamp for {email}")
        db.commit()
        logger.info(f"Successfully verified magic link for {email}")
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to validate magic link for %s", email)
        raise HTTPException(
            status_code=500,
            detail="Failed to complete sign-in. Please try again.",
        ) from exc

    access_token = create_access_token(data={"sub": str(user.id)})
    logger.info(f"Issued JWT access token for {email}")
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/google/init")
def google_oauth_init():
    """
    Placeholder endpoint for Google OAuth setup.
    Returns configuration status and guidance to set credentials.
    """
    settings = get_settings()
    configured = bool(
        settings.google_oauth_client_id and settings.google_oauth_client_secret
    )
    if not configured:
        raise HTTPException(
            status_code=501,
            detail=(
                "Google OAuth is not configured yet. "
                "Set GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET to enable it."
            ),
        )
    raise HTTPException(
        status_code=501,
        detail="Google OAuth flow is not implemented yet. Configuration detected.",
    )


@router.get("/google/callback")
def google_oauth_callback():
    """Stub callback endpoint for Google OAuth."""
    raise HTTPException(
        status_code=501,
        detail="Google OAuth callback handling is not implemented yet.",
    )


@router.post("/impersonate", response_model=Token)
def impersonate_user(
    payload: ImpersonateRequest,
    current_founder: User = Depends(get_current_active_founder),
    db: Session = Depends(get_db),
):
    """Allow founder users to impersonate another active user."""
    target_user = db.query(User).filter(User.id == payload.user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found")
    if not target_user.is_active:
        raise HTTPException(status_code=403, detail="Target user is inactive")

    logger.info(
        "Founder %s impersonating user %s", current_founder.email, target_user.email
    )
    access_token = create_access_token(data={"sub": str(target_user.id)})
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserWithClients)
def get_current_user_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current authenticated user information with accessible clients."""
    from app.schemas import ClientResponse
    
    # Get all accessible clients using centralized authorization logic
    accessible_clients = get_user_clients(current_user, db)
    
    return UserWithClients(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        is_founder=current_user.is_founder,
        is_active=current_user.is_active,
        email_verified_at=current_user.email_verified_at,
        created_at=current_user.created_at,
        accessible_clients=[ClientResponse(
            id=c.id,
            name=c.name,
            slug=c.slug,
            is_active=c.is_active,
            created_at=c.created_at,
            updated_at=c.updated_at
        ) for c in accessible_clients]
    )

