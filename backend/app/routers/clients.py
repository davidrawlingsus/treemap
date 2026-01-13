"""
Client and insight management routes.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import text
from uuid import UUID
from typing import List, Optional
import logging
import json

from app.database import get_db
from app.models import Client, DataSource, Insight, Membership, User, Prompt, Action
from app.schemas import (
    ClientCreate,
    ClientResponse,
    DataSourceResponse,
    InsightCreate,
    InsightUpdate,
    InsightResponse,
    InsightListResponse,
    InsightOrigin,
    PromptMenuItem,
    ClientPromptExecuteRequest,
)
from app.schemas.action import ClientActionResponse, ActionResponse
from app.auth import get_current_user
from app.authorization import verify_client_access

router = APIRouter(prefix="/api/clients", tags=["clients"])
logger = logging.getLogger(__name__)


@router.get("", response_model=List[ClientResponse])
def list_clients(db: Session = Depends(get_db)):
    """List all clients"""
    clients = db.query(Client).order_by(Client.name).all()
    return clients


@router.post("", response_model=ClientResponse)
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


@router.get("/{client_id}", response_model=ClientResponse)
def get_client(client_id: UUID, db: Session = Depends(get_db)):
    """Get a specific client"""
    client = db.query(Client).filter(Client.id == client_id).first()
    
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    return client


@router.get("/{client_id}/sources", response_model=List[DataSourceResponse])
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


@router.get("/{client_id}/insights", response_model=InsightListResponse)
def list_insights(
    client_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    origin_type: Optional[str] = None,
    type: Optional[str] = None,
    project_name: Optional[str] = None,
    data_source: Optional[str] = None,
    dimension_ref: Optional[str] = None,
    category: Optional[str] = None,
    topic_label: Optional[str] = None,
    process_voc_id: Optional[int] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    page: int = 1,
    page_size: int = 50,
):
    """List insights for a client with filtering and sorting"""
    # Verify client access
    verify_client_access(client_id, current_user, db)
    
    # Build base query
    query = db.query(Insight).filter(Insight.client_id == client_id)
    
    # Apply filters using JSONB operators
    # For array filtering, we check if any element in the origins array matches
    if origin_type:
        query = query.filter(
            text(f"EXISTS (SELECT 1 FROM jsonb_array_elements(insights.origins) AS origin WHERE (origin->>'origin_type') = '{origin_type}')")
        )
    
    if type:
        query = query.filter(Insight.type == type)
    
    if project_name:
        query = query.filter(
            text(f"EXISTS (SELECT 1 FROM jsonb_array_elements(insights.origins) AS origin WHERE (origin->>'project_name') = '{project_name}')")
        )
    
    if data_source:
        query = query.filter(
            text(f"EXISTS (SELECT 1 FROM jsonb_array_elements(insights.origins) AS origin WHERE (origin->>'data_source') = '{data_source}')")
        )
    
    if dimension_ref:
        query = query.filter(
            text(f"EXISTS (SELECT 1 FROM jsonb_array_elements(insights.origins) AS origin WHERE (origin->>'dimension_ref') = '{dimension_ref}')")
        )
    
    if category:
        query = query.filter(
            text(f"EXISTS (SELECT 1 FROM jsonb_array_elements(insights.origins) AS origin WHERE (origin->>'category') = '{category}')")
        )
    
    if topic_label:
        query = query.filter(
            text(f"EXISTS (SELECT 1 FROM jsonb_array_elements(insights.origins) AS origin WHERE (origin->>'topic_label') = '{topic_label}')")
        )
    
    if process_voc_id is not None:
        query = query.filter(
            text(f"EXISTS (SELECT 1 FROM jsonb_array_elements(insights.origins) AS origin WHERE (origin->>'process_voc_id')::int = {process_voc_id})")
        )
    
    # Get total count
    total = query.count()
    
    # Apply sorting
    if sort_order.lower() == "asc":
        if sort_by == "name":
            query = query.order_by(Insight.name.asc())
        elif sort_by == "type":
            query = query.order_by(Insight.type.asc())
        elif sort_by == "created_at":
            query = query.order_by(Insight.created_at.asc())
        elif sort_by == "updated_at":
            query = query.order_by(Insight.updated_at.asc())
        else:
            query = query.order_by(Insight.created_at.asc())
    else:
        if sort_by == "name":
            query = query.order_by(Insight.name.desc())
        elif sort_by == "type":
            query = query.order_by(Insight.type.desc())
        elif sort_by == "created_at":
            query = query.order_by(Insight.created_at.desc())
        elif sort_by == "updated_at":
            query = query.order_by(Insight.updated_at.desc())
        else:
            query = query.order_by(Insight.created_at.desc())
    
    # Apply pagination
    offset = (page - 1) * page_size
    insights = query.offset(offset).limit(page_size).all()
    
    # Calculate total pages
    total_pages = (total + page_size - 1) // page_size
    
    return InsightListResponse(
        items=[InsightResponse.from_orm(insight) for insight in insights],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post("/{client_id}/insights", response_model=InsightResponse)
def create_insight(
    client_id: UUID,
    insight_data: InsightCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new insight"""
    try:
        # Verify client access
        verify_client_access(client_id, current_user, db)
        
        # Convert origins to JSONB format
        origins_json = [origin.model_dump() for origin in insight_data.origins]
        
        insight = Insight(
            client_id=client_id,
            name=insight_data.name,
            type=insight_data.type,
            application=insight_data.application,
            description=insight_data.description,
            notes=insight_data.notes,
            status=insight_data.status or 'Not Started',
            origins=origins_json,
            verbatims=insight_data.verbatims or [],
            meta_data=insight_data.metadata or {},
            voc_json=insight_data.voc_json,
            created_by=current_user.id,
        )
        
        db.add(insight)
        db.commit()
        db.refresh(insight)
        
        return InsightResponse.from_orm(insight)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating insight: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create insight: {str(e)}")


