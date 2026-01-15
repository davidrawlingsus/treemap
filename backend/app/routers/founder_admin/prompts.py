"""
Prompt management routes for founder admin.
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi import Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from uuid import UUID
from typing import List, Optional
from pydantic import BaseModel, Field
import json
import logging

from app.database import get_db
from app.models import User, Prompt, Client, Action, PromptHelperPrompt
from app.schemas import PromptResponse, PromptCreate, PromptUpdate, ActionResponse, PromptHelperPromptResponse
from app.auth import get_current_active_founder
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


def get_llm_service(request: Request) -> LLMService:
    """Dependency to get LLM service from app state"""
    return request.app.state.llm_service


def get_or_create_prompt_engineering_client(db: Session) -> Client:
    """Get or create the special 'Prompt Engineering' client for tracking prompt executions."""
    PROMPT_ENGINEERING_SLUG = "prompt-engineering"
    
    client = db.query(Client).filter(Client.slug == PROMPT_ENGINEERING_SLUG).first()
    
    if not client:
        # Create the prompt engineering client
        client = Client(
            name="Prompt Engineering",
            slug=PROMPT_ENGINEERING_SLUG,
            is_active=True,
            settings={}
        )
        db.add(client)
        db.commit()
        db.refresh(client)
    
    return client


class PromptExecuteRequest(BaseModel):
    """Request schema for executing a prompt"""
    user_message: str = Field(..., description="User message to send with the system prompt")

router = APIRouter()


@router.get(
    "/api/founder/prompts",
    response_model=List[PromptResponse],
)
def list_prompts_for_founder(
    status: Optional[str] = None,
    prompt_purpose: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """List all prompts with optional filtering by status and purpose."""
    query = db.query(Prompt)
    
    if status:
        query = query.filter(Prompt.status == status)
    if prompt_purpose:
        query = query.filter(Prompt.prompt_purpose == prompt_purpose)
    
    prompts = query.order_by(Prompt.name, Prompt.version.desc()).all()
    return prompts


@router.get(
    "/api/founder/prompts/helpers",
    response_model=List[PromptResponse],
)
def list_helper_prompts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """List all helper prompts."""
    prompts = db.query(Prompt).filter(Prompt.prompt_type == 'helper').order_by(Prompt.name, Prompt.version.desc()).all()
    return prompts


@router.get(
    "/api/founder/prompts/{prompt_id}",
    response_model=PromptResponse,
)
def get_prompt_for_founder(
    prompt_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Get a single prompt by ID."""
    prompt = db.query(Prompt).filter(Prompt.id == prompt_id).first()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found.")
    return prompt


