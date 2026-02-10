"""
Meta/Facebook Marketing API service.
Handles OAuth token exchange and Marketing API calls.
"""
import logging
import httpx
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import MetaOAuthToken, FacebookAd, Client

logger = logging.getLogger(__name__)

# Meta API base URLs
META_GRAPH_API_BASE = "https://graph.facebook.com/v21.0"
META_OAUTH_BASE = "https://www.facebook.com/v21.0/dialog/oauth"


class MetaAdsService:
    """Service for interacting with Meta Marketing API."""
    
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
    
    # ==================== OAuth Methods ====================
    
    def get_oauth_url(self, client_id: str, redirect_uri: str, state: str) -> str:
        """
        Generate Meta OAuth authorization URL.
        
        Args:
            client_id: Internal client ID for state tracking
            redirect_uri: URL to redirect after auth
            state: CSRF protection token
        
        Returns:
            OAuth authorization URL
        """
        scopes = "ads_management,ads_read,business_management,pages_show_list"
        
        params = {
            "client_id": self.settings.meta_app_id,
            "redirect_uri": redirect_uri,
            "state": state,
            "scope": scopes,
            "response_type": "code",
        }
        
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{META_OAUTH_BASE}?{query_string}"
    
    async def exchange_code_for_token(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """
        Exchange OAuth authorization code for access token.
        
        Args:
            code: Authorization code from OAuth callback
            redirect_uri: Same redirect URI used in auth request
        
        Returns:
            Dict with access_token, token_type, expires_in
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{META_GRAPH_API_BASE}/oauth/access_token",
                params={
                    "client_id": self.settings.meta_app_id,
                    "client_secret": self.settings.meta_app_secret,
                    "redirect_uri": redirect_uri,
                    "code": code,
                }
            )
            response.raise_for_status()
            return response.json()
    
    async def exchange_for_long_lived_token(self, short_lived_token: str) -> Dict[str, Any]:
        """
        Exchange short-lived token for long-lived token (60 days).
        
        Args:
            short_lived_token: Short-lived access token
        
        Returns:
            Dict with access_token, token_type, expires_in
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{META_GRAPH_API_BASE}/oauth/access_token",
                params={
                    "grant_type": "fb_exchange_token",
                    "client_id": self.settings.meta_app_id,
                    "client_secret": self.settings.meta_app_secret,
                    "fb_exchange_token": short_lived_token,
                }
            )
            response.raise_for_status()
            return response.json()
    
    async def get_meta_user_info(self, access_token: str) -> Dict[str, Any]:
        """
        Get Meta user info from access token.
        
        Returns:
            Dict with id, name
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{META_GRAPH_API_BASE}/me",
                params={
                    "access_token": access_token,
                    "fields": "id,name",
                }
            )
            response.raise_for_status()
            return response.json()
    
    def save_token(
        self,
        client_id: str,
        access_token: str,
        expires_in: Optional[int],
        meta_user_id: str,
        meta_user_name: str,
        created_by_user_id: Optional[str] = None,
    ) -> MetaOAuthToken:
        """
        Save or update Meta OAuth token for a client.
        
        Args:
            client_id: Internal client UUID
            access_token: Meta access token
            expires_in: Token lifetime in seconds
            meta_user_id: Meta user ID
            meta_user_name: Meta user name
            created_by_user_id: User who authorized
        
        Returns:
            MetaOAuthToken instance
        """
        expires_at = None
        if expires_in:
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        
        # Check for existing token
        existing = self.db.query(MetaOAuthToken).filter(
            MetaOAuthToken.client_id == client_id
        ).first()
        
        if existing:
            existing.access_token = access_token
            existing.expires_at = expires_at
            existing.meta_user_id = meta_user_id
            existing.meta_user_name = meta_user_name
            existing.created_by = created_by_user_id
            self.db.commit()
            self.db.refresh(existing)
            return existing
        
        token = MetaOAuthToken(
            client_id=client_id,
            access_token=access_token,
            expires_at=expires_at,
            meta_user_id=meta_user_id,
            meta_user_name=meta_user_name,
            created_by=created_by_user_id,
        )
        self.db.add(token)
        self.db.commit()
        self.db.refresh(token)
        return token
    
    def get_token(self, client_id: str) -> Optional[MetaOAuthToken]:
        """Get Meta OAuth token for a client."""
        return self.db.query(MetaOAuthToken).filter(
            MetaOAuthToken.client_id == client_id
        ).first()
    
    def set_default_ad_account(
        self,
        client_id: str,
        ad_account_id: str,
        ad_account_name: Optional[str] = None,
    ) -> MetaOAuthToken:
        """Set the default ad account for a client."""
        token = self.get_token(client_id)
        if not token:
            raise ValueError(f"No Meta token found for client {client_id}")
        
        token.default_ad_account_id = ad_account_id
        token.default_ad_account_name = ad_account_name
        self.db.commit()
        self.db.refresh(token)
        return token
    
    # ==================== Ad Account Methods ====================
    
    async def list_ad_accounts(self, access_token: str) -> List[Dict[str, Any]]:
        """
        List all ad accounts accessible to the user.
        
        Returns:
            List of ad account dicts with id, name, account_status, etc.
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{META_GRAPH_API_BASE}/me/adaccounts",
                params={
                    "access_token": access_token,
                    "fields": "id,name,account_status,currency,timezone_name",
                    "limit": 100,
                }
            )
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
    
    # ==================== Campaign Methods ====================
    
    async def list_campaigns(
        self,
        access_token: str,
        ad_account_id: str,
    ) -> List[Dict[str, Any]]:
        """
        List campaigns for an ad account.
        
        Args:
            access_token: Meta access token
            ad_account_id: Ad account ID (e.g., act_123456)
        
        Returns:
            List of campaign dicts
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{META_GRAPH_API_BASE}/{ad_account_id}/campaigns",
                params={
                    "access_token": access_token,
                    "fields": "id,name,status,objective,created_time",
                    "limit": 100,
                }
            )
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
    
    async def create_campaign(
        self,
        access_token: str,
        ad_account_id: str,
        name: str,
        objective: str = "OUTCOME_TRAFFIC",
        status: str = "PAUSED",
        special_ad_categories: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Create a new campaign.
        
        Returns:
            Dict with created campaign id
        """
        import json as json_module
        
        async with httpx.AsyncClient() as client:
            # special_ad_categories must be sent as JSON array string
            categories = special_ad_categories or []
            
            data = {
                "name": name,
                "objective": objective,
                "status": status,
                "special_ad_categories": json_module.dumps(categories),
                "is_adset_budget_sharing_enabled": "false",  # Required when not using campaign budget
                "access_token": access_token,
            }
            
            response = await client.post(
                f"{META_GRAPH_API_BASE}/{ad_account_id}/campaigns",
                data=data,
            )
            
            if not response.is_success:
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", response.text)
                    logger.error(f"Meta campaign creation failed: {error_msg}")
                    raise Exception(f"Meta API error: {error_msg}")
                except Exception as e:
                    logger.error(f"Meta campaign creation failed: {response.text}")
                    raise
            
            return response.json()
    
    # ==================== AdSet Methods ====================
    
    async def list_adsets(
        self,
        access_token: str,
        campaign_id: str,
    ) -> List[Dict[str, Any]]:
        """
        List adsets for a campaign.
        
        Returns:
            List of adset dicts
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{META_GRAPH_API_BASE}/{campaign_id}/adsets",
                params={
                    "access_token": access_token,
                    "fields": "id,name,status,daily_budget,lifetime_budget",
                    "limit": 100,
                }
            )
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
    
    async def create_adset(
        self,
        access_token: str,
        ad_account_id: str,
        campaign_id: str,
        name: str,
        daily_budget: Optional[int] = None,
        lifetime_budget: Optional[int] = None,
        billing_event: str = "IMPRESSIONS",
        optimization_goal: str = "LINK_CLICKS",
        status: str = "PAUSED",
        targeting: Optional[Dict] = None,
        promoted_object: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Create a new adset.
        
        Args:
            daily_budget: Daily budget in cents (e.g., 1000 = $10)
            lifetime_budget: Lifetime budget in cents
            targeting: Targeting specification dict
            promoted_object: Required for certain optimization goals (e.g., OFFSITE_CONVERSIONS needs pixel_id)
        
        Returns:
            Dict with created adset id
        """
        # Default targeting if not provided (broad targeting)
        if targeting is None:
            targeting = {
                "geo_locations": {
                    "countries": ["US"],
                },
            }
        
        async with httpx.AsyncClient() as client:
            import json as json_module
            
            data = {
                "name": name,
                "campaign_id": campaign_id,
                "billing_event": billing_event,
                "optimization_goal": optimization_goal,
                "bid_strategy": "LOWEST_COST_WITHOUT_CAP",  # Automatic bidding, no bid cap required
                "status": status,
                "targeting": json_module.dumps(targeting),
                "access_token": access_token,
            }
            
            if daily_budget:
                data["daily_budget"] = daily_budget
            if lifetime_budget:
                data["lifetime_budget"] = lifetime_budget
            if promoted_object:
                data["promoted_object"] = json_module.dumps(promoted_object)
            
            response = await client.post(
                f"{META_GRAPH_API_BASE}/{ad_account_id}/adsets",
                data=data,
            )
            
            if not response.is_success:
                try:
                    error_data = response.json()
                    error_obj = error_data.get("error", {})
                    error_msg = error_obj.get("message", response.text)
                    error_subcode = error_obj.get("error_subcode")
                    error_user_msg = error_obj.get("error_user_msg", "")
                    error_user_title = error_obj.get("error_user_title", "")
                    
                    logger.error(f"Meta adset creation failed: {error_user_msg or error_msg}")
                    # Use user-friendly message if available
                    raise Exception(f"Meta API error: {error_user_msg or error_msg}")
                except Exception as e:
                    logger.error(f"Meta adset creation failed: {response.text}")
                    raise
            
            return response.json()
    
    # ==================== Ad Publishing Methods ====================
    
    async def upload_image(
        self,
        access_token: str,
        ad_account_id: str,
        image_url: str,
    ) -> Dict[str, Any]:
        """
        Upload an image to Meta from URL.
        
        Returns:
            Dict with hash (image_hash)
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{META_GRAPH_API_BASE}/{ad_account_id}/adimages",
                data={
                    "url": image_url,
                    "access_token": access_token,
                }
            )
            response.raise_for_status()
            result = response.json()
            
            # Response format: {"images": {"filename": {"hash": "...", "url": "..."}}}
            images = result.get("images", {})
            if images:
                first_image = list(images.values())[0]
                return {"hash": first_image.get("hash")}
            
            return result
    
    async def create_ad_creative(
        self,
        access_token: str,
        ad_account_id: str,
        name: str,
        page_id: str,
        image_hash: Optional[str],
        primary_text: str,
        headline: str,
        description: str,
        link_url: str,
        call_to_action: str,
    ) -> Dict[str, Any]:
        """
        Create an ad creative.
        
        Returns:
            Dict with created creative id
        """
        import json
        
        # Build object story spec for link ad
        object_story_spec = {
            "page_id": page_id,
            "link_data": {
                "link": link_url,
                "message": primary_text,
                "name": headline,
                "description": description,
                "call_to_action": {
                    "type": call_to_action,
                    "value": {
                        "link": link_url,
                    }
                }
            }
        }
        
        if image_hash:
            object_story_spec["link_data"]["image_hash"] = image_hash
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{META_GRAPH_API_BASE}/{ad_account_id}/adcreatives",
                data={
                    "name": name,
                    "object_story_spec": json.dumps(object_story_spec),
                    "access_token": access_token,
                }
            )
            
            if not response.is_success:
                try:
                    error_data = response.json()
                    error_obj = error_data.get("error", {})
                    error_msg = error_obj.get("message", response.text)
                    error_subcode = error_obj.get("error_subcode")
                    error_user_msg = error_obj.get("error_user_msg", "")
                    
                    # Provide clearer message for common errors
                    if error_subcode == 1885183 or "development mode" in error_user_msg.lower():
                        raise Exception(
                            "Your Meta App is in Development Mode. "
                            "Go to developers.facebook.com, select your app, and switch to Live mode to publish ads."
                        )
                    
                    raise Exception(f"Meta API error: {error_user_msg or error_msg}")
                except Exception:
                    raise
            
            return response.json()
    
    async def create_ad(
        self,
        access_token: str,
        ad_account_id: str,
        adset_id: str,
        creative_id: str,
        name: str,
        status: str = "PAUSED",
    ) -> Dict[str, Any]:
        """
        Create an ad.
        
        Returns:
            Dict with created ad id
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{META_GRAPH_API_BASE}/{ad_account_id}/ads",
                data={
                    "name": name,
                    "adset_id": adset_id,
                    "creative": f'{{"creative_id": "{creative_id}"}}',
                    "status": status,
                    "access_token": access_token,
                }
            )
            response.raise_for_status()
            return response.json()
    
    async def publish_ad(
        self,
        ad_id: str,
        adset_id: str,
        ad_account_id: str,
        page_id: str,
        ad_name: Optional[str] = None,
        status: str = "PAUSED",
    ) -> Dict[str, Any]:
        """
        Publish a local Facebook ad to Meta.
        
        This creates the ad creative and ad in Meta.
        
        Args:
            ad_id: Local FacebookAd UUID
            adset_id: Meta adset ID to publish to
            ad_account_id: Meta ad account ID
            page_id: Facebook page ID for the ad
            ad_name: Optional name for the ad in Meta
            status: Initial ad status (PAUSED recommended)
        
        Returns:
            Dict with meta_ad_id, meta_creative_id
        """
        # Get the local ad
        ad = self.db.query(FacebookAd).filter(FacebookAd.id == ad_id).first()
        if not ad:
            raise ValueError(f"Ad {ad_id} not found")
        
        # Get the token for the client
        token = self.get_token(str(ad.client_id))
        if not token:
            raise ValueError(f"No Meta token for client {ad.client_id}")
        
        access_token = token.access_token
        
        # Upload image if we have one
        image_hash = None
        image_url = ad.full_json.get("image_url") if ad.full_json else None
        if image_url:
            try:
                image_result = await self.upload_image(access_token, ad_account_id, image_url)
                image_hash = image_result.get("hash")
                logger.info(f"Uploaded image for ad {ad_id}, hash: {image_hash}")
            except Exception as e:
                logger.warning(f"Failed to upload image for ad {ad_id}: {e}")
        
        # Create the ad creative
        creative_name = ad_name or f"Creative - {ad.headline[:30]}"
        creative_result = await self.create_ad_creative(
            access_token=access_token,
            ad_account_id=ad_account_id,
            name=creative_name,
            page_id=page_id,
            image_hash=image_hash,
            primary_text=ad.primary_text,
            headline=ad.headline,
            description=ad.description or "",
            link_url=ad.destination_url or "https://example.com",
            call_to_action=ad.call_to_action,
        )
        creative_id = creative_result.get("id")
        logger.info(f"Created creative {creative_id} for ad {ad_id}")
        
        # Create the ad
        ad_meta_name = ad_name or f"Ad - {ad.headline[:30]}"
        ad_result = await self.create_ad(
            access_token=access_token,
            ad_account_id=ad_account_id,
            adset_id=adset_id,
            creative_id=creative_id,
            name=ad_meta_name,
            status=status,
        )
        meta_ad_id = ad_result.get("id")
        logger.info(f"Created Meta ad {meta_ad_id} for local ad {ad_id}")
        
        # Update local ad status
        ad.status = "exported"
        self.db.commit()
        
        return {
            "meta_ad_id": meta_ad_id,
            "meta_creative_id": creative_id,
        }
    
    # ==================== Pixel Methods ====================
    
    async def list_pixels(
        self,
        access_token: str,
        ad_account_id: str,
    ) -> List[Dict[str, Any]]:
        """
        List Facebook pixels for an ad account.
        
        Returns:
            List of pixel dicts with id, name
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{META_GRAPH_API_BASE}/{ad_account_id}/adspixels",
                params={
                    "access_token": access_token,
                    "fields": "id,name",
                    "limit": 100,
                }
            )
            
            if not response.is_success:
                logger.warning(f"Failed to fetch pixels: {response.text}")
                return []
            
            data = response.json()
            return data.get("data", [])
    
    # ==================== Facebook Page Methods ====================
    
    async def list_pages(self, access_token: str) -> List[Dict[str, Any]]:
        """
        List Facebook pages the user manages.
        
        Returns:
            List of page dicts with id, name, access_token
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{META_GRAPH_API_BASE}/me/accounts",
                params={
                    "access_token": access_token,
                    "fields": "id,name,access_token",
                    "limit": 100,
                }
            )
            
            if not response.is_success:
                logger.error(f"Failed to fetch pages: {response.text}")
                return []
            
            data = response.json()
            return data.get("data", [])
