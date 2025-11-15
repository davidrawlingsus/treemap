from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import text, or_, func
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
import json
import os
from uuid import UUID
from pathlib import Path
from urllib.parse import quote, urlparse
import logging

from app.database import get_db, engine, Base
from app.models import (
    Client,
    DataSource,
    DimensionName,
    User,
    Membership,
    ProcessVoc,
    AuthorizedDomain,
    AuthorizedDomainClient,
)
from app.schemas import (
    ClientCreate,
    ClientResponse,
    DataSourceCreate,
    DataSourceDetail,
    DataSourceResponse,
    DimensionNameBatchUpdate,
    DimensionNameCreate,
    DimensionNameResponse,
    DimensionQuestionInfo,
    FieldMetadata,
    FieldMetadataResponse,
    FounderUserMembership,
    FounderUserSummary,
    ImpersonateRequest,
    MagicLinkRequest,
    MagicLinkVerifyRequest,
    ProcessVocAdminListResponse,
    ProcessVocBulkUpdateRequest,
    ProcessVocBulkUpdateResponse,
    ProcessVocListResponse,
    ProcessVocResponse,
    QuestionInfo,
    AuthorizedDomainCreate,
    AuthorizedDomainResponse,
    AuthorizedDomainUpdate,
    DataSourceWithQuestions,
    DynamicBulkUpdateRequest,
    Token,
    UserLogin,
    UserResponse,
    UserWithClients,
    VocClientInfo,
    VocProjectInfo,
    VocSourceInfo,
)
from app.transformers import DataTransformer, DataSourceType
from app.config import get_settings
from app.auth import (
    get_current_user, get_current_active_founder,
    create_access_token, verify_password,
    generate_magic_link_token, is_magic_link_token_valid, clear_magic_link_state,
)
from app.services import EmailService, MagicLinkEmailParams
from datetime import datetime, timedelta, timezone


logger = logging.getLogger(__name__)


def extract_origin(url: str | None) -> Optional[str]:
    """Return the origin (scheme + host [+ port]) from a URL-like string."""
    if not url:
        return None
    parsed = urlparse(url.strip())
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"
    return None


settings_for_cors = get_settings()
cors_allow_origins: List[str] = []

primary_origin = extract_origin(settings_for_cors.frontend_base_url)
if primary_origin:
    cors_allow_origins.append(primary_origin)

for origin in settings_for_cors.get_additional_cors_origins():
    normalized_origin = extract_origin(origin)
    if normalized_origin and normalized_origin not in cors_allow_origins:
        cors_allow_origins.append(normalized_origin)

if cors_allow_origins:
    logger.info("Allowing additional CORS origins: %s", cors_allow_origins)


def build_email_service(settings):
    """Instantiate an EmailService based on current settings."""
    return EmailService(
        api_key=settings.resend_api_key,
        from_email=settings.resend_from_email,
        reply_to_email=settings.resend_reply_to_email,
    )


def serialize_authorized_domain(domain: AuthorizedDomain) -> AuthorizedDomainResponse:
    """Convert an AuthorizedDomain ORM object into a response model."""
    clients = [
        ClientResponse.model_validate(link.client)
        for link in domain.client_links
        if link.client is not None
    ]
    clients.sort(key=lambda client: client.name.lower())
    return AuthorizedDomainResponse(
        id=domain.id,
        domain=domain.domain,
        description=domain.description,
        created_at=domain.created_at,
        updated_at=domain.updated_at,
        clients=clients,
    )


# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Visualizd API", version="0.1.0")

# CORS configuration - allow frontend to communicate with backend
# Allow all Railway origins (they use *.up.railway.app pattern) for flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(.*\.up\.railway\.app|localhost)(:\d+)?$",  # Allow all Railway URLs and localhost
    allow_origins=cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files from the parent directory (where index.html is)
# This allows accessing the frontend at http://localhost:8000/index.html
frontend_path = Path(__file__).parent.parent.parent
if (frontend_path / "index.html").exists():
    # Mount static files directory to serve CSS, JS, and other assets
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")
    
    @app.get("/", response_class=FileResponse)
    def serve_index():
        """Serve the frontend index.html"""
        return FileResponse(frontend_path / "index.html")
    
    @app.get("/magic-login", response_class=FileResponse)
    def serve_magic_login():
        """Serve the magic login page (same as index for SPA routing)"""
        return FileResponse(frontend_path / "index.html")
    
    @app.get("/index.html", response_class=FileResponse)
    def serve_index_html():
        """Serve the frontend index.html"""
        return FileResponse(frontend_path / "index.html")
    
    # Serve config.js dynamically
    @app.get("/config.js")
    def serve_config():
        """Serve dynamic config.js with API URL"""
        from fastapi.responses import Response
        api_url = "http://localhost:8000"
        config_content = f"window.APP_CONFIG = {{ API_BASE_URL: '{api_url}' }};"
        return Response(content=config_content, media_type="application/javascript")
    
    # Serve static files directly (styles.css, header.js, etc.)
    # Only match specific file extensions to avoid conflicting with API routes
    @app.get("/styles.css")
    def serve_styles():
        """Serve styles.css"""
        from fastapi.responses import Response
        file_path = frontend_path / "styles.css"
        if file_path.exists():
            with open(file_path, 'r') as f:
                content = f.read()
            return Response(content=content, media_type="text/css")
        raise HTTPException(status_code=404, detail="File not found")
    
    @app.get("/header.js")
    def serve_header():
        """Serve header.js"""
        from fastapi.responses import Response
        file_path = frontend_path / "header.js"
        if file_path.exists():
            with open(file_path, 'r') as f:
                content = f.read()
            return Response(content=content, media_type="application/javascript")
        raise HTTPException(status_code=404, detail="File not found")

    @app.get("/auth.js")
    def serve_auth_js():
        """Serve auth.js"""
        from fastapi.responses import Response
        file_path = frontend_path / "auth.js"
        if file_path.exists():
            with open(file_path, 'r') as f:
                content = f.read()
            return Response(content=content, media_type="application/javascript")
        raise HTTPException(status_code=404, detail="File not found")

if (frontend_path / "founder_admin.html").exists():
    @app.get("/founder_admin", response_class=FileResponse)
    def serve_founder_admin():
        """Serve the founder admin page"""
        return FileResponse(frontend_path / "founder_admin.html")
    
    @app.get("/founder_admin.html", response_class=FileResponse)
    def serve_founder_admin_html():
        """Serve the founder admin page"""
        return FileResponse(frontend_path / "founder_admin.html")