@router.get("/{client_id}/insights/{insight_id}", response_model=InsightResponse)
def get_insight(
    client_id: UUID,
    insight_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific insight"""
    # Verify client access
    verify_client_access(client_id, current_user, db)
    
    insight = db.query(Insight).filter(
        Insight.id == insight_id,
        Insight.client_id == client_id
    ).first()
    
    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")
    
    return InsightResponse.from_orm(insight)


@router.put("/{client_id}/insights/{insight_id}", response_model=InsightResponse)
def update_insight(
    client_id: UUID,
    insight_id: UUID,
    insight_data: InsightUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update an existing insight"""
    # Verify client access
    verify_client_access(client_id, current_user, db)
    
    insight = db.query(Insight).filter(
        Insight.id == insight_id,
        Insight.client_id == client_id
    ).first()
    
    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")
    
    # Update fields
    if insight_data.name is not None:
        insight.name = insight_data.name
    if insight_data.type is not None:
        insight.type = insight_data.type
    if insight_data.application is not None:
        insight.application = insight_data.application
    if insight_data.description is not None:
        insight.description = insight_data.description
    if insight_data.notes is not None:
        logger.info(f"Updating notes for insight {insight_id}, length: {len(insight_data.notes)}")
        logger.info(f"Notes content (first 500 chars): {insight_data.notes[:500]}")
        logger.info(f"Notes content (last 100 chars): {insight_data.notes[-100:]}")
        # Check if notes contains img tag
        if '<img' in insight_data.notes:
            import re
            img_matches = re.findall(r'<img[^>]+src="([^"]+)"', insight_data.notes)
            logger.info(f"Found {len(img_matches)} image(s) in notes")
            for i, img_src in enumerate(img_matches):
                logger.info(f"Image {i+1} src: {img_src}")
                logger.info(f"Image {i+1} src length: {len(img_src)}")
                if not img_src.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                    logger.warning(f"Image {i+1} src does not end with image extension - may be truncated!")
        insight.notes = insight_data.notes
    if insight_data.status is not None:
        insight.status = insight_data.status
    if insight_data.verbatims is not None:
        insight.verbatims = insight_data.verbatims
    if insight_data.metadata is not None:
        insight.meta_data = insight_data.metadata
    
    # Handle origins - if add_origin is provided, append; if origins is provided, replace
    if insight_data.add_origin is not None:
        current_origins = insight.origins if insight.origins else []
        current_origins.append(insight_data.add_origin.model_dump())
        insight.origins = current_origins
    elif insight_data.origins is not None:
        insight.origins = [origin.model_dump() for origin in insight_data.origins]
    
    db.commit()
    db.refresh(insight)
    
    return InsightResponse.from_orm(insight)


@router.delete("/{client_id}/insights/{insight_id}")
def delete_insight(
    client_id: UUID,
    insight_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete an insight"""
    # Verify client access
    verify_client_access(client_id, current_user, db)
    
    insight = db.query(Insight).filter(
        Insight.id == insight_id,
        Insight.client_id == client_id
    ).first()
    
    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")
    
    db.delete(insight)
    db.commit()
    
    return {"message": "Insight deleted successfully"}


@router.post("/{client_id}/insights/{insight_id}/origins", response_model=InsightResponse)
def add_insight_origin(
    client_id: UUID,
    insight_id: UUID,
    origin: InsightOrigin,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a new origin to an existing insight"""
    # Verify client access
    verify_client_access(client_id, current_user, db)
    
    insight = db.query(Insight).filter(
        Insight.id == insight_id,
        Insight.client_id == client_id
    ).first()
    
    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")
    
    # Append new origin
    current_origins = insight.origins if insight.origins else []
    current_origins.append(origin.model_dump())
    insight.origins = current_origins
    
    db.commit()
    db.refresh(insight)
    
    return InsightResponse.from_orm(insight)


def get_llm_service(request: Request):
    """Dependency to get LLM service from app state"""
    return request.app.state.llm_service


@router.get("/{client_id}/prompts", response_model=List[PromptMenuItem])
def list_client_prompts(
    client_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all live prompts available for a client"""
    # Verify client access
    verify_client_access(client_id, current_user, db)
    
    # Get all prompts with status='live'
    prompts = db.query(Prompt).filter(
        Prompt.status == 'live'
    ).order_by(Prompt.prompt_purpose).all()
    
    # Return minimal info (id and purpose) for menu display
    return [PromptMenuItem(id=p.id, purpose=p.prompt_purpose) for p in prompts]


@router.post("/{client_id}/prompts/{prompt_id}/execute")
def execute_client_prompt(
    client_id: UUID,
    prompt_id: UUID,
    payload: ClientPromptExecuteRequest,
    request: Request,
    stream: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    llm_service = Depends(get_llm_service),
):
    """
    Execute a prompt for a client with streaming support.
    
    Automatically combines client's business_summary with voc_data to construct user message.
    """
    # Verify client access
    verify_client_access(client_id, current_user, db)
    
    # Get prompt
    prompt = db.query(Prompt).filter(Prompt.id == prompt_id).first()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    
    # Verify prompt is live
    if prompt.status != 'live':
        raise HTTPException(status_code=403, detail="Only live prompts can be executed")
    
    # Get client to access business_summary
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    try:
        # Construct user message by combining business_summary and voc_data
        user_message_parts = []
        
        if client.business_summary:
            user_message_parts.append(f"Business Context:\n{client.business_summary}")
        
        # Add voc_data as JSON
        voc_json = json.dumps(payload.voc_data, indent=2)
        user_message_parts.append(f"\n\nVoice of Customer Data:\n{voc_json}")
        
        user_message = "\n".join(user_message_parts)
        
        logger.info(
            f"Executing prompt {prompt_id} for client {client_id} "
            f"with model: {prompt.llm_model}, "
            f"user_message length: {len(user_message)}, "
            f"stream: {stream}"
        )
        
        if stream:
            # Store values before creating generator (to avoid session issues)
            prompt_id_value = prompt.id
            prompt_system_message = prompt.system_message
            prompt_llm_model = prompt.llm_model
            user_message_value = user_message
            client_id_value = client_id
            # Capture origin and voc_json from payload
            origin_value = payload.origin if payload.origin else None
            voc_json_value = payload.voc_data  # Store the actual JSON object, not stringified
            
            # Streaming mode - return SSE response
            def generate_stream():
                accumulated_content = ""
                final_metadata = None
                
                # Create separate database session for saving action
                from app.database import SessionLocal
                save_db = SessionLocal()
                
                try:
                    # Stream chunks from LLM service
                    for chunk, metadata in llm_service.execute_prompt_stream(
                        system_message=prompt_system_message,
                        user_message=user_message_value,
                        model=prompt_llm_model
                    ):
                        if metadata is None:
                            # Content chunk
                            if chunk:
                                accumulated_content += chunk
                                # Send SSE message with chunk
                                message = json.dumps({
                                    "type": "chunk",
                                    "content": chunk
                                })
                                yield f"data: {message}\n\n"
                        else:
                            # Final metadata chunk
                            final_metadata = metadata
                            # Send final message
                            message = json.dumps({
                                "type": "done",
                                "tokens_used": metadata.get("tokens_used"),
                                "model": metadata.get("model"),
                                "content": metadata.get("content", accumulated_content)
                            })
                            yield f"data: {message}\n\n"
                    
                    # Save the result to database after streaming completes
                    if final_metadata:
                        try:
                            prompt_text_sent = f"System: {prompt_system_message}\n\nUser: {user_message_value}"
                            
                            # Get content from final_metadata or fallback to accumulated_content
                            final_content = final_metadata.get("content", accumulated_content)
                            
                            result = {
                                "content": final_content,
                                "tokens_used": final_metadata.get("tokens_used"),
                                "model": final_metadata.get("model", prompt_llm_model)
                            }
                            
                            action = Action(
                                prompt_id=prompt_id_value,
                                client_id=client_id_value,
                                prompt_text_sent=prompt_text_sent,
                                actions=result,
                                insight_ids=[],
                                origin=origin_value,
                                voc_json=voc_json_value
                            )
                            save_db.add(action)
                            save_db.commit()
                            logger.info(f"Client prompt execution saved to database. Content length: {len(result.get('content', ''))}")
                        except Exception as save_error:
                            logger.error(f"Error saving client prompt execution to database: {save_error}", exc_info=True)
                            save_db.rollback()
                        finally:
                            save_db.close()
                    
                except Exception as stream_error:
                    logger.error(f"Error during streaming: {stream_error}", exc_info=True)
                    error_message = json.dumps({
                        "type": "error",
                        "error": str(stream_error)
                    })
                    yield f"data: {error_message}\n\n"
                    try:
                        save_db.rollback()
                    except:
                        pass
                    finally:
                        save_db.close()
            
            return StreamingResponse(
                generate_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"
                }
            )
        else:
            # Non-streaming mode (not used by client, but included for completeness)
            result = llm_service.execute_prompt(
                system_message=prompt.system_message,
                user_message=user_message,
                model=prompt.llm_model
            )
            return result
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing prompt: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{client_id}/actions", response_model=List[ClientActionResponse])
def list_client_actions(
    client_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all AI expert outputs (actions) for a client"""
    # Verify client access
    verify_client_access(client_id, current_user, db)
    
    # Get all actions for this client, ordered by created_at descending (newest first)
    actions = db.query(Action).options(
        joinedload(Action.prompt)
    ).filter(
        Action.client_id == client_id
    ).order_by(Action.created_at.desc()).all()
    
    # Convert to response format
    return [ClientActionResponse.from_action_with_prompt(action) for action in actions]


@router.get("/{client_id}/actions/{action_id}", response_model=ActionResponse)
def get_client_action(
    client_id: UUID,
    action_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific action by ID for a client"""
    # Verify client access
    verify_client_access(client_id, current_user, db)
    
    # Get action with prompt relationship loaded
    action = db.query(Action).options(
        joinedload(Action.prompt)
    ).filter(
        Action.id == action_id,
        Action.client_id == client_id
    ).first()
    
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    
    # Use the existing ActionResponse.from_orm_with_prompt method
    return ActionResponse.from_orm_with_prompt(action)

