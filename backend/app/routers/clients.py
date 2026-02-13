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
from app.models import Client, DataSource, Insight, Membership, User, Prompt, Action, PromptClient, ContextMenuGroup
from app.schemas import (
    ClientCreate,
    ClientResponse,
    ClientLogoUpdate,
    ClientSettingsUpdate,
    DataSourceResponse,
    InsightCreate,
    InsightUpdate,
    InsightResponse,
    InsightListResponse,
    InsightOrigin,
    PromptMenuItem,
    ClientPromptExecuteRequest,
    ClientPromptsGroupedItem,
)
from app.schemas.action import ClientActionResponse, ActionResponse
from app.auth import get_current_user, get_current_active_founder
from app.authorization import verify_client_access

router = APIRouter(prefix="/api/clients", tags=["clients"])
logger = logging.getLogger(__name__)


def get_llm_service(request: Request):
    """Dependency to get LLM service from app state"""
    return request.app.state.llm_service


def parse_application_to_jsonb(application_str: Optional[str]) -> Optional[List[str]]:
    """
    Parse comma-separated application string into a list for JSONB storage.
    
    Args:
        application_str: Comma-separated string (e.g., "homepage, pdp, google ad")
    
    Returns:
        List of trimmed application values, or None if input is None/empty
    """
    if not application_str or not application_str.strip():
        return None
    
    # Split by comma, trim whitespace, filter empty strings
    applications = [app.strip() for app in application_str.split(',') if app.strip()]
    return applications if applications else None


@router.get("", response_model=List[ClientResponse])
def list_clients(db: Session = Depends(get_db)):
    """List all clients"""
    clients = db.query(Client).order_by(Client.name).all()
    return clients


