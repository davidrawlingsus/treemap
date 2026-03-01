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
META_GRAPH_API_BASE = "https://graph.facebook.com/v24.0"
META_OAUTH_BASE = "https://www.facebook.com/v24.0/dialog/oauth"


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
        user_id: str,
        access_token: str,
        expires_in: Optional[int],
        meta_user_id: str,
        meta_user_name: str,
    ) -> MetaOAuthToken:
        """
        Save or update Meta OAuth token for a (user, client).
        
        Args:
            client_id: Internal client UUID
            user_id: Internal user UUID who owns this connection
            access_token: Meta access token
            expires_in: Token lifetime in seconds
            meta_user_id: Meta user ID
            meta_user_name: Meta user name
        
        Returns:
            MetaOAuthToken instance
        """
        expires_at = None
        if expires_in:
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        
        existing = self.db.query(MetaOAuthToken).filter(
            MetaOAuthToken.client_id == client_id,
            MetaOAuthToken.user_id == user_id,
        ).first()
        
        if existing:
            existing.access_token = access_token
            existing.expires_at = expires_at
            existing.meta_user_id = meta_user_id
            existing.meta_user_name = meta_user_name
            existing.created_by = user_id
            self.db.commit()
            self.db.refresh(existing)
            return existing
        
        token = MetaOAuthToken(
            client_id=client_id,
            user_id=user_id,
            access_token=access_token,
            expires_at=expires_at,
            meta_user_id=meta_user_id,
            meta_user_name=meta_user_name,
            created_by=user_id,
        )
        self.db.add(token)
        self.db.commit()
        self.db.refresh(token)
        return token
    
    def get_token(self, client_id: str, user_id: str) -> Optional[MetaOAuthToken]:
        """Get Meta OAuth token for a (user, client)."""
        return self.db.query(MetaOAuthToken).filter(
            MetaOAuthToken.client_id == client_id,
            MetaOAuthToken.user_id == user_id,
        ).first()
    
    def set_default_ad_account(
        self,
        client_id: str,
        user_id: str,
        ad_account_id: str,
        ad_account_name: Optional[str] = None,
    ) -> MetaOAuthToken:
        """Set the default ad account for a (user, client)."""
        token = self.get_token(client_id, user_id)
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
    
    # ==================== Text Preparation ====================
    
    @staticmethod
    def prepare_text_for_meta(text: str) -> str:
        """
        Convert raw ad text (with literal escape sequences and markdown)
        into clean plain text suitable for Facebook's API.
        """
        if not text:
            return ""
        import re
        
        # Convert literal escape sequences to actual characters
        result = text.replace('\\n', '\n').replace('\\r', '\r').replace('\\"', '"')
        
        # Normalize line endings
        result = result.replace('\r\n', '\n').replace('\r', '\n')
        
        # Strip markdown formatting (keep the text content)
        result = re.sub(r'\*\*(.+?)\*\*', r'\1', result)  # **bold**
        result = re.sub(r'\*(.+?)\*', r'\1', result)       # *italic*
        result = re.sub(r'^#{1,6}\s+', '', result, flags=re.MULTILINE)  # # headers
        
        return result
    
    # ==================== Ad Publishing Methods ====================
    
    VIDEO_EXTENSIONS = ('.mp4', '.webm', '.mov', '.avi', '.mkv', '.m4v')
    
    @staticmethod
    def is_video_url(url: str) -> bool:
        """Check if a URL points to a video file based on extension."""
        if not url:
            return False
        lower_url = url.lower()
        return any(ext in lower_url for ext in MetaAdsService.VIDEO_EXTENSIONS)
    
    async def upload_image(
        self,
        access_token: str,
        ad_account_id: str,
        image_url: str,
    ) -> Dict[str, Any]:
        """
        Upload an image to Meta by downloading bytes and uploading as file data.
        
        Returns:
            Dict with hash (image_hash)
        """
        from urllib.parse import urlparse
        
        endpoint = f"{META_GRAPH_API_BASE}/{ad_account_id}/adimages"
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            img_resp = await client.get(image_url)
            img_resp.raise_for_status()
            img_bytes = img_resp.content
            content_type = img_resp.headers.get("content-type", "image/jpeg")
            filename = urlparse(image_url).path.split("/")[-1] or "image.jpg"
            
            response = await client.post(
                endpoint,
                data={"access_token": access_token},
                files={"filename": (filename, img_bytes, content_type)},
            )
            
            if not response.is_success:
                error_detail = response.text[:500]
                raise Exception(f"Image upload failed ({response.status_code}): {error_detail}")
            
            result = response.json()
            
            images = result.get("images", {})
            if images:
                first_image = list(images.values())[0]
                return {"hash": first_image.get("hash")}
            
            return result
    
    async def upload_video(
        self,
        access_token: str,
        ad_account_id: str,
        video_url: str,
    ) -> Dict[str, Any]:
        """
        Upload a video to Meta from URL.
        
        Returns:
            Dict with video_id and thumbnail_url
        """
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{META_GRAPH_API_BASE}/{ad_account_id}/advideos",
                data={
                    "file_url": video_url,
                    "access_token": access_token,
                }
            )
            
            if not response.is_success:
                try:
                    error_data = response.json()
                    error_obj = error_data.get("error", {})
                    error_msg = error_obj.get("error_user_msg") or error_obj.get("message", response.text)
                    raise Exception(f"Meta video upload error: {error_msg}")
                except Exception:
                    raise
            
            result = response.json()
            video_id = result.get("id")
            if not video_id:
                raise Exception(f"Meta video upload: no video_id in response: {result}")
            
            # Fetch auto-generated thumbnail from the uploaded video
            thumbnail_url = None
            try:
                thumb_response = await client.get(
                    f"{META_GRAPH_API_BASE}/{video_id}",
                    params={
                        "access_token": access_token,
                        "fields": "picture,thumbnails",
                    }
                )
                if thumb_response.is_success:
                    thumb_data = thumb_response.json()
                    thumbnail_url = thumb_data.get("picture")
                    if not thumbnail_url:
                        thumbs = thumb_data.get("thumbnails", {}).get("data", [])
                        if thumbs:
                            thumbnail_url = thumbs[0].get("uri")
                    logger.info(f"Video {video_id} thumbnail: {thumbnail_url}")
            except Exception as e:
                logger.warning(f"Failed to fetch video thumbnail: {e}")
            
            return {"video_id": video_id, "thumbnail_url": thumbnail_url}
    
    async def create_ad_creative(
        self,
        access_token: str,
        ad_account_id: str,
        name: str,
        page_id: str,
        primary_text: str,
        headline: str,
        description: str,
        link_url: str,
        call_to_action: str,
        image_hash: Optional[str] = None,
        video_id: Optional[str] = None,
        thumbnail_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create an ad creative (supports both image and video).
        
        For image ads: pass image_hash
        For video ads: pass video_id (and optionally thumbnail_url)
        
        Returns:
            Dict with created creative id
        """
        import json
        
        cta_spec = {
            "type": call_to_action,
            "value": {
                "link": link_url,
            }
        }
        
        if video_id:
            # Video creative uses video_data spec
            object_story_spec = {
                "page_id": page_id,
                "video_data": {
                    "video_id": video_id,
                    "message": primary_text,
                    "title": headline,
                    "link_description": description,
                    "call_to_action": cta_spec,
                }
            }
            if thumbnail_url:
                object_story_spec["video_data"]["image_url"] = thumbnail_url
        else:
            # Image/link creative uses link_data spec
            object_story_spec = {
                "page_id": page_id,
                "link_data": {
                    "link": link_url,
                    "message": primary_text,
                    "name": headline,
                    "description": description,
                    "call_to_action": cta_spec,
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
            payload = {
                "name": name,
                "adset_id": adset_id,
                "creative": f'{{"creative_id": "{creative_id}"}}',
                "status": status,
                "access_token": access_token,
            }
            
            response = await client.post(
                f"{META_GRAPH_API_BASE}/{ad_account_id}/ads",
                data=payload,
            )
            
            if not response.is_success:
                try:
                    error_data = response.json()
                    error_obj = error_data.get("error", {})
                    error_msg = error_obj.get("message", response.text)
                    error_code = error_obj.get("code")
                    error_subcode = error_obj.get("error_subcode")
                    error_user_msg = error_obj.get("error_user_msg", "")
                    
                    logger.error(f"Meta ad creation failed: code={error_code} subcode={error_subcode} msg={error_user_msg or error_msg}")
                    raise Exception(f"Meta API error: {error_user_msg or error_msg}")
                except Exception:
                    raise
            
            return response.json()
    
    async def publish_ad(
        self,
        ad_id: str,
        user_id: str,
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
            user_id: Internal user UUID (owns the Meta connection)
            adset_id: Meta adset ID to publish to
            ad_account_id: Meta ad account ID
            page_id: Facebook page ID for the ad
            ad_name: Optional name for the ad in Meta
            status: Initial ad status (PAUSED recommended)
        
        Returns:
            Dict with meta_ad_id, meta_creative_id
        """
        ad = self.db.query(FacebookAd).filter(FacebookAd.id == ad_id).first()
        if not ad:
            raise ValueError(f"Ad {ad_id} not found")
        
        token = self.get_token(str(ad.client_id), user_id)
        if not token:
            raise ValueError(f"No Meta token for client {ad.client_id}")
        
        access_token = token.access_token
        
        # Prepare text fields for Meta (convert escape sequences, strip markdown)
        clean_primary_text = self.prepare_text_for_meta(ad.primary_text)
        clean_headline = self.prepare_text_for_meta(ad.headline)
        clean_description = self.prepare_text_for_meta(ad.description or "")
        
        # Media: reuse existing Meta asset if ad was built from FB Connector media (same account)
        image_hash = None
        video_id = None
        thumbnail_url = None
        full_json = ad.full_json or {}
        media_url = full_json.get("image_url")
        meta_account = full_json.get("meta_ad_account_id")
        meta_image_hash = full_json.get("meta_image_hash")
        meta_video_id = full_json.get("meta_video_id")
        meta_thumb = full_json.get("meta_thumbnail_url")
        reuse_meta = (
            meta_account == ad_account_id
            and (meta_image_hash or meta_video_id)
        )
        if reuse_meta:
            image_hash = meta_image_hash
            video_id = meta_video_id
            thumbnail_url = meta_thumb
            logger.info(f"Reusing Meta asset for ad {ad_id}: image_hash={image_hash}, video_id={video_id}")
        else:
            is_video = self.is_video_url(media_url) if media_url else False
            if media_url and is_video:
                try:
                    video_result = await self.upload_video(access_token, ad_account_id, media_url)
                    video_id = video_result.get("video_id")
                    thumbnail_url = video_result.get("thumbnail_url")
                    logger.info(f"Uploaded video for ad {ad_id}, video_id: {video_id}")
                except Exception as e:
                    logger.warning(f"Failed to upload video for ad {ad_id}: {e}")
            elif media_url:
                try:
                    image_result = await self.upload_image(access_token, ad_account_id, media_url)
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
            primary_text=clean_primary_text,
            headline=clean_headline,
            description=clean_description,
            link_url=ad.destination_url or "https://example.com",
            call_to_action=ad.call_to_action,
            image_hash=image_hash,
            video_id=video_id,
            thumbnail_url=thumbnail_url,
        )
        creative_id = creative_result.get("id")
        logger.info(f"Created creative {creative_id} for ad {ad_id}")
        
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

    # ==================== Media Library (adimages / advideos) ====================

    async def list_ad_images(
        self,
        access_token: str,
        ad_account_id: str,
        limit: int = 50,
        after: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        List images in the ad account's image library.

        Returns:
            Dict with "data" (list of image objects) and "paging" (after, next if present).
        """
        params = {
            "access_token": access_token,
            "fields": "hash,name,permalink_url,original_url,url,url_128,width,height,created_time",
            "limit": limit,
        }
        if after:
            params["after"] = after

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{META_GRAPH_API_BASE}/{ad_account_id}/adimages",
                params=params,
            )
            response.raise_for_status()
            result = response.json()
            data = result.get("data", [])
            paging = result.get("paging", {})
            cursors = paging.get("cursors", {})
            return {
                "data": data,
                "paging": {
                    "after": cursors.get("after"),
                    "next": paging.get("next"),
                },
            }

    async def get_ad_images_total_count(
        self,
        access_token: str,
        ad_account_id: str,
    ) -> Optional[int]:
        """
        Return total number of images in the ad account (lightweight summary request).
        Uses Meta's summary=total_count. Returns None if the API does not provide it.
        """
        params = {
            "access_token": access_token,
            "fields": "id",
            "limit": 1,
            "summary": "total_count",
        }
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{META_GRAPH_API_BASE}/{ad_account_id}/adimages",
                params=params,
            )
            response.raise_for_status()
            result = response.json()
            summary = result.get("summary") or {}
            total = summary.get("total_count")
            return int(total) if total is not None else None

    async def get_ad_videos_total_count(
        self,
        access_token: str,
        ad_account_id: str,
    ) -> Optional[int]:
        """
        Return total number of videos in the ad account (lightweight summary request).
        Uses summary=total_count if supported. Returns None if not available.
        """
        params = {
            "access_token": access_token,
            "fields": "id",
            "limit": 1,
            "summary": "total_count",
        }
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{META_GRAPH_API_BASE}/{ad_account_id}/advideos",
                params=params,
            )
            response.raise_for_status()
            result = response.json()
            summary = result.get("summary") or {}
            total = summary.get("total_count")
            return int(total) if total is not None else None

    async def list_ad_videos(
        self,
        access_token: str,
        ad_account_id: str,
        limit: int = 50,
        after: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        List videos in the ad account's video library.

        Returns:
            Dict with "data" (list of video objects) and "paging" (after, next if present).
        """
        params = {
            "access_token": access_token,
            "fields": "id,title,source,thumbnails,created_time,length,picture",
            "limit": limit,
        }
        if after:
            params["after"] = after

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{META_GRAPH_API_BASE}/{ad_account_id}/advideos",
                params=params,
            )
            response.raise_for_status()
            result = response.json()
            data = result.get("data", [])
            paging = result.get("paging", {})
            cursors = paging.get("cursors", {})
            return {
                "data": data,
                "paging": {
                    "after": cursors.get("after"),
                    "next": paging.get("next"),
                },
            }

    @staticmethod
    def _safe_float(value: Any, default: float = 0.0) -> float:
        try:
            if value is None:
                return default
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _safe_int(value: Any, default: int = 0) -> int:
        try:
            if value is None:
                return default
            return int(float(value))
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _parse_meta_datetime(value: Any) -> Optional[datetime]:
        if not value or not isinstance(value, str):
            return None
        candidate = value.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(candidate)
        except ValueError:
            return None

    @staticmethod
    def _extract_action_value(
        items: Any,
        action_types: set[str],
    ) -> float:
        if not isinstance(items, list):
            return 0.0
        for action in items:
            if not isinstance(action, dict):
                continue
            action_type = (action.get("action_type") or "").strip().lower()
            if action_type in action_types:
                return MetaAdsService._safe_float(action.get("value"), 0.0)
        return 0.0

    @staticmethod
    def _extract_action_count(
        items: Any,
        action_types: set[str],
    ) -> int:
        if not isinstance(items, list):
            return 0
        for action in items:
            if not isinstance(action, dict):
                continue
            action_type = (action.get("action_type") or "").strip().lower()
            if action_type in action_types:
                return MetaAdsService._safe_int(action.get("value"), 0)
        return 0

    @staticmethod
    def _extract_creative_media_keys(creative: Dict[str, Any]) -> list[tuple[str, str]]:
        """Return list of (media_key, media_type) from the creative payload."""
        out: list[tuple[str, str]] = []

        def add_key(key: Any, media_type: str) -> None:
            if not key or not isinstance(key, str):
                return
            key = key.strip()
            if not key:
                return
            out.append((key, media_type))

        add_key(creative.get("image_hash"), "image")

        object_story_spec = creative.get("object_story_spec") or {}
        if isinstance(object_story_spec, dict):
            link_data = object_story_spec.get("link_data") or {}
            if isinstance(link_data, dict):
                add_key(link_data.get("image_hash"), "image")
            photo_data = object_story_spec.get("photo_data") or {}
            if isinstance(photo_data, dict):
                add_key(photo_data.get("image_hash"), "image")
            video_data = object_story_spec.get("video_data") or {}
            if isinstance(video_data, dict):
                add_key(video_data.get("video_id"), "video")

        asset_feed_spec = creative.get("asset_feed_spec") or {}
        if isinstance(asset_feed_spec, dict):
            for img in asset_feed_spec.get("images") or []:
                if isinstance(img, dict):
                    add_key(img.get("hash"), "image")
            for vid in asset_feed_spec.get("videos") or []:
                if isinstance(vid, dict):
                    add_key(vid.get("video_id"), "video")

        # De-duplicate but preserve order.
        seen = set()
        deduped: list[tuple[str, str]] = []
        for key, media_type in out:
            token = f"{media_type}:{key}"
            if token in seen:
                continue
            seen.add(token)
            deduped.append((key, media_type))
        return deduped

    @staticmethod
    def _extract_creative_copy(creative: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize best-effort copy fields from creative payload."""
        object_story_spec = creative.get("object_story_spec") or {}
        if not isinstance(object_story_spec, dict):
            object_story_spec = {}
        link_data = object_story_spec.get("link_data") or {}
        if not isinstance(link_data, dict):
            link_data = {}
        video_data = object_story_spec.get("video_data") or {}
        if not isinstance(video_data, dict):
            video_data = {}

        cta_type = None
        cta = video_data.get("call_to_action") or link_data.get("call_to_action") or {}
        if isinstance(cta, dict):
            cta_type = cta.get("type")

        destination_url = (
            video_data.get("link")
            or link_data.get("link")
            or creative.get("link_url")
        )

        return {
            "ad_primary_text": (
                creative.get("body")
                or video_data.get("message")
                or link_data.get("message")
            ),
            "ad_headline": (
                creative.get("title")
                or video_data.get("title")
                or link_data.get("name")
            ),
            "ad_description": (
                creative.get("description")
                or video_data.get("link_description")
                or link_data.get("description")
            ),
            "ad_call_to_action": cta_type,
            "destination_url": destination_url,
        }

    async def list_ads_with_creative_and_insights(
        self,
        access_token: str,
        ad_account_id: str,
        limit: int = 100,
        after: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        List ads with creative + lifetime insights, paginated.
        """
        fields = ",".join(
            [
                "id",
                "name",
                "created_time",
                "creative{id,image_hash,body,title,object_story_spec,asset_feed_spec}",
                # Meta rejects date_preset(lifetime); use maximum for full available range.
                "insights.date_preset(maximum){impressions,clicks,spend,actions,action_values}",
            ]
        )
        params = {
            "access_token": access_token,
            "fields": fields,
            "limit": limit,
        }
        if after:
            params["after"] = after

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(
                f"{META_GRAPH_API_BASE}/{ad_account_id}/ads",
                params=params,
            )
            response.raise_for_status()
            result = response.json()
            data = result.get("data", [])
            paging = result.get("paging", {})
            cursors = paging.get("cursors", {})
            return {
                "data": data,
                "paging": {
                    "after": cursors.get("after"),
                    "next": paging.get("next"),
                },
            }

    async def build_media_performance_lookup(
        self,
        access_token: str,
        ad_account_id: str,
        max_pages: int = 300,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Build a map keyed by Meta media key (image_hash/video_id) with the
        best-performing ad row (highest revenue, then clicks, then recency).
        """
        lookup: Dict[str, Dict[str, Any]] = {}
        cursor = None
        pages = 0

        purchase_value_types = {
            "purchase",
            "omni_purchase",
            "onsite_web_purchase",
            "offsite_conversion.fb_pixel_purchase",
        }
        purchase_count_types = {
            "purchase",
            "omni_purchase",
            "onsite_web_purchase",
            "offsite_conversion.fb_pixel_purchase",
        }

        while pages < max_pages:
            page = await self.list_ads_with_creative_and_insights(
                access_token=access_token,
                ad_account_id=ad_account_id,
                limit=100,
                after=cursor,
            )
            ads = page.get("data", [])
            if not ads:
                break

            for ad in ads:
                creative = ad.get("creative") or {}
                if not isinstance(creative, dict):
                    continue
                media_keys = self._extract_creative_media_keys(creative)
                if not media_keys:
                    continue

                insights_data = (ad.get("insights") or {}).get("data") or []
                insight = insights_data[0] if insights_data else {}

                spend = self._safe_float(insight.get("spend"), 0.0)
                impressions = self._safe_int(insight.get("impressions"), 0)
                clicks = self._safe_int(insight.get("clicks"), 0)
                actions = insight.get("actions") or []
                action_values = insight.get("action_values") or []
                revenue = self._extract_action_value(action_values, purchase_value_types)
                purchases = self._extract_action_count(actions, purchase_count_types)
                ctr = (clicks / impressions) if impressions > 0 else 0.0
                roas = (revenue / spend) if spend > 0 else 0.0

                copy_fields = self._extract_creative_copy(creative)
                started_running_on = self._parse_meta_datetime(ad.get("created_time"))
                base_candidate = {
                    "meta_ad_account_id": ad_account_id,
                    "meta_ad_id": ad.get("id"),
                    "meta_creative_id": creative.get("id"),
                    "revenue": revenue,
                    "spend": spend,
                    "impressions": impressions,
                    "clicks": clicks,
                    "purchases": purchases,
                    "ctr": ctr,
                    "roas": roas,
                    "started_running_on": started_running_on,
                    **copy_fields,
                }

                for media_key, media_type in media_keys:
                    candidate = {
                        **base_candidate,
                        "media_key": media_key,
                        "media_type": media_type,
                    }
                    existing = lookup.get(media_key)
                    if not existing:
                        lookup[media_key] = candidate
                        continue

                    existing_revenue = self._safe_float(existing.get("revenue"), 0.0)
                    existing_clicks = self._safe_int(existing.get("clicks"), 0)
                    existing_started = existing.get("started_running_on")
                    if not isinstance(existing_started, datetime):
                        existing_started = datetime.min
                    candidate_started = candidate.get("started_running_on")
                    if not isinstance(candidate_started, datetime):
                        candidate_started = datetime.min

                    should_replace = (
                        candidate["revenue"] > existing_revenue
                        or (
                            candidate["revenue"] == existing_revenue
                            and candidate["clicks"] > existing_clicks
                        )
                        or (
                            candidate["revenue"] == existing_revenue
                            and candidate["clicks"] == existing_clicks
                            and candidate_started > existing_started
                        )
                    )
                    if should_replace:
                        lookup[media_key] = candidate

            pages += 1
            cursor = (page.get("paging") or {}).get("after")
            if not cursor:
                break

        logger.info(
            "Built media performance lookup for %s: %s keys across %s pages",
            ad_account_id,
            len(lookup),
            pages,
        )
        return lookup