@router.post(
    "/api/founder/prompts",
    response_model=PromptResponse,
    status_code=201,
)
def create_prompt_for_founder(
    payload: PromptCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Create a new prompt."""
    logger.info(f"Creating prompt: name={payload.name}, version={payload.version}, type={payload.prompt_type}")
    
    # Validation based on prompt type
    if payload.prompt_type == 'system':
        if not payload.system_message:
            raise HTTPException(
                status_code=400,
                detail="System prompts require a system_message."
            )
    elif payload.prompt_type == 'helper':
        if not payload.prompt_message:
            logger.error(f"Helper prompt validation failed: prompt_message is empty or None")
            raise HTTPException(
                status_code=400,
                detail="Helper prompts require a prompt_message."
            )
        # Allow system_message to be None or not provided for helper prompts
        # We'll explicitly set it to None when creating
    else:
        raise HTTPException(
            status_code=400,
            detail="prompt_type must be 'system' or 'helper'."
        )
    
    try:
        prompt = Prompt(
            name=payload.name,
            version=payload.version,
            prompt_type=payload.prompt_type,
            system_message=payload.system_message if payload.prompt_type == 'system' else None,
            prompt_message=payload.prompt_message if payload.prompt_type == 'helper' else None,
            prompt_purpose=payload.prompt_purpose,
            status=payload.status,
            llm_model=payload.llm_model,
        )
        db.add(prompt)
        db.commit()
        db.refresh(prompt)
        logger.info(f"Successfully created prompt: id={prompt.id}, name={prompt.name}, type={prompt.prompt_type}")
        return prompt
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="A prompt with this name and version already exists.",
        )
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))


@router.put(
    "/api/founder/prompts/{prompt_id}",
    response_model=PromptResponse,
)
def update_prompt_for_founder(
    prompt_id: UUID,
    payload: PromptUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Update an existing prompt."""
    prompt = db.query(Prompt).filter(Prompt.id == prompt_id).first()
    
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found.")
    
    # Update fields if provided
    if payload.name is not None:
        prompt.name = payload.name
    if payload.version is not None:
        prompt.version = payload.version
    if payload.prompt_type is not None:
        prompt.prompt_type = payload.prompt_type
    if payload.system_message is not None:
        prompt.system_message = payload.system_message
    if payload.prompt_message is not None:
        prompt.prompt_message = payload.prompt_message
    if payload.prompt_purpose is not None:
        prompt.prompt_purpose = payload.prompt_purpose
    if payload.status is not None:
        prompt.status = payload.status
    if payload.llm_model is not None:
        prompt.llm_model = payload.llm_model
    
    # Validate after updates
    if prompt.prompt_type == 'system' and not prompt.system_message:
        raise HTTPException(
            status_code=400,
            detail="System prompts require a system_message."
        )
    if prompt.prompt_type == 'helper':
        if not prompt.prompt_message:
            raise HTTPException(
                status_code=400,
                detail="Helper prompts require a prompt_message."
            )
        if prompt.system_message:
            raise HTTPException(
                status_code=400,
                detail="Helper prompts cannot have a system_message."
            )
    
    try:
        db.commit()
        db.refresh(prompt)
        return prompt
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="A prompt with this name and version already exists.",
        )
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete(
    "/api/founder/prompts/{prompt_id}",
    status_code=204,
)
def delete_prompt_for_founder(
    prompt_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Delete a prompt (sets status to archived or actually deletes)."""
    prompt = db.query(Prompt).filter(Prompt.id == prompt_id).first()
    
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found.")
    
    try:
        db.delete(prompt)
        db.commit()
        return None
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/api/founder/prompts/all/actions", response_model=List[ActionResponse])
def get_all_prompt_actions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Get all action records (execution results) from all prompts, ordered oldest to newest."""
    from sqlalchemy.orm import joinedload
    from app.schemas.action import ActionResponse
    
    # Get all actions with their prompt relationship loaded
    actions = db.query(Action).options(joinedload(Action.prompt)).order_by(Action.created_at.asc()).all()
    # Convert to response with prompt details
    return [ActionResponse.from_orm_with_prompt(action) for action in actions]


@router.get("/api/founder/prompts/{prompt_id}/actions", response_model=List[ActionResponse])
def get_prompt_actions(
    prompt_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Get all action records (execution results) for a specific prompt, ordered oldest to newest."""
    actions = db.query(Action).filter(Action.prompt_id == prompt_id).order_by(Action.created_at.asc()).all()
    return actions


@router.delete("/api/founder/prompts/actions/{action_id}")
def delete_prompt_action(
    action_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Delete an action record (execution result)."""
    action = db.query(Action).filter(Action.id == action_id).first()
    
    if not action:
        raise HTTPException(status_code=404, detail="Action not found.")
    
    # Verify this action belongs to the prompt engineering client
    prompt_engineering_client = get_or_create_prompt_engineering_client(db)
    if action.client_id != prompt_engineering_client.id:
        raise HTTPException(status_code=403, detail="Action does not belong to prompt engineering.")
    
    try:
        db.delete(action)
        db.commit()
        return {"message": "Action deleted successfully"}
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete action: {str(exc)}")


@router.post("/api/founder/prompts/{prompt_id}/execute")
def execute_prompt_for_founder(
    prompt_id: UUID,
    payload: PromptExecuteRequest,
    request: Request,
    stream: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
    llm_service: LLMService = Depends(get_llm_service),
):
    """
    Execute a prompt by sending it to OpenAI or Anthropic API and save the result to actions table.
    
    Args:
        stream: If True, returns streaming response via Server-Sent Events (SSE)
    """
    prompt = db.query(Prompt).filter(Prompt.id == prompt_id).first()
    
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found.")
    
    try:
        # Append helper prompts to user message if this is a system prompt with linked helpers
        user_message = payload.user_message
        if prompt.prompt_type == 'system':
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
                    user_message = (user_message + "\n\n" + "\n\n".join(helper_messages)) if user_message else "\n\n".join(helper_messages)
        
        logger.info(f"Executing prompt {prompt_id} with model: {prompt.llm_model}, user_message length: {len(user_message) if user_message else 0}, stream: {stream}")
        
        if stream:
            # Store prompt values before creating generator (to avoid session issues)
            prompt_id_value = prompt.id
            prompt_system_message = prompt.system_message
            prompt_llm_model = prompt.llm_model
            user_message_value = user_message
            
            # Streaming mode - return SSE response
            def generate_stream():
                accumulated_content = ""
                final_metadata = None
                # Create a new database session for saving the result
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
                            prompt_engineering_client = get_or_create_prompt_engineering_client(save_db)
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
                                client_id=prompt_engineering_client.id,
                                prompt_text_sent=prompt_text_sent,
                                actions=result,
                                insight_ids=[]
                            )
                            save_db.add(action)
                            save_db.commit()
                            logger.info(f"Streaming execution saved to database. Content length: {len(result.get('content', ''))}")
                        except Exception as save_error:
                            logger.error(f"Error saving streaming result to database: {save_error}", exc_info=True)
                            save_db.rollback()
                        finally:
                            save_db.close()
                    
                except Exception as e:
                    logger.error(f"Error during streaming: {e}", exc_info=True)
                    # Send error message via SSE
                    error_message = json.dumps({
                        "type": "error",
                        "error": str(e)
                    })
                    yield f"data: {error_message}\n\n"
                    try:
                        save_db.rollback()
                    except:
                        pass
                    finally:
                        save_db.close()
                    raise
            
            return StreamingResponse(
                generate_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"  # Disable buffering in nginx
                }
            )
        else:
            # Non-streaming mode (backward compatible)
            result = llm_service.execute_prompt(
                system_message=prompt.system_message,
                user_message=user_message,
                model=prompt.llm_model
            )
            
            logger.info(f"Prompt execution successful. Result keys: {result.keys() if result else 'None'}, content length: {len(result.get('content', '')) if result else 0}")
            
            # Get or create the prompt engineering client
            prompt_engineering_client = get_or_create_prompt_engineering_client(db)
            
            # Combine system and user messages for prompt_text_sent
            # Format: "System: {system_message}\n\nUser: {user_message}"
            prompt_text_sent = f"System: {prompt.system_message}\n\nUser: {user_message}"
            
            # Create action record to save the execution result
            action = Action(
                prompt_id=prompt.id,
                client_id=prompt_engineering_client.id,
                prompt_text_sent=prompt_text_sent,
                actions=result,  # Store full result (content, tokens_used, model) in JSONB
                insight_ids=[]  # No insights used in prompt engineering executions
            )
            db.add(action)
            db.commit()
            db.refresh(action)
            
            # Return the result (same as before for frontend compatibility)
            return result
    except RuntimeError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as exc:
        db.rollback()
        logger.error(f"Failed to execute prompt: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to execute prompt: {str(exc)}")


