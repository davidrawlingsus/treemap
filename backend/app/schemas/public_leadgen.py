"""
Schemas for public lead generation endpoints.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TrustpilotLeadgenRequest(BaseModel):
    work_email: str = Field(..., description="Work email used to infer company domain")
    company_url: Optional[str] = Field(default=None, description="Optional company URL override")
    company_name: Optional[str] = Field(default=None, description="Optional company name override")
    max_reviews: int = Field(default=50, ge=1, le=250, description="Maximum number of Trustpilot reviews to fetch")
    include_debug_data: bool = Field(
        default=False,
        description="Include intermediate normalization/debug fields in response payload",
    )
    resume_run_id: Optional[str] = Field(
        default=None,
        description="Optional existing run_id to resume a partially completed coding chain run",
    )


class TrustpilotLeadgenResponse(BaseModel):
    file_name: str
    generated_at: datetime
    company_domain: str
    company_url: str
    company_name: str
    run_id: Optional[str] = None
    client_id: Optional[str] = None
    review_count: int
    payload: Dict[str, Any]


class TrustpilotLeadgenErrorResponse(BaseModel):
    detail: str
    step: Optional[str] = None