if (frontend_path / "founder_impersonation.html").exists():
    @app.get("/founder_impersonation", response_class=FileResponse)
    def serve_founder_impersonation():
        """Serve the founder impersonation helper page"""
        return FileResponse(frontend_path / "founder_impersonation.html")

    @app.get("/founder_impersonation.html", response_class=FileResponse)
    def serve_founder_impersonation_html():
        """Serve the founder impersonation helper page"""
        return FileResponse(frontend_path / "founder_impersonation.html")

@app.get("/api")
def api_info():
    """API information endpoint"""
    return {"message": "Visualizd API", "version": "0.1.0"}


@app.get("/api/debug/users")
def debug_users(db: Session = Depends(get_db)):
    """Debug endpoint to list all users - for troubleshooting login"""
    users = db.query(User).all()
    return {
        "total_users": len(users),
        "users": [
            {
                "email": u.email,
                "name": u.name,
                "is_active": u.is_active,
                "is_founder": u.is_founder
            }
            for u in users
        ]
    }


@app.get("/api/debug/magic-link-state")
def debug_magic_link_state(email: str, db: Session = Depends(get_db)):
    """Debug endpoint to check magic link state for a user"""
    user = db.query(User).filter(func.lower(User.email) == email.lower()).first()
    
    if not user:
        raise HTTPException(status_code=404, detail=f"User not found: {email}")
    
    return {
        "email": user.email,
        "has_magic_link_token": user.magic_link_token is not None,
        "token_hash_preview": user.magic_link_token[:10] + "..." if user.magic_link_token else None,
        "magic_link_expires_at": user.magic_link_expires_at.isoformat() if user.magic_link_expires_at else None,
        "last_magic_link_sent_at": user.last_magic_link_sent_at.isoformat() if user.last_magic_link_sent_at else None,
        "is_active": user.is_active,
        "email_verified_at": user.email_verified_at.isoformat() if user.email_verified_at else None,
    }


@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Check if API and database are working"""
    try:
        # Test database connection
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


# Authentication Endpoints
@app.post("/api/auth/login", response_model=Token)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Login endpoint - validates email and returns JWT token.
    
    NOTE: For now, this accepts any email from the users table without password validation.
    Password fields may not exist in the Railway database yet.
    """
    settings = get_settings()
    is_production = settings.environment.lower() in {"production", "prod", "production2"}
    
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
    
    # NOTE: Password validation is disabled - any password is accepted
    # TODO: Add password verification when password fields are added
    # if not verify_password(credentials.password, user.hashed_password):
    #     raise HTTPException(status_code=401, detail="Incorrect email or password")
    
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


@app.post("/api/auth/magic-link/request")
def request_magic_link(payload: MagicLinkRequest, db: Session = Depends(get_db)):
    """
    Request a passwordless magic-link for the given email address.
    The email must belong to an authorized domain mapped to at least one client.
    """
    settings = get_settings()
    email = payload.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="A valid email address is required")

    domain = email.split("@")[-1]

    authorized_domain = (
        db.query(AuthorizedDomain)
        .options(joinedload(AuthorizedDomain.clients))
        .filter(func.lower(AuthorizedDomain.domain) == domain.lower())
        .first()
    )

    if not authorized_domain:
        logger.info("Magic-link denied for unauthorized domain: %s", domain)
        raise HTTPException(
            status_code=403,
            detail="This email domain is not authorized. Please contact support.",
        )

    clients = [client for client in authorized_domain.clients if client.is_active]
    if not clients:
        logger.warning(
            "Authorized domain %s has no active client associations", domain
        )
        raise HTTPException(
            status_code=403,
            detail="No active clients are linked to this domain yet. Please contact support.",
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
    logger.warning(f"🔑 Generated magic link token for {email} - expires at: {expires_at}")
    logger.warning(f"🔑 Token hash (first 10 chars): {token_hash[:10]}...")
    
    user.magic_link_token = token_hash
    user.magic_link_expires_at = expires_at
    user.last_magic_link_sent_at = now
    user.is_active = True
    
    # Flush to ensure user fields are updated in the session
    db.flush()
    logger.debug(f"Flushed user magic link state to session")

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
    if redirect_path:
        magic_link_url = f"{base_url}/{redirect_path}?token={quote(token)}&email={quote(email)}"
    else:
        magic_link_url = f"{base_url}?token={quote(token)}&email={quote(email)}"

    try:
        logger.warning(f"💾 Committing magic link state for {email} to database")
        db.commit()
        logger.warning(f"✅ Successfully committed magic link token for {email}")
        
        # Verify the commit by re-querying the user from database
        db.expire(user)  # Expire cached data
        verification_user = db.query(User).filter(func.lower(User.email) == email).first()
        if verification_user and verification_user.magic_link_token:
            logger.warning(f"✅ Verified token persistence - stored hash (first 10): {verification_user.magic_link_token[:10]}...")
            logger.warning(f"✅ Token expires at: {verification_user.magic_link_expires_at}")
        else:
            logger.error(f"Token verification failed - token not found in database for {email}")
            raise HTTPException(
                status_code=500,
                detail="Failed to persist magic link token. Please try again.",
            )
    except HTTPException:
        raise
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


@app.post("/api/auth/magic-link/verify", response_model=Token)
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


@app.get("/api/auth/google/init")
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


@app.get("/api/auth/google/callback")
def google_oauth_callback():
    """Stub callback endpoint for Google OAuth."""
    raise HTTPException(
        status_code=501,
        detail="Google OAuth callback handling is not implemented yet.",
    )


@app.post("/api/auth/impersonate", response_model=Token)
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


@app.get("/api/auth/me", response_model=UserWithClients)
def get_current_user_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current authenticated user information with accessible clients."""
    # Get clients user has access to via memberships
    memberships = db.query(Membership).filter(
        Membership.user_id == current_user.id,
        Membership.status == 'active'
    ).options(joinedload(Membership.client)).all()
    
    accessible_clients = [m.client for m in memberships if m.client]
    
    # If user is founder, also include clients they founded
    if current_user.is_founder:
        founded_clients = db.query(Client).filter(
            Client.founder_user_id == current_user.id
        ).all()
        # Merge and deduplicate
        client_ids = {c.id for c in accessible_clients}
        for client in founded_clients:
            if client.id not in client_ids:
                accessible_clients.append(client)
    
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


@app.get("/api/founder/users", response_model=List[FounderUserSummary])
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


@app.get(
    "/api/founder/authorized-domains",
    response_model=List[AuthorizedDomainResponse],
)
def list_authorized_domains_for_founder(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """List authorized domains with associated clients for founder tooling."""
    domains = (
        db.query(AuthorizedDomain)
        .options(
            joinedload(AuthorizedDomain.client_links).joinedload(
                AuthorizedDomainClient.client
            )
        )
        .order_by(func.lower(AuthorizedDomain.domain))
        .all()
    )

    return [serialize_authorized_domain(domain) for domain in domains]


@app.post(
    "/api/founder/authorized-domains",
    response_model=AuthorizedDomainResponse,
    status_code=201,
)
def create_authorized_domain_for_founder(
    payload: AuthorizedDomainCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Create a new authorized domain and associate it with clients."""
    normalized_domain = payload.domain.strip().lower()
    if not normalized_domain:
        raise HTTPException(status_code=400, detail="Domain is required.")

    existing = (
        db.query(AuthorizedDomain)
        .filter(func.lower(AuthorizedDomain.domain) == normalized_domain)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=400, detail="An authorized domain with this name already exists."
        )

    client_ids = set(payload.client_ids or [])
    clients: List[Client] = []
    if client_ids:
        clients = db.query(Client).filter(Client.id.in_(client_ids)).all()
        found_ids = {client.id for client in clients}
        missing = client_ids - found_ids
        if missing:
            raise HTTPException(
                status_code=404,
                detail="One or more selected clients were not found.",
            )

    authorized_domain = AuthorizedDomain(
        domain=normalized_domain,
        description=payload.description.strip() if payload.description else None,
    )
    authorized_domain.clients = clients

    try:
        db.add(authorized_domain)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400, detail="An authorized domain with this name already exists."
        )
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))

    created_domain = (
        db.query(AuthorizedDomain)
        .options(
            joinedload(AuthorizedDomain.client_links).joinedload(
                AuthorizedDomainClient.client
            )
        )
        .filter(AuthorizedDomain.id == authorized_domain.id)
        .one()
    )

    return serialize_authorized_domain(created_domain)