@router.get(
    "/api/founder/prompts/{system_prompt_id}/helper-prompts",
    response_model=List[PromptHelperPromptResponse],
)
def get_linked_helper_prompts(
    system_prompt_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Get all helper prompts linked to a system prompt."""
    links = db.query(PromptHelperPrompt).filter(
        PromptHelperPrompt.system_prompt_id == system_prompt_id
    ).all()
    return links


@router.post(
    "/api/founder/prompts/{system_prompt_id}/helper-prompts/{helper_prompt_id}",
    response_model=PromptHelperPromptResponse,
    status_code=201,
)
def link_helper_prompt(
    system_prompt_id: UUID,
    helper_prompt_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Link a helper prompt to a system prompt."""
    # Verify system prompt exists and is a system prompt
    system_prompt = db.query(Prompt).filter(Prompt.id == system_prompt_id).first()
    if not system_prompt:
        raise HTTPException(status_code=404, detail="System prompt not found.")
    if system_prompt.prompt_type != 'system':
        raise HTTPException(status_code=400, detail="The specified prompt is not a system prompt.")
    
    # Verify helper prompt exists and is a helper prompt
    helper_prompt = db.query(Prompt).filter(Prompt.id == helper_prompt_id).first()
    if not helper_prompt:
        raise HTTPException(status_code=404, detail="Helper prompt not found.")
    if helper_prompt.prompt_type != 'helper':
        raise HTTPException(status_code=400, detail="The specified prompt is not a helper prompt.")
    
    # Check if link already exists
    existing_link = db.query(PromptHelperPrompt).filter(
        PromptHelperPrompt.system_prompt_id == system_prompt_id,
        PromptHelperPrompt.helper_prompt_id == helper_prompt_id
    ).first()
    
    if existing_link:
        raise HTTPException(status_code=400, detail="This helper prompt is already linked to the system prompt.")
    
    try:
        link = PromptHelperPrompt(
            system_prompt_id=system_prompt_id,
            helper_prompt_id=helper_prompt_id
        )
        db.add(link)
        db.commit()
        db.refresh(link)
        return link
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Failed to create link.")
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete(
    "/api/founder/prompts/{system_prompt_id}/helper-prompts/{helper_prompt_id}",
    status_code=204,
)
def unlink_helper_prompt(
    system_prompt_id: UUID,
    helper_prompt_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder),
):
    """Unlink a helper prompt from a system prompt."""
    link = db.query(PromptHelperPrompt).filter(
        PromptHelperPrompt.system_prompt_id == system_prompt_id,
        PromptHelperPrompt.helper_prompt_id == helper_prompt_id
    ).first()
    
    if not link:
        raise HTTPException(status_code=404, detail="Link not found.")
    
    try:
        db.delete(link)
        db.commit()
        return None
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))

