"""
Meta Ads management routes for OAuth and Marketing API.
Access: any authenticated user with access to the client (membership or founder).
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional
import logging
import secrets
import base64
import hashlib
import hmac
import json

import httpx
from app.database import get_db
from app.models import User, Client, MetaOAuthToken
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
)
from app.auth import get_current_user
from app.authorization import verify_client_access
from app.config import get_settings
from app.services.meta_ads_service import MetaAdsService

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory state storage for OAuth (in production, use Redis or DB)
_oauth_states = {}


# ==================== OAuth Endpoints ====================

@router.get("/api/meta/oauth/debug-redirect")
def meta_oauth_debug_redirect(request: Request):
    """Temporary diagnostic: shows what redirect_uri would be computed. Remove after debugging."""
    settings = get_settings()
    explicit = settings.meta_redirect_uri
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("host", "localhost:8000")
    derived = f"{scheme}://{host}/api/meta/oauth/callback"
    return {
        "meta_redirect_uri_setting": explicit,
        "derived_redirect_uri": derived,
        "would_use": explicit if explicit else derived,
        "request_host": host,
        "request_scheme": request.url.scheme,
        "x_forwarded_proto": request.headers.get("x-forwarded-proto"),
        "frontend_base_url": settings.frontend_base_url,
    }


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
    
    # #region agent log
    import json as _json, time as _time, pathlib as _pathlib
    _dbg_path = _pathlib.Path("/Users/davidrawlings/Code/Marketable Project Folder/vizualizd/.cursor/debug-df77f4.log")
    _dbg_path.parent.mkdir(parents=True, exist_ok=True)
    with open(_dbg_path, "a") as _f:
        _f.write(_json.dumps({"sessionId":"df77f4","hypothesisId":"H5","location":"meta_ads.py:oauth_init","message":"redirect_uri resolution","data":{"meta_redirect_uri_setting":settings.meta_redirect_uri,"request_host":request.headers.get("host"),"request_scheme":request.url.scheme,"x_forwarded_proto":request.headers.get("x-forwarded-proto"),"final_redirect_uri":redirect_uri},"timestamp":_time.time()})+"\n")
    # #endregion
    
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
