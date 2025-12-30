"""
Dimension summary generation routes.
"""
import time
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from uuid import UUID
import logging
import os

from app.database import get_db
from app.models import Client, DimensionSummary
from app.services.openai_service import DimensionData, OpenAIService
from app.services.dimension_sampler import DimensionSampler
from app.config import get_settings

router = APIRouter(prefix="/api/dimensions", tags=["dimensions"])
logger = logging.getLogger(__name__)


def get_openai_service(request: Request) -> OpenAIService:
    """Dependency to get OpenAI service from app state"""
    return request.app.state.openai_service


@router.get("/{client_uuid}/{data_source}/{dimension_ref}/summary")
def get_or_generate_summary(
    client_uuid: UUID,
    data_source: str,
    dimension_ref: str,
    force_regenerate: bool = False,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Get existing summary or generate new one.
    Returns cached summary if available, generates on first call.
    
    Query params:
    - force_regenerate: Force generation even if cached (default: false)
    """
    
    # Check cache first (unless force regenerate)
    if not force_regenerate:
        existing = db.query(DimensionSummary).filter(
            DimensionSummary.client_uuid == client_uuid,
            DimensionSummary.data_source == data_source,
            DimensionSummary.dimension_ref == dimension_ref
        ).first()
        
        if existing:
            return {
                "status": "cached",
                "summary": {
                    "id": str(existing.id),
                    "dimension_name": existing.dimension_name,
                    "summary_text": existing.summary_text,
                    "key_insights": existing.key_insights or [],
                    "category_snapshot": existing.category_snapshot or {},
                    "patterns": existing.patterns or "",
                    "sample_size": existing.sample_size,
                    "total_responses": existing.total_responses,
                    "model_used": existing.model_used,
                    "tokens_used": existing.tokens_used,
                    "topic_distribution": existing.topic_distribution
                },
                "generated_at": existing.created_at,
                "from_cache": True
            }
    
    # Generate new summary
    try:
        start_time = time.time()
        
        # Get client for context
        client = db.query(Client).filter(Client.id == client_uuid).first()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        # Extract samples with full analysis
        sampler = DimensionSampler()
        samples, total_count, full_analysis = sampler.extract_with_analysis(
            db=db,
            client_uuid=client_uuid,
            data_source=data_source,
            dimension_ref=dimension_ref,
            sample_size=100
        )
        
        if not samples:
            raise HTTPException(
                status_code=404,
                detail="No data found for this dimension"
            )
        
        # Convert to DimensionData format
        dimension_samples = [
            DimensionData(
                value=s.value,
                sentiment=s.overall_sentiment,
                topics=s.topics
            )
            for s in samples
        ]
        
        # Generate with OpenAI
        dimension_name = samples[0].dimension_name if samples[0].dimension_name else dimension_ref
        
        openai_service = get_openai_service(request)
        result = openai_service.generate_dimension_summary(
            dimension_name=dimension_name,
            dimension_ref=dimension_ref,
            samples=dimension_samples,
            full_analysis=full_analysis,
            client_name=client.name
        )
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Save to database
        if force_regenerate:
            # Delete existing if regenerating
            existing = db.query(DimensionSummary).filter(
                DimensionSummary.client_uuid == client_uuid,
                DimensionSummary.data_source == data_source,
                DimensionSummary.dimension_ref == dimension_ref
            ).first()
            if existing:
                db.delete(existing)
                db.flush()
        
        summary_record = DimensionSummary(
            client_uuid=client_uuid,
            data_source=data_source,
            dimension_ref=dimension_ref,
            dimension_name=dimension_name,
            summary_text=result['summary'],
            key_insights=result['key_insights'],
            category_snapshot=result['category_snapshot'],
            patterns=result['patterns'],
            sample_size=len(samples),
            total_responses=total_count,
            model_used=result['model'],
            tokens_used=result['tokens_used'],
            topic_distribution=full_analysis['category_distribution'],
            generation_duration_ms=duration_ms
        )
        
        db.add(summary_record)
        db.commit()
        db.refresh(summary_record)
        
        return {
            "status": "generated",
            "summary": {
                "id": str(summary_record.id),
                "dimension_name": summary_record.dimension_name,
                "summary_text": summary_record.summary_text,
                "key_insights": summary_record.key_insights or [],
                "category_snapshot": summary_record.category_snapshot or {},
                "patterns": summary_record.patterns or "",
                "sample_size": summary_record.sample_size,
                "total_responses": summary_record.total_responses,
                "model_used": summary_record.model_used,
                "tokens_used": summary_record.tokens_used,
                "topic_distribution": summary_record.topic_distribution
            },
            "generated_at": summary_record.created_at,
            "duration_ms": duration_ms,
            "from_cache": False
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate summary: {str(e)}"
        )


# Database Management Endpoints

