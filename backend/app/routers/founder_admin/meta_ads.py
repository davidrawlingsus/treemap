"""
Meta Ads management routes for OAuth and Marketing API.
Access: any authenticated user with access to the client (membership or founder).
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, StreamingResponse
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional
from datetime import datetime, timezone
import json
import logging
import os
import random
import secrets
import string
import time
import base64
import hashlib
import hmac

import httpx
from app.database import get_db
from app.models import User, Client, MetaOAuthToken, AdImage, AdImagePerformance
from app.schemas import (
    MetaOAuthInitResponse,
    MetaTokenStatusResponse,
    SetDefaultAdAccountRequest,
    MetaAdAccount,
    MetaAdAccountListResponse,
    MetaCampaign,
    MetaCampaignListResponse,
    CreateCampaignRequest,
    CreateCampaignResponse,
    MetaAdSet,
    MetaAdSetListResponse,
    CreateAdSetRequest,
    CreateAdSetResponse,
    PublishAdRequest,
    PublishAdResponse,
    MetaMediaLibraryResponse,
    MetaMediaLibraryItem,
    MetaMediaLibraryPaging,
    MetaMediaLibraryCountsResponse,
    MetaMediaImportRequest,
    MetaMediaImportResponse,
    MetaMediaImportItem,
    MetaImportAllRequest,
)
from app.schemas.ad_image import AdImageResponse
from app.auth import get_current_user
from app.authorization import verify_client_access
from app.config import get_settings
from app.routers.founder_admin.ad_images import _is_untitled_thumbnail
from app.services.meta_ads_service import MetaAdsService

logger = logging.getLogger(__name__)

router = APIRouter()


def _parse_meta_created_time(s: Optional[str]) -> Optional[datetime]:
    """Parse Meta API created_time (ISO string) to timezone-aware datetime."""
    if not s:
        return None
    try:
        n = s.strip().replace("Z", "+00:00")
        if len(n) >= 5 and (n[-5] == "+" or n[-5] == "-") and ":" not in n[-3:]:
            n = n[:-2] + ":" + n[-2:]
        return datetime.fromisoformat(n)
    except Exception:
        return None

# In-memory state storage for OAuth (in production, use Redis or DB)
_oauth_states = {}


# ==================== OAuth Endpoints ====================

@router.get("/api/meta/oauth/init")
def meta_oauth_init(
    request: Request,
    client_id: UUID = Query(..., description="Client ID to connect Meta account to"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MetaOAuthInitResponse:
    """
    Initialize Meta OAuth flow.
    Returns the OAuth URL for the frontend to open in a popup.
    """
    settings = get_settings()
    verify_client_access(client_id, current_user, db)
    
    if not settings.meta_app_id or not settings.meta_app_secret:
        raise HTTPException(
            status_code=500,
            detail="Meta OAuth not configured. Set META_APP_ID and META_APP_SECRET."
        )
    
    # Generate state token for CSRF protection
    state = secrets.token_urlsafe(32)
    # Build redirect URI: use explicit setting, or derive from the incoming request
    # so the callback hits this same backend server directly (not via a frontend proxy).
    redirect_uri = settings.meta_redirect_uri
    if not redirect_uri:
        scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
        host = request.headers.get("host", "localhost:8000")
        redirect_uri = f"{scheme}://{host}/api/meta/oauth/callback"
    
    _oauth_states[state] = {
        "client_id": str(client_id),
        "user_id": str(current_user.id),
        "redirect_uri": redirect_uri,
    }
    
    service = MetaAdsService(db)
    oauth_url = service.get_oauth_url(
        client_id=str(client_id),
        redirect_uri=redirect_uri,
        state=state,
    )
    
    return MetaOAuthInitResponse(oauth_url=oauth_url, state=state)


@router.get("/api/meta/oauth/callback")
async def meta_oauth_callback(
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    error_description: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Handle Meta OAuth callback.
    Exchanges code for token and stores it.
    Returns HTML that closes the popup and notifies the parent window.
    """
    # Handle error responses from Meta
    if error:
        error_msg = error_description or error
        return HTMLResponse(
            content=f"""
            <html>
            <body>
                <script>
                    window.opener?.postMessage({{type: 'meta_oauth_error', error: '{error_msg}'}}, '*');
                    window.close();
                </script>
                <p>Authentication failed: {error_msg}. You can close this window.</p>
            </body>
            </html>
            """,
            status_code=400,
        )
    
    # Check for missing required parameters
    if not code or not state:
        return HTMLResponse(
            content="""
            <html>
            <body>
                <script>
                    window.opener?.postMessage({type: 'meta_oauth_error', error: 'Missing authorization code'}, '*');
                    window.close();
                </script>
                <p>Authentication failed: Missing authorization code. You can close this window.</p>
            </body>
            </html>
            """,
            status_code=400,
        )
    
    settings = get_settings()
    
    # Verify state
    state_data = _oauth_states.pop(state, None)
    if not state_data:
        return HTMLResponse(
            content="""
            <html>
            <body>
                <script>
                    window.opener?.postMessage({type: 'meta_oauth_error', error: 'Invalid state'}, '*');
                    window.close();
                </script>
                <p>Authentication failed: Invalid state. You can close this window.</p>
            </body>
            </html>
            """,
            status_code=400,
        )
    
    client_id = state_data["client_id"]
    user_id = state_data["user_id"]
    
    # Use the same redirect URI that was used in init (stored in state)
    redirect_uri = state_data.get("redirect_uri")
    if not redirect_uri:
        redirect_uri = settings.meta_redirect_uri or f"{settings.frontend_base_url}/api/meta/oauth/callback"
    
    service = MetaAdsService(db)
    
    try:
        # Exchange code for short-lived token
        token_response = await service.exchange_code_for_token(code, redirect_uri)
        short_lived_token = token_response.get("access_token")
        
        if not short_lived_token:
            raise ValueError("No access token in response")
        
        # Exchange for long-lived token
        long_lived_response = await service.exchange_for_long_lived_token(short_lived_token)
        access_token = long_lived_response.get("access_token")
        expires_in = long_lived_response.get("expires_in")
        
        # Get user info
        user_info = await service.get_meta_user_info(access_token)
        meta_user_id = user_info.get("id")
        meta_user_name = user_info.get("name")
        
        # Save token for this (user, client)
        service.save_token(
            client_id=client_id,
            user_id=user_id,
            access_token=access_token,
            expires_in=expires_in,
            meta_user_id=meta_user_id,
            meta_user_name=meta_user_name,
        )
        
        logger.info(f"Meta OAuth completed for client {client_id}, user {meta_user_name}")
        
        # Return HTML that closes popup and notifies parent
        return HTMLResponse(
            content=f"""
            <html>
            <body>
                <script>
                    window.opener?.postMessage({{
                        type: 'meta_oauth_success',
                        meta_user_name: '{meta_user_name}'
                    }}, '*');
                    window.close();
                </script>
                <p>Authentication successful! You can close this window.</p>
            </body>
            </html>
            """
        )
        
    except Exception as e:
        logger.error(f"Meta OAuth error: {e}")
        # Escape error message for JavaScript
        safe_error = str(e).replace("'", "\\'").replace('"', '\\"').replace('\n', ' ')
        return HTMLResponse(
            content=f"""
            <html>
            <body>
                <script>
                    window.opener?.postMessage({{
                        type: 'meta_oauth_error',
                        error: '{safe_error}'
                    }}, '*');
                    window.close();
                </script>
                <p>Authentication failed: {safe_error}. You can close this window.</p>
            </body>
            </html>
            """,
            status_code=400,
        )


