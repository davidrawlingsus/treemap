"""
Meta Ads schemas for OAuth and API operations.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID


# ==================== OAuth Schemas ====================

class MetaOAuthInitResponse(BaseModel):
    """Response for OAuth init endpoint."""
    oauth_url: str = Field(..., description="URL to redirect user for Meta OAuth")
    state: str = Field(..., description="State token for CSRF protection")


class MetaTokenStatusResponse(BaseModel):
    """Response for checking Meta token status."""
    has_token: bool = Field(..., description="Whether client has a valid Meta token")
    is_expired: bool = Field(False, description="Whether the token is expired")
    meta_user_name: Optional[str] = Field(None, description="Name of connected Meta user")
    default_ad_account_id: Optional[str] = Field(None, description="Default ad account ID")
    default_ad_account_name: Optional[str] = Field(None, description="Default ad account name")
    expires_at: Optional[datetime] = Field(None, description="Token expiration time")


class SetDefaultAdAccountRequest(BaseModel):
    """Request to set default ad account for a client."""
    client_id: UUID
    ad_account_id: str = Field(..., description="Meta ad account ID (e.g., act_123456)")
    ad_account_name: Optional[str] = Field(None, description="Ad account name for display")


# ==================== Ad Account Schemas ====================

class MetaAdAccount(BaseModel):
    """Meta ad account info."""
    id: str = Field(..., description="Ad account ID (e.g., act_123456)")
    name: str = Field(..., description="Ad account name")
    account_status: int = Field(..., description="Account status (1=active, 2=disabled, etc)")
    currency: Optional[str] = Field(None, description="Account currency")
    timezone_name: Optional[str] = Field(None, description="Account timezone")


class MetaAdAccountListResponse(BaseModel):
    """Response for listing ad accounts."""
    items: List[MetaAdAccount]
    total: int


# ==================== Campaign Schemas ====================

class MetaCampaign(BaseModel):
    """Meta campaign info."""
    id: str = Field(..., description="Campaign ID")
    name: str = Field(..., description="Campaign name")
    status: str = Field(..., description="Campaign status (ACTIVE, PAUSED, etc)")
    objective: Optional[str] = Field(None, description="Campaign objective")
    created_time: Optional[datetime] = Field(None, description="When campaign was created")


class MetaCampaignListResponse(BaseModel):
    """Response for listing campaigns."""
    items: List[MetaCampaign]
    total: int


class CreateCampaignRequest(BaseModel):
    """Request to create a new campaign."""
    ad_account_id: str = Field(..., description="Ad account ID to create campaign in")
    name: str = Field(..., description="Campaign name")
    objective: str = Field("OUTCOME_TRAFFIC", description="Campaign objective")
    status: str = Field("PAUSED", description="Initial campaign status")
    special_ad_categories: List[str] = Field(default_factory=list, description="Special ad categories if applicable")


class CreateCampaignResponse(BaseModel):
    """Response for campaign creation."""
    id: str = Field(..., description="Created campaign ID")
    name: str


# ==================== AdSet Schemas ====================

class MetaAdSet(BaseModel):
    """Meta adset info."""
    id: str = Field(..., description="AdSet ID")
    name: str = Field(..., description="AdSet name")
    status: str = Field(..., description="AdSet status")
    campaign_id: str = Field(..., description="Parent campaign ID")
    daily_budget: Optional[str] = Field(None, description="Daily budget in cents")
    lifetime_budget: Optional[str] = Field(None, description="Lifetime budget in cents")


class MetaAdSetListResponse(BaseModel):
    """Response for listing adsets."""
    items: List[MetaAdSet]
    total: int


class CreateAdSetRequest(BaseModel):
    """Request to create a new adset."""
    campaign_id: str = Field(..., description="Campaign ID to create adset in")
    name: str = Field(..., description="AdSet name")
    daily_budget: Optional[int] = Field(None, description="Daily budget in cents (min 100 = $1)")
    lifetime_budget: Optional[int] = Field(None, description="Lifetime budget in cents")
    billing_event: str = Field("IMPRESSIONS", description="Billing event type")
    optimization_goal: str = Field("LINK_CLICKS", description="Optimization goal")
    status: str = Field("PAUSED", description="Initial adset status")
    # Targeting is complex - using basic defaults
    targeting: Optional[dict] = Field(None, description="Targeting specification")


class CreateAdSetResponse(BaseModel):
    """Response for adset creation."""
    id: str = Field(..., description="Created adset ID")
    name: str


# ==================== Ad Publishing Schemas ====================

class PublishAdRequest(BaseModel):
    """Request to publish an ad to Meta."""
    ad_id: UUID = Field(..., description="Local Facebook ad ID to publish")
    adset_id: str = Field(..., description="Meta adset ID to publish to")
    ad_account_id: str = Field(..., description="Meta ad account ID")
    name: Optional[str] = Field(None, description="Optional name for the ad in Meta")
    status: str = Field("PAUSED", description="Initial ad status in Meta")


class PublishAdResponse(BaseModel):
    """Response for ad publishing."""
    success: bool
    meta_ad_id: Optional[str] = Field(None, description="Created Meta ad ID")
    meta_creative_id: Optional[str] = Field(None, description="Created creative ID")
    error: Optional[str] = Field(None, description="Error message if failed")
