"""
Schemas for lead-gen VoC founder/visualization endpoints.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel
from uuid import UUID


class LeadgenVocRunSummary(BaseModel):
    run_id: str
    company_name: str
    company_domain: str
    work_email: str
    review_count: int
    coding_enabled: bool
    coding_status: Optional[str] = None
    generated_at: Optional[datetime] = None
    created_at: datetime
    converted_at: Optional[datetime] = None
    converted_client_uuid: Optional[UUID] = None


class LeadgenVocRunListResponse(BaseModel):
    items: List[LeadgenVocRunSummary]


class LeadgenVocProcessedJsonResponse(BaseModel):
    run_id: str
    payload: Dict[str, Any]


class LeadgenVocRowsResponse(BaseModel):
    run_id: str
    rows: List[Dict[str, Any]]