@router.post("/api/meta/deauthorize")
async def meta_deauthorize_callback(
    request: Request,
    signed_request: str = Form(...),
    db: Session = Depends(get_db),
):
    """
    Handle Meta deauthorization callback.
    
    Meta calls this endpoint when a user removes your app from their Facebook settings.
    The signed_request contains the user_id of the user who deauthorized.
    
    Configure this URL in Meta Developer Console:
    Settings > Basic > Deauthorize Callback URL
    """
    settings = get_settings()
    
    if not settings.meta_app_secret:
        logger.error("META_APP_SECRET not configured for deauthorization callback")
        return JSONResponse(
            status_code=200,
            content={"success": False, "error": "Not configured"}
        )
    
    try:
        # Parse the signed request
        # Format: encoded_signature.payload
        parts = signed_request.split('.')
        if len(parts) != 2:
            raise ValueError("Invalid signed_request format")
        
        encoded_sig, payload = parts
        
        # Decode the signature
        # Meta uses URL-safe base64 encoding without padding
        sig = base64.urlsafe_b64decode(encoded_sig + '==')
        
        # Decode the payload
        data = json.loads(base64.urlsafe_b64decode(payload + '==').decode('utf-8'))
        
        # Verify the signature
        expected_sig = hmac.new(
            settings.meta_app_secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).digest()
        
        if not hmac.compare_digest(sig, expected_sig):
            logger.warning("Meta deauthorize callback: Invalid signature")
            return JSONResponse(
                status_code=200,
                content={"success": False, "error": "Invalid signature"}
            )
        
        # Get the Meta user ID from the payload
        meta_user_id = data.get('user_id')
        
        if meta_user_id:
            # Find and delete all tokens for this Meta user
            tokens = db.query(MetaOAuthToken).filter(
                MetaOAuthToken.meta_user_id == str(meta_user_id)
            ).all()
            
            for token in tokens:
                logger.info(f"Deauthorizing Meta token for client {token.client_id}, Meta user {meta_user_id}")
                db.delete(token)
            
            db.commit()
            
            logger.info(f"Meta deauthorization completed for user {meta_user_id}, removed {len(tokens)} tokens")
        
        # Meta expects a 200 response
        return JSONResponse(
            status_code=200,
            content={"success": True}
        )
        
    except Exception as e:
        logger.error(f"Meta deauthorize callback error: {e}")
        # Still return 200 to acknowledge receipt
        return JSONResponse(
            status_code=200,
            content={"success": False, "error": str(e)}
        )


@router.post("/api/meta/data-deletion")
async def meta_data_deletion_callback(
    request: Request,
    signed_request: str = Form(...),
    db: Session = Depends(get_db),
):
    """
    Handle Meta data deletion callback.
    
    Meta calls this endpoint when a user requests deletion of their data.
    This is required for GDPR/CCPA compliance.
    
    Configure this URL in Meta Developer Console:
    Settings > Basic > Data Deletion Request URL
    """
    settings = get_settings()
    
    if not settings.meta_app_secret:
        logger.error("META_APP_SECRET not configured for data deletion callback")
        return JSONResponse(
            status_code=200,
            content={"url": "", "confirmation_code": ""}
        )
    
    try:
        # Parse the signed request (same as deauthorize)
        parts = signed_request.split('.')
        if len(parts) != 2:
            raise ValueError("Invalid signed_request format")
        
        encoded_sig, payload = parts
        sig = base64.urlsafe_b64decode(encoded_sig + '==')
        data = json.loads(base64.urlsafe_b64decode(payload + '==').decode('utf-8'))
        
        # Verify the signature
        expected_sig = hmac.new(
            settings.meta_app_secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).digest()
        
        if not hmac.compare_digest(sig, expected_sig):
            logger.warning("Meta data deletion callback: Invalid signature")
            return JSONResponse(
                status_code=200,
                content={"url": "", "confirmation_code": "invalid_signature"}
            )
        
        meta_user_id = data.get('user_id')
        
        if meta_user_id:
            # Delete all tokens for this Meta user
            tokens = db.query(MetaOAuthToken).filter(
                MetaOAuthToken.meta_user_id == str(meta_user_id)
            ).all()
            
            for token in tokens:
                logger.info(f"Data deletion: Removing Meta token for client {token.client_id}")
                db.delete(token)
            
            db.commit()
            
            logger.info(f"Meta data deletion completed for user {meta_user_id}, removed {len(tokens)} tokens")
        
        # Generate a confirmation code
        confirmation_code = secrets.token_hex(16)
        
        # Meta expects a JSON response with a status URL and confirmation code
        # The URL should show the deletion status (can be a simple page)
        status_url = f"{settings.frontend_base_url}/meta-deletion-status?code={confirmation_code}"
        
        return JSONResponse(
            status_code=200,
            content={
                "url": status_url,
                "confirmation_code": confirmation_code
            }
        )
        
    except Exception as e:
        logger.error(f"Meta data deletion callback error: {e}")
        return JSONResponse(
            status_code=200,
            content={"url": "", "confirmation_code": f"error_{secrets.token_hex(8)}"}
        )


