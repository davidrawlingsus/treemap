import uuid

from fastapi.testclient import TestClient

from app.main import app
from app.auth import get_optional_current_user
from app.database import SessionLocal
from app.models import ChatConversation, ChatVisitorSession, User
from app.routers.help_chat import get_slack_service


client = TestClient(app)


class FakeSlackService:
    def __init__(self):
        self.message_index = 0
        self.thread_ts = f"thread-{uuid.uuid4()}"
        self.reply_ts = f"reply-{uuid.uuid4()}"

    def ensure_configured(self):
        return None

    def verify_signature(self, payload, timestamp, signature):
        return True

    def should_process_event(self, event):
        return True

    def post_visitor_message(self, conversation, message, thread):
        self.message_index += 1
        thread_ts = thread.thread_ts if thread is not None else self.thread_ts
        return {
            "channel_id": "C_HELP",
            "message_ts": f"{self.message_index}.000",
            "thread_ts": thread_ts,
        }


def create_test_user():
    db = SessionLocal()
    user = User(
        email=f"help-chat-{uuid.uuid4()}@example.com",
        name="Help Chat Tester",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user


def cleanup_conversation(conversation_id):
    db = SessionLocal()
    conversation = db.query(ChatConversation).filter(ChatConversation.id == conversation_id).first()
    if conversation is not None:
        visitor_session_id = conversation.visitor_session_id
        db.delete(conversation)
        db.commit()
        if visitor_session_id is not None:
            visitor_session = db.query(ChatVisitorSession).filter(ChatVisitorSession.id == visitor_session_id).first()
            if visitor_session is not None:
                db.delete(visitor_session)
                db.commit()
    db.close()


def cleanup_user(user_id):
    db = SessionLocal()
    user = db.query(User).filter(User.id == user_id).first()
    if user is not None:
        db.delete(user)
        db.commit()
    db.close()


def test_help_chat_public_resume_and_operator_reply_flow():
    fake_slack = FakeSlackService()
    app.dependency_overrides[get_slack_service] = lambda: fake_slack

    conversation_id = None
    try:
        ensure_response = client.post(
            "/api/help-chat/conversations/ensure",
            json={
                "source_url": "http://localhost:3000/pricing.html",
                "source_path": "/pricing.html",
                "source_title": "Pricing",
            },
        )
        assert ensure_response.status_code == 200
        conversation = ensure_response.json()
        conversation_id = conversation["id"]
        visitor_token = conversation["visitor_token"]

        second_ensure_response = client.post(
            "/api/help-chat/conversations/ensure",
            json={
                "visitor_token": visitor_token,
                "source_url": "http://localhost:3000/pricing.html",
                "source_path": "/pricing.html",
            },
        )
        assert second_ensure_response.status_code == 200
        assert second_ensure_response.json()["id"] == conversation_id

        first_message_response = client.post(
            f"/api/help-chat/conversations/{conversation_id}/messages",
            params={"visitor_token": visitor_token},
            json={"body": "I need help with pricing"},
        )
        assert first_message_response.status_code == 200
        first_message = first_message_response.json()

        db = SessionLocal()
        stored_conversation = db.query(ChatConversation).filter(ChatConversation.id == conversation_id).first()
        assert stored_conversation is not None
        thread_ts = stored_conversation.slack_thread.thread_ts
        db.close()

        webhook_response = client.post(
            "/api/help-chat/slack/events",
            headers={
                "x-slack-request-timestamp": "1",
                "x-slack-signature": "v0=fake",
            },
            json={
                "type": "event_callback",
                "event": {
                    "type": "message",
                    "channel": "C_HELP",
                    "thread_ts": thread_ts,
                    "ts": fake_slack.reply_ts,
                    "user": "U123",
                    "text": "Happy to help. What do you need?",
                },
            },
        )
        assert webhook_response.status_code == 200

        messages_response = client.get(
            f"/api/help-chat/conversations/{conversation_id}/messages",
            params={"visitor_token": visitor_token},
        )
        assert messages_response.status_code == 200
        messages = messages_response.json()
        assert len(messages) == 2
        assert messages[0]["id"] == first_message["id"]
        assert messages[1]["sender_type"] == "operator"

    finally:
        app.dependency_overrides.pop(get_slack_service, None)
        if conversation_id is not None:
            cleanup_conversation(conversation_id)


def test_help_chat_authenticated_user_is_attached_to_conversation():
    fake_slack = FakeSlackService()
    test_user = create_test_user()
    app.dependency_overrides[get_slack_service] = lambda: fake_slack
    app.dependency_overrides[get_optional_current_user] = lambda: test_user

    conversation_id = None
    try:
        response = client.post(
            "/api/help-chat/conversations/ensure",
            json={
                "source_url": "http://localhost:3000/index.html",
                "source_path": "/index.html",
                "source_title": "Vizualizd",
            },
        )
        assert response.status_code == 200
        body = response.json()
        conversation_id = body["id"]
        assert body["is_authenticated_user"] is True
        assert body["participant_email"] == test_user.email
    finally:
        app.dependency_overrides.pop(get_slack_service, None)
        app.dependency_overrides.pop(get_optional_current_user, None)
        if conversation_id is not None:
            cleanup_conversation(conversation_id)
        cleanup_user(test_user.id)
