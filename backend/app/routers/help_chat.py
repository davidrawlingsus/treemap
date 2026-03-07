import asyncio
import json
import logging
import secrets
import time
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse, PlainTextResponse, StreamingResponse
from sqlalchemy.orm import Session, joinedload

from app.auth import get_optional_current_user
from app.database import SessionLocal, get_db
from app.models import ChatConversation, ChatMessage, ChatSlackThread, ChatVisitorSession, User
from app.schemas import (
    HelpChatConversationResponse,
    HelpChatEnsureConversationRequest,
    HelpChatMessageCreate,
    HelpChatMessageResponse,
)
from app.services.slack_chat_service import SlackHelpChatService


router = APIRouter(prefix="/api/help-chat", tags=["help-chat"])
logger = logging.getLogger(__name__)


def get_slack_service() -> SlackHelpChatService:
    return SlackHelpChatService()


def _generate_visitor_token() -> str:
    return secrets.token_urlsafe(24)


def _conversation_query(db: Session):
    return db.query(ChatConversation).options(
        joinedload(ChatConversation.user),
        joinedload(ChatConversation.visitor_session),
        joinedload(ChatConversation.messages),
        joinedload(ChatConversation.slack_thread),
    )


def _get_conversation_or_404(db: Session, conversation_id: UUID) -> ChatConversation:
    conversation = (
        _conversation_query(db)
        .filter(ChatConversation.id == conversation_id)
        .first()
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


def _assert_conversation_access(
    conversation: ChatConversation,
    visitor_token: str | None,
    current_user: User | None,
) -> None:
    if current_user is not None:
        if conversation.user_id == current_user.id:
            return
        if (
            conversation.visitor_session is not None
            and conversation.visitor_session.authenticated_user_id == current_user.id
        ):
            return

    if (
        visitor_token
        and conversation.visitor_session is not None
        and conversation.visitor_session.visitor_token == visitor_token
    ):
        return

    raise HTTPException(status_code=403, detail="You do not have access to this conversation")


def _touch_visitor_session(
    db: Session,
    payload: HelpChatEnsureConversationRequest,
    current_user: User | None,
) -> tuple[ChatVisitorSession, str]:
    visitor_token = (payload.visitor_token or "").strip() or _generate_visitor_token()
    visitor_session = (
        db.query(ChatVisitorSession)
        .filter(ChatVisitorSession.visitor_token == visitor_token)
        .first()
    )

    if (
        visitor_session is not None
        and current_user is not None
        and visitor_session.authenticated_user_id is not None
        and visitor_session.authenticated_user_id != current_user.id
    ):
        visitor_session = None
        visitor_token = _generate_visitor_token()

    if visitor_session is None:
        visitor_session = ChatVisitorSession(visitor_token=visitor_token)
        db.add(visitor_session)

    if current_user is not None:
        visitor_session.authenticated_user_id = current_user.id
        visitor_session.name = current_user.name or visitor_session.name
        visitor_session.email = current_user.email or visitor_session.email

    if payload.visitor_name is not None and payload.visitor_name.strip():
        visitor_session.name = payload.visitor_name.strip()
    if payload.visitor_email is not None:
        visitor_session.email = str(payload.visitor_email)

    visitor_session.last_seen_at = datetime.now(timezone.utc)
    db.flush()
    return visitor_session, visitor_token


def _apply_conversation_context(
    conversation: ChatConversation,
    payload: HelpChatEnsureConversationRequest,
) -> None:
    conversation.source_url = payload.source_url or conversation.source_url
    conversation.source_path = payload.source_path or conversation.source_path
    conversation.source_title = payload.source_title or conversation.source_title
    conversation.referrer_url = payload.referrer_url or conversation.referrer_url
    if payload.metadata:
        merged_metadata = dict(conversation.conversation_metadata or {})
        merged_metadata.update(payload.metadata)
        conversation.conversation_metadata = merged_metadata


def _participant_name(conversation: ChatConversation) -> str | None:
    if conversation.visitor_session is not None:
        if conversation.visitor_session.name:
            return conversation.visitor_session.name
        if conversation.visitor_session.email:
            return conversation.visitor_session.email
    if conversation.user is not None:
        return conversation.user.name or conversation.user.email
    return None


def _participant_email(conversation: ChatConversation) -> str | None:
    if conversation.visitor_session is not None and conversation.visitor_session.email:
        return conversation.visitor_session.email
    if conversation.user is not None:
        return conversation.user.email
    return None


def _serialize_message(message: ChatMessage) -> dict:
    return HelpChatMessageResponse.model_validate(message).model_dump(mode="json")


def _conversation_response(
    conversation: ChatConversation,
    visitor_token: str,
) -> HelpChatConversationResponse:
    messages = [HelpChatMessageResponse.model_validate(message) for message in conversation.messages]
    return HelpChatConversationResponse(
        id=conversation.id,
        visitor_token=visitor_token,
        status=conversation.status,
        source_url=conversation.source_url,
        source_path=conversation.source_path,
        source_title=conversation.source_title,
        referrer_url=conversation.referrer_url,
        participant_name=_participant_name(conversation),
        participant_email=_participant_email(conversation),
        is_authenticated_user=bool(conversation.user_id),
        messages=messages,
    )


@router.post("/conversations/ensure", response_model=HelpChatConversationResponse)
def ensure_conversation(
    payload: HelpChatEnsureConversationRequest,
    current_user: User | None = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    visitor_session, visitor_token = _touch_visitor_session(db, payload, current_user)

    if payload.conversation_id is not None:
        conversation = _get_conversation_or_404(db, payload.conversation_id)
        _assert_conversation_access(conversation, visitor_token, current_user)
    else:
        conversation = (
            _conversation_query(db)
            .filter(
                ChatConversation.visitor_session_id == visitor_session.id,
                ChatConversation.status == "open",
            )
            .order_by(ChatConversation.last_message_at.desc())
            .first()
        )

        if conversation is None and current_user is not None:
            conversation = (
                _conversation_query(db)
                .filter(
                    ChatConversation.user_id == current_user.id,
                    ChatConversation.status == "open",
                )
                .order_by(ChatConversation.last_message_at.desc())
                .first()
            )

    if conversation is None:
        conversation = ChatConversation(
            visitor_session_id=visitor_session.id,
            user_id=current_user.id if current_user is not None else None,
            status="open",
        )
        db.add(conversation)
        db.flush()
    else:
        conversation.visitor_session_id = visitor_session.id
        if current_user is not None:
            conversation.user_id = current_user.id

    _apply_conversation_context(conversation, payload)
    db.commit()
    db.refresh(conversation)

    hydrated = _get_conversation_or_404(db, conversation.id)
    return _conversation_response(hydrated, visitor_token)


@router.get("/conversations/{conversation_id}/messages", response_model=list[HelpChatMessageResponse])
def list_messages(
    conversation_id: UUID,
    visitor_token: str | None = Query(default=None),
    current_user: User | None = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    conversation = _get_conversation_or_404(db, conversation_id)
    _assert_conversation_access(conversation, visitor_token, current_user)
    return [HelpChatMessageResponse.model_validate(message) for message in conversation.messages]


@router.post("/conversations/{conversation_id}/messages", response_model=HelpChatMessageResponse)
def create_message(
    conversation_id: UUID,
    payload: HelpChatMessageCreate,
    visitor_token: str | None = Query(default=None),
    current_user: User | None = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
    slack_service: SlackHelpChatService = Depends(get_slack_service),
):
    conversation = _get_conversation_or_404(db, conversation_id)
    _assert_conversation_access(conversation, visitor_token, current_user)

    body = payload.body.strip()
    if not body:
        raise HTTPException(status_code=400, detail="Message body cannot be empty")

    if payload.client_message_id:
        existing = (
            db.query(ChatMessage)
            .filter(
                ChatMessage.conversation_id == conversation_id,
                ChatMessage.client_message_id == payload.client_message_id,
            )
            .first()
        )
        if existing is not None:
            return HelpChatMessageResponse.model_validate(existing)

    sender_type = "user" if current_user is not None else "visitor"
    sender_label = _participant_name(conversation) or ("User" if current_user is not None else "Visitor")

    message = ChatMessage(
        conversation_id=conversation.id,
        sender_type=sender_type,
        sender_label=sender_label,
        body=body,
        client_message_id=payload.client_message_id,
    )
    conversation.last_message_at = datetime.now(timezone.utc)
    db.add(message)
    db.flush()

    try:
        slack_result = slack_service.post_visitor_message(conversation, message, conversation.slack_thread)
    except RuntimeError as exc:
        db.rollback()
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    message.slack_channel_id = slack_result["channel_id"]
    message.slack_ts = slack_result["message_ts"]

    if conversation.slack_thread is None:
        db.add(
            ChatSlackThread(
                conversation_id=conversation.id,
                channel_id=slack_result["channel_id"],
                thread_ts=slack_result["thread_ts"],
                initial_message_ts=slack_result["message_ts"],
            )
        )

    db.commit()
    db.refresh(message)
    return HelpChatMessageResponse.model_validate(message)


@router.get("/conversations/{conversation_id}/stream")
async def stream_messages(
    conversation_id: UUID,
    request: Request,
    visitor_token: str | None = Query(default=None),
    since: datetime | None = Query(default=None),
    current_user: User | None = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    conversation = _get_conversation_or_404(db, conversation_id)
    _assert_conversation_access(conversation, visitor_token, current_user)

    if since is None:
        latest = (
            db.query(ChatMessage)
            .filter(ChatMessage.conversation_id == conversation_id)
            .order_by(ChatMessage.created_at.desc())
            .first()
        )
        last_seen = latest.created_at if latest is not None else datetime.now(timezone.utc)
    else:
        last_seen = since if since.tzinfo else since.replace(tzinfo=timezone.utc)

    async def event_stream():
        stream_db = SessionLocal()
        heartbeat_started = time.monotonic()
        cursor = last_seen
        try:
            while True:
                if await request.is_disconnected():
                    break

                messages = (
                    stream_db.query(ChatMessage)
                    .filter(
                        ChatMessage.conversation_id == conversation_id,
                        ChatMessage.created_at > cursor,
                    )
                    .order_by(ChatMessage.created_at.asc())
                    .all()
                )

                for message in messages:
                    cursor = message.created_at
                    payload = {
                        "type": "message",
                        "message": _serialize_message(message),
                    }
                    yield f"data: {json.dumps(payload)}\n\n"

                if time.monotonic() - heartbeat_started >= 15:
                    heartbeat_started = time.monotonic()
                    yield "event: ping\ndata: {}\n\n"

                await asyncio.sleep(1)
        finally:
            stream_db.close()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/slack/events")
async def slack_events(
    request: Request,
    db: Session = Depends(get_db),
    slack_service: SlackHelpChatService = Depends(get_slack_service),
):
    payload = await request.body()
    try:
        body = json.loads(payload.decode("utf-8") or "{}")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid Slack payload") from exc

    # Slack URL verification can happen before the app is fully configured.
    if body.get("type") == "url_verification":
        return PlainTextResponse(body.get("challenge", ""))

    try:
        slack_service.ensure_configured()
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    if not slack_service.verify_signature(
        payload,
        request.headers.get("x-slack-request-timestamp"),
        request.headers.get("x-slack-signature"),
    ):
        raise HTTPException(status_code=400, detail="Invalid Slack signature")

    if body.get("type") != "event_callback":
        return {"ok": True}

    event = body.get("event") or {}
    if not slack_service.should_process_event(event):
        return {"ok": True}

    channel_id = event.get("channel")
    thread_ts = event.get("thread_ts")
    message_ts = event.get("ts")

    thread = (
        db.query(ChatSlackThread)
        .options(joinedload(ChatSlackThread.conversation))
        .filter(
            ChatSlackThread.channel_id == channel_id,
            ChatSlackThread.thread_ts == thread_ts,
        )
        .first()
    )
    if thread is None:
        logger.info("Ignoring Slack reply for unknown thread %s", thread_ts)
        return {"ok": True}

    existing = (
        db.query(ChatMessage)
        .filter(ChatMessage.slack_ts == message_ts)
        .first()
    )
    if existing is not None:
        return {"ok": True}

    message = ChatMessage(
        conversation_id=thread.conversation_id,
        sender_type="operator",
        sender_label="David R",
        body=(event.get("text") or "").strip(),
        slack_channel_id=channel_id,
        slack_ts=message_ts,
    )
    thread.conversation.last_message_at = datetime.now(timezone.utc)
    db.add(message)
    db.commit()
    return {"ok": True}