@router.get("/api/meta/token-status")
def get_meta_token_status(
    client_id: UUID = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MetaTokenStatusResponse:
    """Check if a client has a valid Meta token."""
    verify_client_access(client_id, current_user, db)
    service = MetaAdsService(db)
    token = service.get_token(str(client_id), str(current_user.id))
    
    if not token:
        return MetaTokenStatusResponse(has_token=False, is_expired=False)
    
    return MetaTokenStatusResponse(
        has_token=True,
        is_expired=token.is_expired(),
        meta_user_name=token.meta_user_name,
        default_ad_account_id=token.default_ad_account_id,
        default_ad_account_name=token.default_ad_account_name,
        expires_at=token.expires_at,
    )


@router.delete("/api/meta/disconnect")
def disconnect_meta(
    client_id: UUID = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Disconnect Meta account from a client (delete this user's token)."""
    verify_client_access(client_id, current_user, db)
    token = db.query(MetaOAuthToken).filter(
        MetaOAuthToken.client_id == client_id,
        MetaOAuthToken.user_id == current_user.id,
    ).first()
    
    if token:
        db.delete(token)
        db.commit()
        logger.info(f"Disconnected Meta account from client {client_id}")
    
    return {"success": True}


# ==================== Ad Account Endpoints ====================

@router.get("/api/meta/ad-accounts")
async def list_ad_accounts(
    client_id: UUID = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MetaAdAccountListResponse:
    """List Meta ad accounts for a client."""
    verify_client_access(client_id, current_user, db)
    service = MetaAdsService(db)
    token = service.get_token(str(client_id), str(current_user.id))
    if not token:
        raise HTTPException(status_code=400, detail="No Meta token for this client")
    if token.is_expired():
        raise HTTPException(status_code=401, detail="Meta token expired, please reconnect")
    accounts = await service.list_ad_accounts(token.access_token)
    
    items = [
        MetaAdAccount(
            id=acc["id"],
            name=acc.get("name", ""),
            account_status=acc.get("account_status", 0),
            currency=acc.get("currency"),
            timezone_name=acc.get("timezone_name"),
        )
        for acc in accounts
    ]
    
    return MetaAdAccountListResponse(items=items, total=len(items))


@router.post("/api/meta/set-default-ad-account")
def set_default_ad_account(
    request: SetDefaultAdAccountRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Set the default ad account for a client."""
    verify_client_access(request.client_id, current_user, db)
    service = MetaAdsService(db)
    try:
        service.set_default_ad_account(
            client_id=str(request.client_id),
            user_id=str(current_user.id),
            ad_account_id=request.ad_account_id,
            ad_account_name=request.ad_account_name,
        )
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== Campaign Endpoints ====================

@router.get("/api/meta/campaigns")
async def list_campaigns(
    ad_account_id: str = Query(...),
    client_id: UUID = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MetaCampaignListResponse:
    """List campaigns for an ad account."""
    verify_client_access(client_id, current_user, db)
    service = MetaAdsService(db)
    token = service.get_token(str(client_id), str(current_user.id))
    
    if not token:
        raise HTTPException(status_code=400, detail="No Meta token for this client")
    if token.is_expired():
        raise HTTPException(status_code=401, detail="Meta token expired, please reconnect")

    try:
        campaigns = await service.list_campaigns(token.access_token, ad_account_id)
    except httpx.HTTPStatusError as e:
        msg = str(e)
        try:
            err_body = e.response.json()
            msg = err_body.get("error", {}).get("message", e.response.text) or msg
        except Exception:
            if e.response is not None:
                msg = e.response.text or msg
        logger.warning("Meta list_campaigns failed: %s", msg)
        raise HTTPException(status_code=502, detail=f"Meta API: {msg}")
    except Exception as e:
        logger.exception("Meta list_campaigns error")
        raise HTTPException(status_code=502, detail=str(e))

    items = [
        MetaCampaign(
            id=c.get("id", ""),
            name=c.get("name", ""),
            status=c.get("status", "UNKNOWN"),
            objective=c.get("objective"),
            created_time=c.get("created_time"),
        )
        for c in (campaigns or [])
    ]
    return MetaCampaignListResponse(items=items, total=len(items))


@router.post("/api/meta/campaigns")
async def create_campaign(
    request: CreateCampaignRequest,
    client_id: UUID = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CreateCampaignResponse:
    """Create a new campaign."""
    verify_client_access(client_id, current_user, db)
    service = MetaAdsService(db)
    token = service.get_token(str(client_id), str(current_user.id))
    
    if not token:
        raise HTTPException(status_code=400, detail="No Meta token for this client")
    
    try:
        result = await service.create_campaign(
            access_token=token.access_token,
            ad_account_id=request.ad_account_id,
            name=request.name,
            objective=request.objective,
            status=request.status,
            special_ad_categories=request.special_ad_categories,
        )
        return CreateCampaignResponse(id=result["id"], name=request.name)
    except Exception as e:
        logger.error(f"Failed to create campaign: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ==================== AdSet Endpoints ====================

@router.get("/api/meta/adsets")
async def list_adsets(
    campaign_id: str = Query(...),
    client_id: UUID = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MetaAdSetListResponse:
    """List adsets for a campaign."""
    verify_client_access(client_id, current_user, db)
    service = MetaAdsService(db)
    token = service.get_token(str(client_id), str(current_user.id))
    
    if not token:
        raise HTTPException(status_code=400, detail="No Meta token for this client")
    
    adsets = await service.list_adsets(token.access_token, campaign_id)
    
    items = [
        MetaAdSet(
            id=a["id"],
            name=a.get("name", ""),
            status=a.get("status", "UNKNOWN"),
            campaign_id=campaign_id,
            daily_budget=a.get("daily_budget"),
            lifetime_budget=a.get("lifetime_budget"),
        )
        for a in adsets
    ]
    
    return MetaAdSetListResponse(items=items, total=len(items))


@router.post("/api/meta/adsets")
async def create_adset(
    request: CreateAdSetRequest,
    client_id: UUID = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CreateAdSetResponse:
    """Create a new adset."""
    verify_client_access(client_id, current_user, db)
    service = MetaAdsService(db)
    token = service.get_token(str(client_id), str(current_user.id))
    
    if not token:
        raise HTTPException(status_code=400, detail="No Meta token for this client")
    
    # Get ad account from token's default or require it in request
    ad_account_id = token.default_ad_account_id
    if not ad_account_id:
        raise HTTPException(
            status_code=400,
            detail="No default ad account set. Please select an ad account first."
        )
    
    try:
        result = await service.create_adset(
            access_token=token.access_token,
            ad_account_id=ad_account_id,
            campaign_id=request.campaign_id,
            name=request.name,
            daily_budget=request.daily_budget,
            lifetime_budget=request.lifetime_budget,
            billing_event=request.billing_event,
            optimization_goal=request.optimization_goal,
            status=request.status,
            targeting=request.targeting,
            promoted_object=request.promoted_object,
        )
        return CreateAdSetResponse(id=result["id"], name=request.name)
    except Exception as e:
        logger.error(f"Failed to create adset: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ==================== Pixel Endpoints ====================

@router.get("/api/meta/pixels")
async def list_pixels(
    client_id: UUID = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List Facebook pixels for the client's ad account."""
    verify_client_access(client_id, current_user, db)
    service = MetaAdsService(db)
    token = service.get_token(str(client_id), str(current_user.id))
    
    if not token:
        raise HTTPException(status_code=400, detail="No Meta token for this client")
    
    ad_account_id = token.default_ad_account_id
    if not ad_account_id:
        raise HTTPException(status_code=400, detail="No default ad account set")
    
    pixels = await service.list_pixels(token.access_token, ad_account_id)
    return {"items": pixels, "total": len(pixels)}


# ==================== Ad Publishing Endpoints ====================

@router.get("/api/meta/pages")
async def list_pages(
    client_id: UUID = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List Facebook pages the user manages."""
    verify_client_access(client_id, current_user, db)
    service = MetaAdsService(db)
    token = service.get_token(str(client_id), str(current_user.id))
    
    if not token:
        raise HTTPException(status_code=400, detail="No Meta token for this client")
    
    pages = await service.list_pages(token.access_token)
    return {"items": pages, "total": len(pages)}


# ==================== Media Library (FB Connector) Endpoints ====================

@router.get("/api/meta/media-library/counts", response_model=MetaMediaLibraryCountsResponse)
async def get_meta_media_library_counts(
    client_id: UUID = Query(...),
    media_type: str = Query("all", description="all, image, or video"),
    ad_account_id: Optional[str] = Query(None, description="Ad account to use; if omitted, token default is used"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MetaMediaLibraryCountsResponse:
    """Return total counts for the ad account media library (for progress). Poll before Load All."""
    verify_client_access(client_id, current_user, db)
    service = MetaAdsService(db)
    token = service.get_token(str(client_id), str(current_user.id))
    if not token:
        raise HTTPException(status_code=400, detail="No Meta token for this client")
    if token.is_expired():
        raise HTTPException(status_code=401, detail="Meta token expired, please reconnect")
    ad_account_id = ad_account_id or token.default_ad_account_id
    if not ad_account_id:
        raise HTTPException(
            status_code=400,
            detail="No default ad account set. Please select an ad account first.",
        )
    try:
        image_count = None
        video_count = None
        if media_type in ("all", "image"):
            image_count = await service.get_ad_images_total_count(
                token.access_token, ad_account_id
            )
        if media_type in ("all", "video"):
            video_count = await service.get_ad_videos_total_count(
                token.access_token, ad_account_id
            )
        return MetaMediaLibraryCountsResponse(
            image_count=image_count,
            video_count=video_count,
        )
    except httpx.HTTPStatusError as e:
        msg = str(e)
        try:
            err_body = e.response.json()
            msg = err_body.get("error", {}).get("message", e.response.text) or msg
        except Exception:
            msg = e.response.text or msg
        logger.warning("Meta media library counts API failed: %s", msg)
        raise HTTPException(status_code=502, detail=f"Meta API: {msg}")
    except Exception as e:
        logger.exception("Meta media library counts failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/meta/media-library", response_model=MetaMediaLibraryResponse)
async def get_meta_media_library(
    client_id: UUID = Query(...),
    media_type: str = Query("all", description="all, image, or video"),
    limit: int = Query(50, ge=1, le=100),
    after: Optional[str] = Query(None, description="Cursor for single-type pagination"),
    image_after: Optional[str] = Query(None, description="Cursor for next images (media_type=all)"),
    video_after: Optional[str] = Query(None, description="Cursor for next videos (media_type=all)"),
    ad_account_id: Optional[str] = Query(None, description="Ad account to use; if omitted, token default is used"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MetaMediaLibraryResponse:
    """List images and/or videos from the client's Meta ad account media library. Paginate with 'after' for image/video, or image_after+video_after for 'all'."""
    verify_client_access(client_id, current_user, db)
    service = MetaAdsService(db)
    token = service.get_token(str(client_id), str(current_user.id))
    if not token:
        raise HTTPException(status_code=400, detail="No Meta token for this client")
    if token.is_expired():
        raise HTTPException(status_code=401, detail="Meta token expired, please reconnect")
    ad_account_id = ad_account_id or token.default_ad_account_id
    if not ad_account_id:
        raise HTTPException(
            status_code=400,
            detail="No default ad account set. Please select an ad account first."
        )
    try:
        items = []
        paging_after = None
        paging_image_after = None
        paging_video_after = None
        paging_next = None
        per_type_limit = max(1, limit // 2) if media_type == "all" else limit
        # For "all", only request images when we have image_after (paginating) or no cursors yet (first page). Skip images when image_after is absent but video_after is present (images exhausted).
        request_images = media_type in ("all", "image") and (
            media_type != "all" or image_after is not None or video_after is None
        )
        if request_images:
            img_cursor = image_after if media_type == "all" else after
            img_result = await service.list_ad_images(
                token.access_token, ad_account_id, limit=per_type_limit, after=img_cursor
            )
            for img in img_result.get("data", []):
                items.append(MetaMediaLibraryItem(
                    type="image",
                    id=img.get("hash"),
                    name=img.get("name"),
                    thumbnail_url=img.get("url_128"),
                    original_url=img.get("original_url") or img.get("url"),
                    width=img.get("width"),
                    height=img.get("height"),
                    created_time=img.get("created_time"),
                ))
            img_paging = img_result.get("paging", {})
            if media_type == "all":
                paging_image_after = img_paging.get("after")
            else:
                paging_after = img_paging.get("after")
                paging_next = img_paging.get("next")
        elif media_type == "all":
            paging_image_after = None
        # For "all", only request videos when we have video_after or no cursors yet. Skip when video_after is absent but image_after is present (videos exhausted).
        request_videos = media_type in ("all", "video") and (
            media_type != "all" or video_after is not None or image_after is None
        )
        if request_videos:
            vid_cursor = video_after if media_type == "all" else after
            vid_result = await service.list_ad_videos(
                token.access_token, ad_account_id, limit=per_type_limit, after=vid_cursor
            )
            for vid in vid_result.get("data", []):
                thumb = vid.get("picture")
                if not thumb and vid.get("thumbnails", {}).get("data"):
                    thumbs = vid["thumbnails"]["data"]
                    if thumbs:
                        thumb = thumbs[0].get("uri")
                items.append(MetaMediaLibraryItem(
                    type="video",
                    id=vid.get("id"),
                    name=vid.get("title"),
                    thumbnail_url=thumb,
                    original_url=vid.get("source"),
                    source=vid.get("source"),
                    created_time=vid.get("created_time"),
                    length=vid.get("length"),
                ))
            vid_paging = vid_result.get("paging", {})
            if media_type == "all":
                paging_video_after = vid_paging.get("after")
            else:
                paging_after = vid_paging.get("after")
                paging_next = vid_paging.get("next")
        elif media_type == "all":
            paging_video_after = None
        has_more = paging_after or paging_image_after or paging_video_after
        return MetaMediaLibraryResponse(
            items=items,
            paging=MetaMediaLibraryPaging(
                after=paging_after,
                image_after=paging_image_after,
                video_after=paging_video_after,
                next=paging_next,
            ) if has_more else None,
        )
    except httpx.HTTPStatusError as e:
        msg = str(e)
        try:
            err_body = e.response.json()
            msg = err_body.get("error", {}).get("message", e.response.text) or msg
        except Exception:
            msg = e.response.text or msg
        logger.warning("Meta media library API failed: %s", msg)
        raise HTTPException(status_code=502, detail=f"Meta API: {msg}")
    except Exception as e:
        logger.exception("Meta media library error")
        raise HTTPException(status_code=502, detail=str(e))


def _normalize_url(url: str) -> str:
    if not url or not url.strip():
        return url
    u = url.strip()
    if u.startswith("//"):
        return "https:" + u
    if not u.startswith("http://") and not u.startswith("https://"):
        return "https://" + u
    return u


def _upsert_ad_image_performance(
    db: Session,
    image: AdImage,
    candidate: dict,
) -> None:
    """Create/update one best-performance row for the imported image."""
    existing = (
        db.query(AdImagePerformance)
        .filter(AdImagePerformance.ad_image_id == image.id)
        .first()
    )
    row = existing or AdImagePerformance(ad_image_id=image.id, client_id=image.client_id)

    revenue = float(candidate.get("revenue") or 0.0)
    spend = float(candidate.get("spend") or 0.0)
    impressions = int(candidate.get("impressions") or 0)
    clicks = int(candidate.get("clicks") or 0)
    ctr = float(candidate.get("ctr") or 0.0)
    roas = float(candidate.get("roas") or 0.0)

    row.client_id = image.client_id
    row.meta_ad_account_id = candidate.get("meta_ad_account_id") or image.meta_ad_account_id
    row.meta_ad_id = candidate.get("meta_ad_id")
    row.meta_creative_id = candidate.get("meta_creative_id")
    row.media_key = candidate.get("media_key") or image.library_id
    row.media_type = candidate.get("media_type")
    row.ad_primary_text = candidate.get("ad_primary_text")
    row.ad_headline = candidate.get("ad_headline")
    row.ad_description = candidate.get("ad_description")
    row.ad_call_to_action = candidate.get("ad_call_to_action")
    row.destination_url = candidate.get("destination_url")
    row.started_running_on = candidate.get("started_running_on")
    row.revenue = revenue
    row.spend = spend
    row.impressions = impressions
    row.clicks = clicks
    row.purchases = int(candidate.get("purchases") or 0)
    row.ctr = ctr
    row.roas = roas
    row.last_synced_at = datetime.now(timezone.utc)

    db.add(row)
    # Keep started_running_on on AdImage in sync with selected best ad.
    if row.started_running_on:
        image.started_running_on = row.started_running_on
        db.add(image)
    db.commit()


async def _import_one_meta_item(
    db: Session,
    client_id: UUID,
    ad_account_id: str,
    current_user: User,
    item: MetaMediaImportItem,
    blob_token: str,
    performance_lookup: Optional[dict[str, dict]] = None,
) -> tuple[Optional[AdImageResponse], bool]:
    """Download one Meta media item, upload to blob, create AdImage. Returns (response, success)."""
    if _is_untitled_thumbnail(item.filename):
        return (None, False)
    try:
        download_url = _normalize_url(item.original_url)
        if not download_url.startswith("http"):
            logger.warning("Skipping import item with invalid URL: %s", (item.original_url or "")[:80])
            return (None, False)
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(download_url)
            resp.raise_for_status()
            content = resp.content
            content_type = resp.headers.get("content-type", "image/jpeg")
        if "video" in content_type:
            content_type = "video/mp4"
        ext = "jpg"
        if "png" in content_type:
            ext = "png"
        elif "video" in content_type:
            ext = "mp4"
        random_suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=7))
        unique_filename = f"ad-images/{client_id}/{int(time.time())}-{random_suffix}.{ext}"
        import vercel_blob
        blob = vercel_blob.put(unique_filename, content, {
            "access": "public",
            "contentType": content_type,
            "token": blob_token,
        })
        blob_url = blob.get("url") if isinstance(blob, dict) else getattr(blob, "url", str(blob))
        meta_hash_or_video_id = item.hash if item.type == "image" else item.video_id
        filename = item.filename or (f"meta-{item.type}-{meta_hash_or_video_id or 'unknown'}.{ext}")
        meta_created = _parse_meta_created_time(item.created_time)
        image = AdImage(
            client_id=client_id,
            url=blob_url,
            filename=filename,
            file_size=len(content),
            content_type=content_type,
            uploaded_by=current_user.id,
            library_id=meta_hash_or_video_id,
            meta_ad_account_id=ad_account_id,
            meta_thumbnail_url=item.thumbnail_url if item.type == "video" else None,
            meta_created_time=meta_created,
        )
        db.add(image)
        db.commit()
        db.refresh(image)
        perf_for_response = None
        if performance_lookup and meta_hash_or_video_id:
            perf = performance_lookup.get(meta_hash_or_video_id)
            if perf:
                try:
                    _upsert_ad_image_performance(db, image, perf)
                    perf_for_response = perf
                except Exception as perf_err:
                    db.rollback()
                    logger.warning(
                        "Failed to persist performance for media key %s: %s",
                        meta_hash_or_video_id,
                        perf_err,
                    )
        response_payload = AdImageResponse.model_validate(image).model_dump(mode="python")
        if perf_for_response:
            response_payload.update({
                "revenue": perf_for_response.get("revenue"),
                "spend": perf_for_response.get("spend"),
                "impressions": perf_for_response.get("impressions"),
                "clicks": perf_for_response.get("clicks"),
                "purchases": perf_for_response.get("purchases"),
                "ctr": perf_for_response.get("ctr"),
                "roas": perf_for_response.get("roas"),
                "ad_primary_text": perf_for_response.get("ad_primary_text"),
                "ad_headline": perf_for_response.get("ad_headline"),
                "ad_description": perf_for_response.get("ad_description"),
                "ad_call_to_action": perf_for_response.get("ad_call_to_action"),
                "destination_url": perf_for_response.get("destination_url"),
                "started_running_on_best_ad": perf_for_response.get("started_running_on"),
                "meta_ad_id": perf_for_response.get("meta_ad_id"),
                "meta_creative_id": perf_for_response.get("meta_creative_id"),
                "performance_last_synced_at": datetime.now(timezone.utc),
            })
        return (AdImageResponse.model_validate(response_payload), True)
    except Exception as e:
        logger.warning("Failed to import Meta media item %s: %s", (item.original_url or "")[:80], e)
        return (None, False)


@router.post("/api/meta/import-media", response_model=MetaMediaImportResponse)
async def import_meta_media(
    request: MetaMediaImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MetaMediaImportResponse:
    """Import selected media from Meta ad account into local library (full-res download, Blob upload, AdImage records)."""
    verify_client_access(request.client_id, current_user, db)
    service = MetaAdsService(db)
    token = service.get_token(str(request.client_id), str(current_user.id))
    if not token:
        raise HTTPException(status_code=400, detail="No Meta token for this client")
    if token.is_expired():
        raise HTTPException(status_code=401, detail="Meta token expired, please reconnect")
    ad_account_id = request.ad_account_id or token.default_ad_account_id
    if not ad_account_id:
        raise HTTPException(status_code=400, detail="No ad account set. Please select an ad account.")
    blob_token = os.getenv("BLOB_READ_WRITE_TOKEN")
    if not blob_token:
        raise HTTPException(status_code=500, detail="Blob storage not configured")
    try:
        performance_lookup = await service.build_media_performance_lookup(
            token.access_token,
            ad_account_id,
        )
    except Exception as e:
        logger.warning("Meta performance lookup failed during import-media; continuing without performance: %s", e)
        performance_lookup = {}

    created = []
    failed_count = 0
    for item in request.items:
        resp, ok = await _import_one_meta_item(
            db,
            request.client_id,
            ad_account_id,
            current_user,
            item,
            blob_token,
            performance_lookup=performance_lookup,
        )
        if ok:
            created.append(resp)
        else:
            failed_count += 1
    if not created and failed_count > 0:
        raise HTTPException(status_code=502, detail=f"Import failed: all {failed_count} items failed (e.g. rate limit or download error). Try fewer items or try again later.")
    return MetaMediaImportResponse(items=created, failed_count=failed_count)


@router.post("/api/meta/import-media-stream")
async def import_meta_media_stream(
    request: MetaMediaImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Import selected media with SSE: progress (imported, total) and item (created AdImage) per successful import."""
    verify_client_access(request.client_id, current_user, db)
    service = MetaAdsService(db)
    token = service.get_token(str(request.client_id), str(current_user.id))
    if not token:
        raise HTTPException(status_code=400, detail="No Meta token for this client")
    if token.is_expired():
        raise HTTPException(status_code=401, detail="Meta token expired, please reconnect")
    ad_account_id = request.ad_account_id or token.default_ad_account_id
    if not ad_account_id:
        raise HTTPException(status_code=400, detail="No ad account set. Please select an ad account.")
    blob_token = os.getenv("BLOB_READ_WRITE_TOKEN")
    if not blob_token:
        raise HTTPException(status_code=500, detail="Blob storage not configured")
    try:
        performance_lookup = await service.build_media_performance_lookup(
            token.access_token,
            ad_account_id,
        )
    except Exception as e:
        logger.warning("Meta performance lookup failed during import-media-stream; continuing without performance: %s", e)
        performance_lookup = {}

    total = len(request.items)
    created: list = []
    failed_count = 0

    async def event_stream():
        nonlocal created, failed_count
        try:
            for i, item in enumerate(request.items):
                resp, ok = await _import_one_meta_item(
                    db,
                    request.client_id,
                    ad_account_id,
                    current_user,
                    item,
                    blob_token,
                    performance_lookup=performance_lookup,
                )
                if ok:
                    created.append(resp)
                    yield f"data: {json.dumps({'type': 'item', 'item': resp.model_dump(mode='json')})}\n\n".encode("utf-8")
                else:
                    failed_count += 1
                yield f"data: {json.dumps({'type': 'progress', 'imported': len(created), 'failed': failed_count, 'total': total})}\n\n".encode("utf-8")
            yield f"data: {json.dumps({'type': 'result', 'items': [x.model_dump(mode='json') for x in created], 'failed_count': failed_count})}\n\n".encode("utf-8")
        except Exception as e:
            logger.exception("Import-media-stream error")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n".encode("utf-8")

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/api/meta/import-all", response_model=MetaMediaImportResponse)
async def import_all_meta_media(
    request: MetaImportAllRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MetaMediaImportResponse:
    """Import all media from Meta ad account (server-side list + import). No need to load thumbnails in the UI."""
    verify_client_access(request.client_id, current_user, db)
    service = MetaAdsService(db)
    token = service.get_token(str(request.client_id), str(current_user.id))
    if not token:
        raise HTTPException(status_code=400, detail="No Meta token for this client")
    if token.is_expired():
        raise HTTPException(status_code=401, detail="Meta token expired, please reconnect")
    ad_account_id = request.ad_account_id or token.default_ad_account_id
    if not ad_account_id:
        raise HTTPException(status_code=400, detail="No ad account set. Please select an ad account.")
    blob_token = os.getenv("BLOB_READ_WRITE_TOKEN")
    if not blob_token:
        raise HTTPException(status_code=500, detail="Blob storage not configured")
    try:
        performance_lookup = await service.build_media_performance_lookup(
            token.access_token,
            ad_account_id,
        )
    except Exception as e:
        logger.warning("Meta performance lookup failed during import-all; continuing without performance: %s", e)
        performance_lookup = {}

    media_type = (request.media_type or "all").strip().lower()
    if media_type not in ("all", "image", "video"):
        media_type = "all"
    page_size = 24
    max_pages = 250
    created: list = []
    failed_count = 0
    image_after: Optional[str] = None
    video_after: Optional[str] = None
    after: Optional[str] = None
    pages_done = 0

    while pages_done < max_pages:
        to_import: list[MetaMediaImportItem] = []
        # Decide what to fetch using cursors at loop start (before any updates)
        request_images = media_type in ("all", "image") and (media_type != "all" or image_after is not None or video_after is None)
        request_videos = media_type in ("all", "video") and (media_type != "all" or video_after is not None or image_after is None)

        if request_images:
            img_cursor = image_after if media_type == "all" else after
            try:
                img_result = await service.list_ad_images(
                    token.access_token, ad_account_id, limit=page_size, after=img_cursor
                )
            except Exception as e:
                logger.warning("Import-all: list_ad_images failed: %s", e)
                break
            for img in img_result.get("data", []):
                to_import.append(MetaMediaImportItem(
                    type="image",
                    hash=img.get("hash"),
                    original_url=(img.get("original_url") or img.get("url")) or "",
                    filename=f"{img.get('name')}.jpg" if img.get("name") else None,
                    thumbnail_url=None,
                    created_time=img.get("created_time"),
                ))
            img_paging = img_result.get("paging", {})
            if media_type == "all":
                image_after = img_paging.get("after")
            else:
                after = img_paging.get("after")

        vid_result = None
        if request_videos:
            vid_cursor = video_after if media_type == "all" else after
            try:
                vid_result = await service.list_ad_videos(
                    token.access_token, ad_account_id, limit=page_size, after=vid_cursor
                )
            except Exception as e:
                logger.warning("Import-all: list_ad_videos failed: %s", e)
                request_videos = False
        if request_videos and vid_result is not None:
            thumb = None
            for vid in vid_result.get("data", []):
                t = vid.get("picture")
                if not t and vid.get("thumbnails", {}).get("data"):
                    thumbs = vid["thumbnails"]["data"]
                    if thumbs:
                        t = thumbs[0].get("uri")
                to_import.append(MetaMediaImportItem(
                    type="video",
                    video_id=vid.get("id"),
                    original_url=vid.get("source") or "",
                    filename=f"{vid.get('title')}.mp4" if vid.get("title") else None,
                    thumbnail_url=t,
                    created_time=vid.get("created_time"),
                ))
            vid_paging = vid_result.get("paging", {})
            if media_type == "all":
                video_after = vid_paging.get("after")
            else:
                after = vid_paging.get("after")
        if media_type != "all":
            break

        if not to_import:
            if media_type == "all":
                if not image_after and not video_after:
                    break
            else:
                break
        for item in to_import:
            resp, ok = await _import_one_meta_item(
                db,
                request.client_id,
                ad_account_id,
                current_user,
                item,
                blob_token,
                performance_lookup=performance_lookup,
            )
            if ok:
                created.append(resp)
            else:
                failed_count += 1
        pages_done += 1
        if media_type == "all":
            if not image_after and not video_after:
                break
        else:
            if not after:
                break

    if not created and failed_count > 0:
        raise HTTPException(status_code=502, detail=f"Import failed: all {failed_count} items failed. Try again later.")
    return MetaMediaImportResponse(items=created, failed_count=failed_count)


@router.post("/api/meta/import-all-stream")
async def import_all_meta_media_stream(
    request: MetaImportAllRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Import all media from Meta with Server-Sent Events progress. Streams progress and final result."""
    verify_client_access(request.client_id, current_user, db)
    service = MetaAdsService(db)
    token = service.get_token(str(request.client_id), str(current_user.id))
    if not token:
        raise HTTPException(status_code=400, detail="No Meta token for this client")
    if token.is_expired():
        raise HTTPException(status_code=401, detail="Meta token expired, please reconnect")
    ad_account_id = request.ad_account_id or token.default_ad_account_id
    if not ad_account_id:
        raise HTTPException(status_code=400, detail="No ad account set. Please select an ad account.")
    blob_token = os.getenv("BLOB_READ_WRITE_TOKEN")
    if not blob_token:
        raise HTTPException(status_code=500, detail="Blob storage not configured")
    try:
        performance_lookup = await service.build_media_performance_lookup(
            token.access_token,
            ad_account_id,
        )
    except Exception as e:
        logger.warning("Meta performance lookup failed during import-all-stream; continuing without performance: %s", e)
        performance_lookup = {}

    media_type = (request.media_type or "all").strip().lower()
    if media_type not in ("all", "image", "video"):
        media_type = "all"
    page_size = 24
    max_pages = 250
    created: list = []
    failed_count = 0
    image_after: Optional[str] = None
    video_after: Optional[str] = None
    after: Optional[str] = None
    pages_done = 0

    async def event_stream():
        nonlocal created, failed_count, pages_done, image_after, video_after, after
        try:
            while pages_done < max_pages:
                to_import: list[MetaMediaImportItem] = []
                # Decide what to fetch using cursors at loop start (before any updates)
                request_images = media_type in ("all", "image") and (media_type != "all" or image_after is not None or video_after is None)
                request_videos = media_type in ("all", "video") and (media_type != "all" or video_after is not None or image_after is None)

                if request_images:
                    img_cursor = image_after if media_type == "all" else after
                    try:
                        img_result = await service.list_ad_images(
                            token.access_token, ad_account_id, limit=page_size, after=img_cursor
                        )
                    except Exception as e:
                        logger.warning("Import-all-stream: list_ad_images failed: %s", e)
                        break
                    for img in img_result.get("data", []):
                        to_import.append(MetaMediaImportItem(
                            type="image",
                            hash=img.get("hash"),
                            original_url=(img.get("original_url") or img.get("url")) or "",
                            filename=f"{img.get('name')}.jpg" if img.get("name") else None,
                            thumbnail_url=None,
                            created_time=img.get("created_time"),
                        ))
                    img_paging = img_result.get("paging", {})
                    if media_type == "all":
                        image_after = img_paging.get("after")
                    else:
                        after = img_paging.get("after")

                vid_result = None
                if request_videos:
                    vid_cursor = video_after if media_type == "all" else after
                    try:
                        vid_result = await service.list_ad_videos(
                            token.access_token, ad_account_id, limit=page_size, after=vid_cursor
                        )
                    except Exception as e:
                        logger.warning("Import-all-stream: list_ad_videos failed: %s", e)
                        if media_type != "all":
                            break
                        request_videos = False
                if request_videos and vid_result is not None:
                    for vid in vid_result.get("data", []):
                        t = vid.get("picture")
                        if not t and vid.get("thumbnails", {}).get("data"):
                            thumbs = vid["thumbnails"]["data"]
                            if thumbs:
                                t = thumbs[0].get("uri")
                        to_import.append(MetaMediaImportItem(
                            type="video",
                            video_id=vid.get("id"),
                            original_url=vid.get("source") or "",
                            filename=f"{vid.get('title')}.mp4" if vid.get("title") else None,
                            thumbnail_url=t,
                            created_time=vid.get("created_time"),
                        ))
                    vid_paging = vid_result.get("paging", {})
                    if media_type == "all":
                        video_after = vid_paging.get("after")
                    else:
                        after = vid_paging.get("after")
                if media_type != "all":
                    break

                if not to_import:
                    if media_type == "all":
                        if not image_after and not video_after:
                            break
                    else:
                        break
                for item in to_import:
                    resp, ok = await _import_one_meta_item(
                        db,
                        request.client_id,
                        ad_account_id,
                        current_user,
                        item,
                        blob_token,
                        performance_lookup=performance_lookup,
                    )
                    if ok:
                        created.append(resp)
                        yield f"data: {json.dumps({'type': 'item', 'item': resp.model_dump(mode='json')})}\n\n".encode("utf-8")
                    else:
                        failed_count += 1
                    # Yield progress after each item so the client receives updates promptly (avoids buffering hiding progress until end of page)
                    yield f"data: {json.dumps({'type': 'progress', 'imported': len(created), 'failed': failed_count, 'pages_done': pages_done})}\n\n".encode("utf-8")
                pages_done += 1

                if media_type == "all":
                    if not image_after and not video_after:
                        break
                else:
                    if not after:
                        break

            payload = {
                "type": "result",
                "items": [x.model_dump(mode="json") for x in created],
                "failed_count": failed_count,
            }
            yield f"data: {json.dumps(payload)}\n\n".encode("utf-8")
        except Exception as e:
            logger.exception("Import-all-stream error")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n".encode("utf-8")

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/api/meta/publish-ad")
async def publish_ad(
    request: PublishAdRequest,
    page_id: str = Query(..., description="Facebook page ID to publish from"),
    client_id: UUID = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PublishAdResponse:
    """
    Publish a local Facebook ad to Meta.
    Creates ad creative and ad in the specified adset.
    """
    verify_client_access(client_id, current_user, db)
    service = MetaAdsService(db)
    token = service.get_token(str(client_id), str(current_user.id))
    if not token:
        raise HTTPException(status_code=400, detail="No Meta token for this client")
    try:
        result = await service.publish_ad(
            ad_id=str(request.ad_id),
            user_id=str(current_user.id),
            adset_id=request.adset_id,
            ad_account_id=request.ad_account_id,
            page_id=page_id,
            ad_name=request.name,
            status=request.status,
        )
        
        return PublishAdResponse(
            success=True,
            meta_ad_id=result.get("meta_ad_id"),
            meta_creative_id=result.get("meta_creative_id"),
        )
    except Exception as e:
        logger.error(f"Failed to publish ad: {e}")
        return PublishAdResponse(
            success=False,
            error=str(e),
        )