@router.post("", response_model=ClientResponse)
def create_client(
    client: ClientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Create a new client (founder only). Use ad_library_only=True for diagnosis-only brands."""
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


@router.put("/{client_id}/logo", response_model=ClientResponse)
def update_client_logo(
    client_id: UUID,
    logo_data: ClientLogoUpdate,
    db: Session = Depends(get_db)
):
    """Update client logo URL and header color"""
    client = db.query(Client).filter(Client.id == client_id).first()
    
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    client.logo_url = logo_data.logo_url
    client.header_color = logo_data.header_color
    
    db.commit()
    db.refresh(client)
    
    return client


@router.put("/{client_id}/settings", response_model=ClientResponse)
def update_client_settings(
    client_id: UUID,
    settings_data: ClientSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update client settings (logo, business context, tone of voice)"""
    # Verify client access
    verify_client_access(client_id, current_user, db)
    
    client = db.query(Client).filter(Client.id == client_id).first()
    
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Update only provided fields
    if settings_data.client_url is not None:
        client.client_url = settings_data.client_url
    if settings_data.logo_url is not None:
        client.logo_url = settings_data.logo_url
    if settings_data.header_color is not None:
        client.header_color = settings_data.header_color
    if settings_data.business_summary is not None:
        client.business_summary = settings_data.business_summary
    if settings_data.tone_of_voice is not None:
        client.tone_of_voice = settings_data.tone_of_voice
    
    db.commit()
    db.refresh(client)
    
    logger.info(f"Updated settings for client {client_id}")
    return client


@router.post("/{client_id}/generate-tone-of-voice")
def generate_tone_of_voice(
    client_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    llm_service = Depends(get_llm_service),
):
    """
    Generate a tone of voice guide for a client by:
    1. Crawling their brand website
    2. Combining website copy with business context
    3. Using LLM to generate a comprehensive tone guide
    4. Storing the result in the client's tone_of_voice field
    """
    from app.services.web_crawler_service import WebCrawlerService
    
    # Verify client access
    verify_client_access(client_id, current_user, db)
    
    # Get client
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Check if client has a URL
    if not client.client_url:
        raise HTTPException(
            status_code=400, 
            detail="Please set a brand website URL in Settings before generating tone of voice"
        )
    
    # Get the tone_of_voice prompt from prompts table
    prompt = db.query(Prompt).filter(
        Prompt.prompt_purpose == "tone_of_voice",
        Prompt.status == "live"
    ).order_by(Prompt.version.desc()).first()
    
    if not prompt:
        raise HTTPException(
            status_code=404, 
            detail="Tone of voice prompt not configured. Please create a prompt with purpose 'tone_of_voice' in Prompt Engineering."
        )
    
    try:
        # Crawl the brand website
        logger.info(f"Crawling website for client {client_id}: {client.client_url}")
        crawler = WebCrawlerService()
        crawl_result = crawler.crawl_brand_pages(client.client_url, max_pages=4)
        
        if not crawl_result['combined_copy']:
            raise HTTPException(
                status_code=400,
                detail=f"Could not extract content from website. Errors: {', '.join(crawl_result['errors'])}"
            )
        
        # Build user message with website copy + business context
        user_message_parts = []
        
        # Add brand name
        user_message_parts.append(f"Brand Name: {client.name}")
        
        # Add website copy
        user_message_parts.append(f"\n\n=== Website Copy ===\n{crawl_result['combined_copy']}")
        
        # Add business context if available
        if client.business_summary:
            user_message_parts.append(f"\n\n=== Business Context ===\n{client.business_summary}")
        
        user_message = '\n'.join(user_message_parts)
        
        logger.info(
            f"Generating tone of voice for client {client_id} "
            f"with model: {prompt.llm_model}, "
            f"pages crawled: {len(crawl_result['pages_crawled'])}, "
            f"user_message length: {len(user_message)}"
        )
        
        # Execute LLM prompt
        result = llm_service.execute_prompt(
            system_message=prompt.system_message,
            user_message=user_message,
            model=prompt.llm_model
        )
        
        generated_tone = result.get('content', '')
        
        if not generated_tone:
            raise HTTPException(status_code=500, detail="LLM returned empty response")
        
        # Save the generated tone of voice to the client
        client.tone_of_voice = generated_tone
        db.commit()
        db.refresh(client)
        
        logger.info(f"Generated and saved tone of voice for client {client_id}, length: {len(generated_tone)}")
        
        return {
            "tone_of_voice": generated_tone,
            "pages_crawled": crawl_result['pages_crawled'],
            "tokens_used": result.get('tokens_used'),
            "model": result.get('model')
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating tone of voice: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


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
    application: Optional[str] = None,  # Filter by application (e.g., "homepage", "pdp")
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
    
    if application:
        # Filter insights where the application JSONB array contains the specified application
        query = query.filter(
            text(f"application @> '\"{application}\"'::jsonb")
        )
    
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
        
        # Parse application from comma-separated string to JSONB array
        application_jsonb = parse_application_to_jsonb(insight_data.application)
        
        insight = Insight(
            client_id=client_id,
            name=insight_data.name,
            type=insight_data.type,
            application=application_jsonb,
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
        # Parse application from comma-separated string to JSONB array
        insight.application = parse_application_to_jsonb(insight_data.application)
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


@router.get("/{client_id}/prompts", response_model=List[ClientPromptsGroupedItem])
def list_client_prompts(
    client_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all client-facing prompts available for a client, grouped by context menu group."""
    # Verify client access
    verify_client_access(client_id, current_user, db)
    
    from sqlalchemy import or_
    
    # Get prompts with client_facing=True that are either:
    # 1. Available to all clients (all_clients=True), OR
    # 2. Specifically associated with this client via PromptClient
    prompts = db.query(Prompt).outerjoin(
        PromptClient, Prompt.id == PromptClient.prompt_id
    ).filter(
        Prompt.client_facing == True,
        or_(
            Prompt.all_clients == True,
            PromptClient.client_id == client_id
        )
    ).order_by(Prompt.name).all()
    
    # Get AI Expert group for prompts with null context_menu_group_id (backward compat)
    ai_expert_group = db.query(ContextMenuGroup).filter(ContextMenuGroup.label == "AI Expert").first()
    
    # Group prompts by context_menu_group_id (use AI Expert for null)
    groups_dict = {}
    for p in prompts:
        group_id = p.context_menu_group_id or (ai_expert_group.id if ai_expert_group else None)
        if group_id is None:
            continue  # Skip if no AI Expert group (shouldn't happen after migration)
        if group_id not in groups_dict:
            g = db.query(ContextMenuGroup).filter(ContextMenuGroup.id == group_id).first()
            if g:
                groups_dict[group_id] = {
                    "id": g.id,
                    "label": g.label,
                    "sort_order": g.sort_order,
                    "prompts": [],
                }
        if group_id in groups_dict:
            groups_dict[group_id]["prompts"].append(PromptMenuItem(id=p.id, name=p.name))
    
    # Sort by sort_order, then by label
    sorted_groups = sorted(groups_dict.values(), key=lambda x: (x["sort_order"], x["label"]))
    return [ClientPromptsGroupedItem(**g) for g in sorted_groups]


@router.get("/{client_id}/prompts/by-purpose", response_model=PromptMenuItem)
def get_client_prompt_by_purpose(
    client_id: UUID,
    purpose: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the first live prompt with the given prompt_purpose. Purpose-only prompts (e.g. ad_iterate)
    are found here without needing client_facing or all_clients - they don't appear in context menus."""
    from sqlalchemy import func

    verify_client_access(client_id, current_user, db)

    purpose_lower = purpose.lower().strip()

    # By-purpose lookup: purpose-only prompts (e.g. ad_iterate) are found here without needing
    # client_facing (context menu) or all_clients/client assignment. verify_client_access ensures
    # the user has access to the client.
    prompt = (
        db.query(Prompt)
        .filter(
            func.lower(Prompt.prompt_purpose) == purpose_lower,
            Prompt.status == "live",
        )
        .order_by(Prompt.name)
        .first()
    )

    if not prompt:
        raise HTTPException(
            status_code=404,
            detail=f"No live prompt with purpose '{purpose}' configured. In Prompt Engineering, ensure: prompt_purpose='{purpose}' and status='live'.",
        )

    return PromptMenuItem(id=prompt.id, name=prompt.name)


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
        
        if client.tone_of_voice:
            user_message_parts.append(f"\n\nBrand Tone of Voice:\n{client.tone_of_voice}")
        
        # Add voc_data as JSON
        voc_json = json.dumps(payload.voc_data, indent=2)
        user_message_parts.append(f"\n\nVoice of Customer Data:\n{voc_json}")
        
        # Append helper prompts if linked to this system prompt
        from app.models import PromptHelperPrompt
        helper_links = db.query(PromptHelperPrompt).filter(
            PromptHelperPrompt.system_prompt_id == prompt.id
        ).all()
        
        if helper_links:
            helper_messages = []
            for link in helper_links:
                helper_prompt = db.query(Prompt).filter(Prompt.id == link.helper_prompt_id).first()
                if helper_prompt and helper_prompt.prompt_message:
                    helper_messages.append(helper_prompt.prompt_message)
            
            if helper_messages:
                user_message_parts.append("\n\n" + "\n\n".join(helper_messages))
        
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


@router.delete("/{client_id}/actions/{action_id}")
def delete_action(
    client_id: UUID,
    action_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete an action"""
    # Verify client access
    verify_client_access(client_id, current_user, db)
    
    action = db.query(Action).filter(
        Action.id == action_id,
        Action.client_id == client_id
    ).first()
    
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    
    db.delete(action)
    db.commit()
    
    return {"message": "Action deleted successfully"}