@app.put(
    "/api/founder/authorized-domains/{domain_id}",
    response_model=AuthorizedDomainResponse,
)
def update_authorized_domain_for_founder(
    domain_id: UUID,
    payload: AuthorizedDomainUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Update an existing authorized domain and its client associations."""
    authorized_domain = (
        db.query(AuthorizedDomain)
        .options(joinedload(AuthorizedDomain.client_links))
        .filter(AuthorizedDomain.id == domain_id)
        .first()
    )

    if not authorized_domain:
        raise HTTPException(status_code=404, detail="Authorized domain not found.")

    normalized_domain = payload.domain.strip().lower()
    if not normalized_domain:
        raise HTTPException(status_code=400, detail="Domain is required.")

    if normalized_domain != authorized_domain.domain:
        duplicate = (
            db.query(AuthorizedDomain)
            .filter(func.lower(AuthorizedDomain.domain) == normalized_domain)
            .filter(AuthorizedDomain.id != domain_id)
            .first()
        )
        if duplicate:
            raise HTTPException(
                status_code=400,
                detail="Another authorized domain with this name already exists.",
            )
        authorized_domain.domain = normalized_domain

    authorized_domain.description = (
        payload.description.strip() if payload.description else None
    )

    if payload.client_ids is not None:
        client_ids = set(payload.client_ids)
        clients: List[Client] = []
        if client_ids:
            clients = db.query(Client).filter(Client.id.in_(client_ids)).all()
            found_ids = {client.id for client in clients}
            missing = client_ids - found_ids
            if missing:
                raise HTTPException(
                    status_code=404,
                    detail="One or more selected clients were not found.",
                )
        authorized_domain.clients = clients

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400, detail="An authorized domain with this name already exists."
        )
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))

    updated_domain = (
        db.query(AuthorizedDomain)
        .options(
            joinedload(AuthorizedDomain.client_links).joinedload(
                AuthorizedDomainClient.client
            )
        )
        .filter(AuthorizedDomain.id == domain_id)
        .one()
    )

    return serialize_authorized_domain(updated_domain)


@app.post("/api/data-sources/upload", response_model=DataSourceResponse)
async def upload_data_source(
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    source_type: Optional[str] = Form(None),
    auto_detect: bool = Form(True),
    db: Session = Depends(get_db)
):
    """
    Upload a JSON file as a data source.
    
    Args:
        file: JSON file to upload
        name: Optional name for the data source (defaults to filename)
        source_type: Optional source format type (will auto-detect if not provided)
        auto_detect: Whether to auto-detect the format (default: True)
        db: Database session
    """
    try:
        # Read the uploaded file
        contents = await file.read()
        raw_data = json.loads(contents)
        
        # Validate that raw_data is a list
        if not isinstance(raw_data, list):
            raise HTTPException(
                status_code=400, 
                detail="JSON data must be an array of objects"
            )
        
        # Use filename as name if not provided
        if not name:
            name = file.filename.replace('.json', '')
        
        # Detect or use provided source type
        detected_format = None
        if auto_detect:
            detected_format = DataTransformer.detect_format(raw_data)
            print(f"Auto-detected format: {detected_format}")
        elif source_type:
            try:
                detected_format = DataSourceType(source_type)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid source_type. Must be one of: {[t.value for t in DataSourceType]}"
                )
        else:
            detected_format = DataSourceType.GENERIC
        
        # Transform data to normalized format
        normalized_data = DataTransformer.transform(raw_data, detected_format)
        
        print(f"Transformed {len(raw_data)} raw rows into {len(normalized_data)} normalized rows")
        
        # Create data source
        data_source = DataSource(
            name=name,
            source_type=source_type or "generic",
            source_format=detected_format.value,
            raw_data=raw_data,
            normalized_data=normalized_data,
            is_normalized=True
        )
        
        db.add(data_source)
        db.commit()
        db.refresh(data_source)
        
        return data_source
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")
    except Exception as e:
        db.rollback()
        print(f"Error uploading data source: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/data-sources", response_model=DataSourceResponse)
def create_data_source(data: DataSourceCreate, db: Session = Depends(get_db)):
    """Create a data source from JSON payload"""
    try:
        data_source = DataSource(
            name=data.name,
            source_type=data.source_type,
            raw_data=data.raw_data
        )
        
        db.add(data_source)
        db.commit()
        db.refresh(data_source)
        
        return data_source
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/data-sources", response_model=List[DataSourceResponse])
def list_data_sources(
    client_id: Optional[UUID] = None,
    source_name: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all data sources (without raw_data), with optional filtering"""
    query = db.query(DataSource).options(joinedload(DataSource.client))
    
    if client_id:
        query = query.filter(DataSource.client_id == client_id)
    if source_name:
        query = query.filter(DataSource.source_name == source_name)
    
    data_sources = query.all()
    
    # Add client_name to response
    result = []
    for ds in data_sources:
        ds_dict = {
            'id': ds.id,
            'name': ds.name,
            'client_id': ds.client_id,
            'source_name': ds.source_name,
            'source_type': ds.source_type,
            'source_format': ds.source_format,
            'is_normalized': ds.is_normalized,
            'created_at': ds.created_at,
            'updated_at': ds.updated_at,
            'client_name': ds.client.name if ds.client else None
        }
        result.append(ds_dict)
    
    return result


def enrich_data_with_dimension_names(data: list, dimension_names_map: dict) -> list:
    """
    Enrich normalized data with dimension names from the map.
    Adds dimension_name to metadata for LLM context.
    """
    if not data:
        return data
    
    enriched = []
    for row in data:
        if isinstance(row, dict):
            ref_key = row.get('metadata', {}).get('ref_key')
            if ref_key and ref_key in dimension_names_map:
                if 'metadata' not in row:
                    row['metadata'] = {}
                row['metadata']['dimension_name'] = dimension_names_map[ref_key]
        enriched.append(row)
    
    return enriched


@app.get("/api/data-sources/{data_source_id}", response_model=DataSourceDetail)
def get_data_source(data_source_id: UUID, use_raw: bool = False, db: Session = Depends(get_db)):
    """
    Get a specific data source with full data.
    Enriches the data with dimension names for LLM context.
    
    Args:
        data_source_id: UUID of the data source
        use_raw: If True, return raw_data; if False, return normalized_data (default)
        db: Database session
    """
    data_source = db.query(DataSource).options(
        joinedload(DataSource.dimension_names)
    ).filter(DataSource.id == data_source_id).first()
    
    if not data_source:
        raise HTTPException(status_code=404, detail="Data source not found")
    
    # Build dimension names map
    dimension_map = {dn.ref_key: dn.custom_name for dn in data_source.dimension_names}
    
    # Enrich data with dimension names for LLM context
    if data_source.normalized_data and dimension_map:
        data_source.normalized_data = enrich_data_with_dimension_names(
            data_source.normalized_data, 
            dimension_map
        )
    
    # Return the appropriate data format
    # The response model will handle serialization
    return data_source


@app.delete("/api/data-sources/{data_source_id}")
def delete_data_source(data_source_id: UUID, db: Session = Depends(get_db)):
    """Delete a data source"""
    data_source = db.query(DataSource).filter(DataSource.id == data_source_id).first()
    
    if not data_source:
        raise HTTPException(status_code=404, detail="Data source not found")
    
    db.delete(data_source)
    db.commit()
    
    return {"message": "Data source deleted successfully"}


# Client Endpoints
@app.get("/api/clients", response_model=List[ClientResponse])
def list_clients(db: Session = Depends(get_db)):
    """List all clients"""
    clients = db.query(Client).order_by(Client.name).all()
    return clients


@app.post("/api/clients", response_model=ClientResponse)
def create_client(client: ClientCreate, db: Session = Depends(get_db)):
    """Create a new client"""
    try:
        # Check if client with same name or slug already exists
        existing = db.query(Client).filter(
            (Client.name == client.name) | (Client.slug == client.slug)
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=400,
                detail="Client with this name or slug already exists"
            )
        
        db_client = Client(**client.model_dump())
        db.add(db_client)
        db.commit()
        db.refresh(db_client)
        
        return db_client
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/clients/{client_id}", response_model=ClientResponse)
def get_client(client_id: UUID, db: Session = Depends(get_db)):
    """Get a specific client"""
    client = db.query(Client).filter(Client.id == client_id).first()
    
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    return client


@app.get("/api/clients/{client_id}/sources", response_model=List[DataSourceResponse])
def list_client_sources(client_id: UUID, db: Session = Depends(get_db)):
    """List all data sources for a specific client"""
    # Verify client exists
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    data_sources = db.query(DataSource).filter(
        DataSource.client_id == client_id
    ).options(joinedload(DataSource.client)).all()
    
    # Add client_name to response
    result = []
    for ds in data_sources:
        ds_dict = {
            'id': ds.id,
            'name': ds.name,
            'client_id': ds.client_id,
            'source_name': ds.source_name,
            'source_type': ds.source_type,
            'source_format': ds.source_format,
            'is_normalized': ds.is_normalized,
            'created_at': ds.created_at,
            'updated_at': ds.updated_at,
            'client_name': ds.client.name if ds.client else None
        }
        result.append(ds_dict)
    
    return result


@app.get("/api/data-sources/{data_source_id}/questions", response_model=DataSourceWithQuestions)
def get_data_source_questions(data_source_id: UUID, db: Session = Depends(get_db)):
    """
    Get available questions for a data source.
    Detects ref_* fields that contain objects with 'text' and 'topics' fields.
    Includes custom dimension names if assigned.
    """
    data_source = db.query(DataSource).options(
        joinedload(DataSource.client),
        joinedload(DataSource.dimension_names)
    ).filter(
        DataSource.id == data_source_id
    ).first()
    
    if not data_source:
        raise HTTPException(status_code=404, detail="Data source not found")
    
    # Build a map of ref_key -> custom_name from dimension_names
    dimension_name_map = {
        dn.ref_key: dn.custom_name 
        for dn in data_source.dimension_names
    }
    
    # Detect questions from normalized_data
    questions = []
    data = data_source.normalized_data if data_source.normalized_data else data_source.raw_data
    
    if data and isinstance(data, list) and len(data) > 0:
        # Look for ref_key in metadata (normalized format)
        question_refs = {}
        
        for row in data[:min(100, len(data))]:
            if not isinstance(row, dict):
                continue
            
            # Check for normalized format with metadata.ref_key
            if 'metadata' in row and isinstance(row['metadata'], dict):
                ref_key = row['metadata'].get('ref_key')
                if ref_key and ref_key not in question_refs:
                    question_refs[ref_key] = {
                        'ref_key': ref_key,
                        'sample_text': row.get('text', '')[:100],  # First 100 chars
                        'response_count': 0,
                        'custom_name': dimension_name_map.get(ref_key)
                    }
            # Also check for raw format with ref_* keys
            else:
                for key, value in row.items():
                    if key.startswith('ref_') and isinstance(value, dict):
                        if 'text' in value and 'topics' in value:
                            if key not in question_refs:
                                question_refs[key] = {
                                    'ref_key': key,
                                    'sample_text': value.get('text', '')[:100],
                                    'response_count': 0,
                                    'custom_name': dimension_name_map.get(key)
                                }
        
        # Count responses for each question
        for row in data:
            if not isinstance(row, dict):
                continue
                
            # Count in normalized format
            if 'metadata' in row and isinstance(row['metadata'], dict):
                ref_key = row['metadata'].get('ref_key')
                if ref_key in question_refs:
                    question_refs[ref_key]['response_count'] += 1
            # Count in raw format
            else:
                for key in question_refs.keys():
                    if key in row and isinstance(row[key], dict) and 'text' in row[key]:
                        question_refs[key]['response_count'] += 1
        
        questions = list(question_refs.values())
    
    # Build response
    result = {
        'id': data_source.id,
        'name': data_source.name,
        'client_id': data_source.client_id,
        'source_name': data_source.source_name,
        'source_type': data_source.source_type,
        'source_format': data_source.source_format,
        'is_normalized': data_source.is_normalized,
        'created_at': data_source.created_at,
        'updated_at': data_source.updated_at,
        'client_name': data_source.client.name if data_source.client else None,
        'questions': questions
    }
    
    return result


# Dimension Names Endpoints

@app.get("/api/data-sources/{data_source_id}/dimension-names", response_model=List[DimensionNameResponse])
def get_dimension_names(data_source_id: UUID, db: Session = Depends(get_db)):
    """
    Get all custom dimension names for a data source.
    """
    # Verify data source exists
    data_source = db.query(DataSource).filter(DataSource.id == data_source_id).first()
    if not data_source:
        raise HTTPException(status_code=404, detail="Data source not found")
    
    dimension_names = db.query(DimensionName).filter(
        DimensionName.data_source_id == data_source_id
    ).all()
    
    return dimension_names


@app.post("/api/data-sources/{data_source_id}/dimension-names", response_model=DimensionNameResponse)
def create_or_update_dimension_name(
    data_source_id: UUID,
    dimension_data: DimensionNameCreate,
    db: Session = Depends(get_db)
):
    """
    Create or update a single dimension name for a data source.
    Also enriches the normalized_data JSON with the dimension name for LLM context.
    """
    # Verify data source exists
    data_source = db.query(DataSource).filter(DataSource.id == data_source_id).first()
    if not data_source:
        raise HTTPException(status_code=404, detail="Data source not found")
    
    # Check if dimension name already exists
    existing = db.query(DimensionName).filter(
        DimensionName.data_source_id == data_source_id,
        DimensionName.ref_key == dimension_data.ref_key
    ).first()
    
    if existing:
        # Update existing
        existing.custom_name = dimension_data.custom_name
    else:
        # Create new
        existing = DimensionName(
            data_source_id=data_source_id,
            ref_key=dimension_data.ref_key,
            custom_name=dimension_data.custom_name
        )
        db.add(existing)
    
    # ENRICH THE JSON: Update normalized_data to include dimension name
    if data_source.normalized_data:
        for row in data_source.normalized_data:
            if isinstance(row, dict) and row.get('metadata', {}).get('ref_key') == dimension_data.ref_key:
                # Add dimension_name to metadata
                if 'metadata' not in row:
                    row['metadata'] = {}
                row['metadata']['dimension_name'] = dimension_data.custom_name
        
        # Mark the column as modified so SQLAlchemy knows to update it
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(data_source, 'normalized_data')
    
    db.commit()
    db.refresh(existing)
    return existing


@app.post("/api/data-sources/{data_source_id}/dimension-names/batch", response_model=List[DimensionNameResponse])
def batch_update_dimension_names(
    data_source_id: UUID,
    batch_data: DimensionNameBatchUpdate,
    db: Session = Depends(get_db)
):
    """
    Batch create or update multiple dimension names for a data source.
    Also enriches the normalized_data JSON with dimension names for LLM context.
    """
    # Verify data source exists
    data_source = db.query(DataSource).filter(DataSource.id == data_source_id).first()
    if not data_source:
        raise HTTPException(status_code=404, detail="Data source not found")
    
    results = []
    
    # Build a map of ref_key -> custom_name
    dimension_map = {d.ref_key: d.custom_name for d in batch_data.dimension_names}
    
    for dimension_data in batch_data.dimension_names:
        # Check if dimension name already exists
        existing = db.query(DimensionName).filter(
            DimensionName.data_source_id == data_source_id,
            DimensionName.ref_key == dimension_data.ref_key
        ).first()
        
        if existing:
            # Update existing
            existing.custom_name = dimension_data.custom_name
            results.append(existing)
        else:
            # Create new
            new_dimension_name = DimensionName(
                data_source_id=data_source_id,
                ref_key=dimension_data.ref_key,
                custom_name=dimension_data.custom_name
            )
            db.add(new_dimension_name)
            results.append(new_dimension_name)
    
    # ENRICH THE JSON: Update normalized_data to include all dimension names
    if data_source.normalized_data:
        for row in data_source.normalized_data:
            if isinstance(row, dict):
                ref_key = row.get('metadata', {}).get('ref_key')
                if ref_key and ref_key in dimension_map:
                    # Add dimension_name to metadata
                    if 'metadata' not in row:
                        row['metadata'] = {}
                    row['metadata']['dimension_name'] = dimension_map[ref_key]
        
        # Mark the column as modified so SQLAlchemy knows to update it
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(data_source, 'normalized_data')
    
    db.commit()
    
    # Refresh all objects
    for result in results:
        db.refresh(result)
    
    return results


@app.delete("/api/data-sources/{data_source_id}/dimension-names/{ref_key}")
def delete_dimension_name(
    data_source_id: UUID,
    ref_key: str,
    db: Session = Depends(get_db)
):
    """
    Delete a custom dimension name.
    """
    dimension_name = db.query(DimensionName).filter(
        DimensionName.data_source_id == data_source_id,
        DimensionName.ref_key == ref_key
    ).first()
    
    if not dimension_name:
        raise HTTPException(status_code=404, detail="Dimension name not found")
    
    db.delete(dimension_name)
    db.commit()
    
    return {"message": "Dimension name deleted successfully"}


# ProcessVoc Endpoints

@app.get("/api/voc/data", response_model=List[ProcessVocResponse])
def get_voc_data(
    client_uuid: Optional[UUID] = None,
    data_source: Optional[str] = None,
    project_name: Optional[str] = None,
    dimension_ref: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get process_voc rows with optional filtering.
    
    Query parameters:
    - client_uuid: Filter by client UUID (will match by UUID or by client name if UUID is null)
    - data_source: Filter by data source name (e.g., "email_survey")
    - project_name: Filter by project name
    - dimension_ref: Filter by dimension reference (e.g., "ref_ljwfv")
    """
    query = db.query(ProcessVoc)
    
    if client_uuid:
        # First, try to get client name from clients table
        client = db.query(Client).filter(Client.id == client_uuid).first()
        
        if client:
            # Filter by client_uuid OR by client_name (for rows where client_uuid is null)
            query = query.filter(
                or_(
                    ProcessVoc.client_uuid == client_uuid,
                    ProcessVoc.client_name == client.name
                )
            )
        else:
            # Fallback to just UUID if client not found
            query = query.filter(ProcessVoc.client_uuid == client_uuid)
    
    if data_source:
        query = query.filter(ProcessVoc.data_source == data_source)
    if project_name:
        query = query.filter(ProcessVoc.project_name == project_name)
    if dimension_ref:
        query = query.filter(ProcessVoc.dimension_ref == dimension_ref)
    
    return query.all()


@app.get("/api/voc/questions", response_model=List[DimensionQuestionInfo])
def get_voc_questions(
    client_uuid: Optional[UUID] = None,
    data_source: Optional[str] = None,
    project_name: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    List available dimensions/questions in process_voc.
    
    Query parameters:
    - client_uuid: Filter by client UUID (will match by UUID or by client name if UUID is null)
    - data_source: Filter by data source name
    - project_name: Filter by project name
    """
    from sqlalchemy import func
    
    query = db.query(
        ProcessVoc.dimension_ref,
        ProcessVoc.dimension_name,
        func.count(ProcessVoc.id).label('response_count')
    )
    
    if client_uuid:
        # Get client name for matching
        client = db.query(Client).filter(Client.id == client_uuid).first()
        if client:
            # Filter by client_uuid OR by client_name (for rows where client_uuid is null)
            query = query.filter(
                or_(
                    ProcessVoc.client_uuid == client_uuid,
                    ProcessVoc.client_name == client.name
                )
            )
        else:
            query = query.filter(ProcessVoc.client_uuid == client_uuid)
    
    if data_source:
        query = query.filter(ProcessVoc.data_source == data_source)
    if project_name:
        query = query.filter(ProcessVoc.project_name == project_name)
    
    query = query.group_by(
        ProcessVoc.dimension_ref,
        ProcessVoc.dimension_name
    )
    
    results = query.all()
    
    return [
        DimensionQuestionInfo(
            dimension_ref=row.dimension_ref,
            dimension_name=row.dimension_name,
            response_count=row.response_count
        )
        for row in results
    ]


@app.get("/api/voc/sources", response_model=List[VocSourceInfo])
def get_voc_sources(
    client_uuid: Optional[UUID] = None,
    project_name: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    List available data sources in process_voc.
    
    Query parameters:
    - client_uuid: Filter by client UUID (will match by UUID or by client name if UUID is null)
    - project_name: Filter by project name
    """
    from sqlalchemy import func
    
    query = db.query(
        ProcessVoc.data_source,
        ProcessVoc.client_uuid,
        func.max(ProcessVoc.client_name).label('client_name'),
        func.count(ProcessVoc.id).label('response_count')
    )
    
    if client_uuid:
        # Get client name for matching
        client = db.query(Client).filter(Client.id == client_uuid).first()
        if client:
            # Filter by client_uuid OR by client_name (for rows where client_uuid is null)
            query = query.filter(
                or_(
                    ProcessVoc.client_uuid == client_uuid,
                    ProcessVoc.client_name == client.name
                )
            )
        else:
            query = query.filter(ProcessVoc.client_uuid == client_uuid)
    
    if project_name:
        query = query.filter(ProcessVoc.project_name == project_name)
    
    query = query.group_by(
        ProcessVoc.data_source,
        ProcessVoc.client_uuid
    )
    
    results = query.all()
    
    return [
        VocSourceInfo(
            data_source=row.data_source,
            client_uuid=row.client_uuid or client_uuid,  # Use provided UUID if row has null
            client_name=row.client_name,
            response_count=row.response_count
        )
        for row in results
        if row.data_source is not None
    ]


@app.get("/api/voc/projects", response_model=List[VocProjectInfo])
def get_voc_projects(
    client_uuid: Optional[UUID] = None,
    db: Session = Depends(get_db)
):
    """
    List available projects in process_voc for a client.
    
    Query parameters:
    - client_uuid: Filter by client UUID (will match by UUID or by client name if UUID is null)
    """
    from sqlalchemy import func
    
    query = db.query(
        ProcessVoc.project_name,
        func.max(ProcessVoc.project_id).label('project_id'),
        func.count(ProcessVoc.id).label('response_count')
    )
    
    if client_uuid:
        # Get client name for matching
        client = db.query(Client).filter(Client.id == client_uuid).first()
        if client:
            # Filter by client_uuid OR by client_name (for rows where client_uuid is null)
            query = query.filter(
                or_(
                    ProcessVoc.client_uuid == client_uuid,
                    ProcessVoc.client_name == client.name
                )
            )
        else:
            query = query.filter(ProcessVoc.client_uuid == client_uuid)
    
    # Filter out null project names
    query = query.filter(ProcessVoc.project_name.isnot(None))
    
    query = query.group_by(
        ProcessVoc.project_name
    )
    
    results = query.all()
    
    return [
        VocProjectInfo(
            project_name=row.project_name,
            project_id=row.project_id,
            response_count=row.response_count
        )
        for row in results
        if row.project_name is not None
    ]


@app.get("/api/voc/clients", response_model=List[VocClientInfo])
def get_voc_clients(
    db: Session = Depends(get_db)
):
    """
    List clients that have data in process_voc.
    Returns distinct clients with data source counts.
    Handles both cases: client_uuid set, or client_name only (tries to match to clients table).
    """
    from sqlalchemy import func, distinct, case
    
    # First, try to get clients grouped by client_uuid (when not null)
    query_with_uuid = db.query(
        ProcessVoc.client_uuid,
        func.max(ProcessVoc.client_name).label('client_name'),
        func.count(func.distinct(ProcessVoc.data_source)).label('data_source_count')
    ).filter(
        ProcessVoc.client_uuid.isnot(None)
    ).group_by(
        ProcessVoc.client_uuid
    )
    
    results_with_uuid = query_with_uuid.all()
    
    # Build a map of client_uuid -> info
    client_map = {}
    for row in results_with_uuid:
        client_map[row.client_uuid] = {
            'client_uuid': row.client_uuid,
            'client_name': row.client_name,
            'data_source_count': row.data_source_count
        }
    
    # Now get clients grouped by client_name (when client_uuid is null)
    # and try to match them to existing clients in the clients table
    query_by_name = db.query(
        ProcessVoc.client_name,
        func.count(func.distinct(ProcessVoc.data_source)).label('data_source_count')
    ).filter(
        ProcessVoc.client_uuid.is_(None),
        ProcessVoc.client_name.isnot(None)
    ).group_by(
        ProcessVoc.client_name
    )
    
    results_by_name = query_by_name.all()
    
    # For each client_name, try to find matching client in clients table
    for row in results_by_name:
        if row.client_name:
            # Try to find a client with matching name
            matching_client = db.query(Client).filter(Client.name == row.client_name).first()
            
            if matching_client:
                # Use the existing client UUID
                if matching_client.id not in client_map:
                    client_map[matching_client.id] = {
                        'client_uuid': matching_client.id,
                        'client_name': matching_client.name,
                        'data_source_count': row.data_source_count
                    }
                else:
                    # Merge data source counts if client already exists
                    client_map[matching_client.id]['data_source_count'] += row.data_source_count
            else:
                # No matching client found - we'll need to create a temporary UUID
                # For now, we'll skip these or create them on-the-fly
                # For the frontend, we can use client_name as identifier
                pass
    
    # Convert to list and return
    return [
        VocClientInfo(
            client_uuid=info['client_uuid'],
            client_name=info['client_name'],
            data_source_count=info['data_source_count']
        )
        for info in client_map.values()
    ]


# Founder Admin Endpoints

@app.get("/api/founder-admin/voc-data", response_model=ProcessVocAdminListResponse)
def get_founder_admin_voc_data(
    filter_project_id: Optional[str] = None,
    filter_project_name: Optional[str] = None,
    filter_dimension_ref: Optional[str] = None,
    filter_dimension_name: Optional[str] = None,
    filter_client_name: Optional[str] = None,
    # Legacy parameter names for backward compatibility
    project_id: Optional[str] = None,
    project_name: Optional[str] = None,
    dimension_ref: Optional[str] = None,
    client_name: Optional[str] = None,
    page: int = 1,
    page_size: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder)
):
    """
    Get all process_voc rows with optional filtering.
    Requires founder authentication.
    Returns paginated results.
    
    Supports both filter_* parameter names and legacy names.
    """
    # Build query
    query = db.query(ProcessVoc)
    
    # Support both new and legacy parameter names
    filter_pid = filter_project_id or project_id
    filter_pname = filter_project_name or project_name
    filter_dref = filter_dimension_ref or dimension_ref
    filter_dname = filter_dimension_name
    filter_cname = filter_client_name or client_name
    
    # Apply filters (case-insensitive partial matching)
    if filter_pid:
        query = query.filter(ProcessVoc.project_id.ilike(f"%{filter_pid}%"))
    if filter_pname:
        query = query.filter(ProcessVoc.project_name.ilike(f"%{filter_pname}%"))
    if filter_dref:
        query = query.filter(ProcessVoc.dimension_ref.ilike(f"%{filter_dref}%"))
    if filter_dname:
        query = query.filter(ProcessVoc.dimension_name.ilike(f"%{filter_dname}%"))
    if filter_cname:
        query = query.filter(ProcessVoc.client_name.ilike(f"%{filter_cname}%"))
    
    # Get total count
    total = query.count()
    
    # Calculate pagination
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    offset = (page - 1) * page_size
    
    # Get paginated results
    items = query.order_by(ProcessVoc.id).offset(offset).limit(page_size).all()
    
    return ProcessVocAdminListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@app.post("/api/founder-admin/voc-data/bulk-update", response_model=ProcessVocBulkUpdateResponse)
def bulk_update_voc_data(
    update_request: ProcessVocBulkUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder)
):
    """
    Bulk update project_name and/or dimension_name for multiple process_voc rows.
    Requires founder authentication.
    """
    updated_count = 0
    
    for update_item in update_request.updates:
        # Find the row by ID
        row = db.query(ProcessVoc).filter(ProcessVoc.id == update_item.id).first()
        
        if not row:
            continue  # Skip if row not found
        
        # Update fields if provided
        if update_item.project_name is not None:
            row.project_name = update_item.project_name
        if update_item.dimension_name is not None:
            row.dimension_name = update_item.dimension_name
        if update_item.data_source is not None:
            row.data_source = update_item.data_source
        if update_item.client_name is not None:
            row.client_name = update_item.client_name
        
        updated_count += 1
    
    # Commit all changes
    db.commit()
    
    return ProcessVocBulkUpdateResponse(
        updated_count=updated_count,
        message=f"Successfully updated {updated_count} row(s)"
    )


@app.get("/api/founder-admin/field-metadata", response_model=FieldMetadataResponse)
def get_field_metadata(
    current_user: User = Depends(get_current_active_founder)
):
    """
    Get metadata about all editable fields in process_voc table.
    Requires founder authentication.
    """
    fields = [
        # Client fields
        FieldMetadata(name="client_name", type="string", nullable=True, category="client", editable=True),
        FieldMetadata(name="client_id", type="string", nullable=True, category="client", editable=True),
        # Project fields
        FieldMetadata(name="project_name", type="string", nullable=True, category="project", editable=True),
        FieldMetadata(name="project_id", type="string", nullable=True, category="project", editable=True),
        # Dimension fields
        FieldMetadata(name="dimension_name", type="text", nullable=True, category="dimension", editable=True),
        FieldMetadata(name="dimension_ref", type="string", nullable=False, category="dimension", editable=True),
        # Response fields
        FieldMetadata(name="data_source", type="string", nullable=True, category="response", editable=True),
        FieldMetadata(name="value", type="text", nullable=True, category="response", editable=True),
        FieldMetadata(name="overall_sentiment", type="string", nullable=True, category="response", editable=True),
        FieldMetadata(name="response_type", type="string", nullable=True, category="response", editable=True),
        FieldMetadata(name="user_type", type="string", nullable=True, category="response", editable=True),
        # Metadata fields
        FieldMetadata(name="region", type="string", nullable=True, category="metadata", editable=True),
        FieldMetadata(name="total_rows", type="integer", nullable=True, category="metadata", editable=True),
        FieldMetadata(name="respondent_id", type="string", nullable=False, category="metadata", editable=True),
        # Timestamp fields
        FieldMetadata(name="created", type="datetime", nullable=True, category="timestamp", editable=True),
        FieldMetadata(name="last_modified", type="datetime", nullable=True, category="timestamp", editable=True),
        FieldMetadata(name="start_date", type="datetime", nullable=True, category="timestamp", editable=True),
        FieldMetadata(name="submit_date", type="datetime", nullable=True, category="timestamp", editable=True),
        # Complex fields
        FieldMetadata(name="topics", type="json", nullable=True, category="response", editable=True),
    ]
    
    return FieldMetadataResponse(fields=fields)


@app.post("/api/founder-admin/voc-data/bulk-update-filtered", response_model=ProcessVocBulkUpdateResponse)
def bulk_update_filtered_voc_data(
    filter_project_id: Optional[str] = None,
    filter_project_name: Optional[str] = None,
    filter_dimension_ref: Optional[str] = None,
    filter_dimension_name: Optional[str] = None,
    filter_client_name: Optional[str] = None,
    update_request: Optional[DynamicBulkUpdateRequest] = None,
    # Legacy parameters for backward compatibility
    project_name: Optional[str] = None,
    dimension_name: Optional[str] = None,
    data_source: Optional[str] = None,
    client_name: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder)
):
    """
    Bulk update any fields for all rows matching filter criteria.
    Requires founder authentication.
    At least one filter must be provided.
    
    Supports two modes:
    1. Legacy: Use individual parameters (project_name, dimension_name, etc.)
    2. New: Use update_request with dynamic field map
    """
    # Require at least one filter to prevent accidental updates to all rows
    if not filter_project_id and not filter_project_name and not filter_dimension_ref and not filter_dimension_name and not filter_client_name:
        raise HTTPException(
            status_code=400,
            detail="At least one filter must be provided"
        )
    
    # Build update map - support both legacy and new format
    updates = {}
    if update_request:
        updates = update_request.updates
    else:
        # Legacy mode
        if project_name is not None:
            updates["project_name"] = project_name
        if dimension_name is not None:
            updates["dimension_name"] = dimension_name
        if data_source is not None:
            updates["data_source"] = data_source
        if client_name is not None:
            updates["client_name"] = client_name
    
    # Remove None values (fields to skip)
    updates = {k: v for k, v in updates.items() if v is not None}
    
    if not updates:
        raise HTTPException(
            status_code=400,
            detail="At least one field to update must be provided"
        )
    
    # Build query with filters (case-insensitive partial matching)
    query = db.query(ProcessVoc)
    
    if filter_project_id:
        query = query.filter(ProcessVoc.project_id.ilike(f"%{filter_project_id}%"))
    if filter_project_name:
        query = query.filter(ProcessVoc.project_name.ilike(f"%{filter_project_name}%"))
    if filter_dimension_ref:
        query = query.filter(ProcessVoc.dimension_ref.ilike(f"%{filter_dimension_ref}%"))
    if filter_dimension_name:
        query = query.filter(ProcessVoc.dimension_name.ilike(f"%{filter_dimension_name}%"))
    if filter_client_name:
        query = query.filter(ProcessVoc.client_name.ilike(f"%{filter_client_name}%"))
    
    # Get all matching rows
    rows = query.all()
    updated_count = 0
    
    # Define which fields are editable (exclude auto fields and relationships)
    editable_fields = {
        'client_name', 'client_id', 'project_name', 'project_id',
        'dimension_name', 'dimension_ref', 'data_source', 'value',
        'overall_sentiment', 'response_type', 'user_type', 'region',
        'total_rows', 'respondent_id', 'created', 'last_modified',
        'start_date', 'submit_date', 'topics'
    }
    
    for row in rows:
        updated = False
        for field_name, new_value in updates.items():
            if field_name not in editable_fields:
                continue  # Skip non-editable fields
            
            if hasattr(row, field_name):
                # Handle different field types
                if field_name == 'topics' and new_value:
                    # Parse JSON for topics
                    try:
                        import json
                        row.topics = json.loads(new_value) if isinstance(new_value, str) else new_value
                    except:
                        continue  # Skip invalid JSON
                elif field_name == 'total_rows' and new_value:
                    # Parse integer
                    try:
                        row.total_rows = int(new_value)
                    except:
                        continue
                elif field_name in ['created', 'last_modified', 'start_date', 'submit_date'] and new_value:
                    # Parse datetime
                    try:
                        from datetime import datetime
                        row.__setattr__(field_name, datetime.fromisoformat(new_value.replace('Z', '+00:00')))
                    except:
                        continue
                else:
                    # String/text fields
                    row.__setattr__(field_name, new_value)
                updated = True
        
        if updated:
            updated_count += 1
    
    # Commit all changes
    db.commit()
    
    return ProcessVocBulkUpdateResponse(
        updated_count=updated_count,
        message=f"Successfully updated {updated_count} row(s) matching filters"
    )


@app.delete("/api/founder-admin/voc-data/bulk-delete", response_model=ProcessVocBulkUpdateResponse)
def bulk_delete_voc_data(
    filter_project_id: Optional[str] = None,
    filter_project_name: Optional[str] = None,
    filter_dimension_ref: Optional[str] = None,
    filter_dimension_name: Optional[str] = None,
    filter_client_name: Optional[str] = None,
    # Legacy parameters
    project_id: Optional[str] = None,
    dimension_ref: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder)
):
    """
    Bulk delete all rows matching filter criteria.
    Requires founder authentication.
    At least one filter must be provided.
    """
    # Support both new and legacy parameter names
    filter_pid = filter_project_id or project_id
    filter_pname = filter_project_name
    filter_dref = filter_dimension_ref or dimension_ref
    filter_dname = filter_dimension_name
    filter_cname = filter_client_name
    
    # Require at least one filter to prevent accidental deletion of all rows
    if not filter_pid and not filter_pname and not filter_dref and not filter_dname and not filter_cname:
        raise HTTPException(
            status_code=400,
            detail="At least one filter must be provided"
        )
    
    # Build query with filters (case-insensitive partial matching)
    query = db.query(ProcessVoc)
    
    if filter_pid:
        query = query.filter(ProcessVoc.project_id.ilike(f"%{filter_pid}%"))
    if filter_pname:
        query = query.filter(ProcessVoc.project_name.ilike(f"%{filter_pname}%"))
    if filter_dref:
        query = query.filter(ProcessVoc.dimension_ref.ilike(f"%{filter_dref}%"))
    if filter_dname:
        query = query.filter(ProcessVoc.dimension_name.ilike(f"%{filter_dname}%"))
    if filter_cname:
        query = query.filter(ProcessVoc.client_name.ilike(f"%{filter_cname}%"))
    
    # Get all matching rows
    rows = query.all()
    deleted_count = len(rows)
    
    # Delete all matching rows
    for row in rows:
        db.delete(row)
    
    # Commit all changes
    db.commit()
    
    return ProcessVocBulkUpdateResponse(
        updated_count=deleted_count,
        message=f"Successfully deleted {deleted_count} row(s) matching filters"
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

