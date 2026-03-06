import hashlib
import hmac
import json
import logging
import time
from typing import Any

import requests

from app.config import Settings, get_settings


logger = logging.getLogger(__name__)


class SlackHelpChatService:
    """Minimal Slack bridge for help-chat conversations."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def is_configured(self) -> bool:
        return self.settings.is_slack_help_configured()

    def ensure_configured(self) -> None:
        if not self.is_configured():
            raise RuntimeError("Slack help chat is not configured")

    def verify_signature(
        self,
        payload: bytes,
        timestamp: str | None,
        signature: str | None,
    ) -> bool:
        """Validate Slack request signing signature."""
        self.ensure_configured()
        if not timestamp or not signature:
            return False

        try:
            request_age = abs(int(time.time()) - int(timestamp))
        except ValueError:
            return False

        if request_age > 60 * 5:
            return False

        signing_secret = (self.settings.slack_signing_secret or "").encode("utf-8")
        basestring = f"v0:{timestamp}:{payload.decode('utf-8')}".encode("utf-8")
        digest = "v0=" + hmac.new(signing_secret, basestring, hashlib.sha256).hexdigest()
        return hmac.compare_digest(digest, signature)

    def post_visitor_message(
        self,
        conversation: Any,
        message: Any,
        thread: Any | None,
    ) -> dict[str, str]:
        """Send a site message into Slack, creating a thread when needed."""
        self.ensure_configured()
        channel_id = (self.settings.slack_help_channel_id or "").strip()
        payload = {
            "channel": channel_id,
            "text": self._build_message_text(conversation, message, thread is None),
            "unfurl_links": False,
            "unfurl_media": False,
        }
        if thread is not None:
            payload["thread_ts"] = thread.thread_ts

        response_body = self._post_json(
            "https://slack.com/api/chat.postMessage",
            payload,
        )
        message_ts = response_body.get("ts")
        if not message_ts:
            raise RuntimeError("Slack did not return a message timestamp")

        thread_ts = response_body.get("thread_ts") or message_ts
        return {
            "channel_id": response_body.get("channel", channel_id),
            "message_ts": message_ts,
            "thread_ts": thread_ts,
        }

    def should_process_event(self, event: dict[str, Any]) -> bool:
        """Return True when the event is a human reply in a tracked thread."""
        if event.get("type") != "message":
            return False
        if event.get("subtype"):
            return False
        if event.get("bot_id") or event.get("app_id"):
            return False
        if not event.get("user"):
            return False
        if not (event.get("thread_ts") and event.get("ts")):
            return False
        return bool((event.get("text") or "").strip())

    def _build_message_text(self, conversation: Any, message: Any, is_first_message: bool) -> str:
        participant_name = self._participant_name(conversation)
        participant_email = self._participant_email(conversation)
        source_url = conversation.source_url or "unknown"

        if is_first_message:
            header_lines = [
                ":speech_balloon: New help chat message",
                f"*From:* {participant_name}",
            ]
            if participant_email:
                header_lines.append(f"*Email:* {participant_email}")
            if conversation.user_id:
                header_lines.append("*User Type:* Authenticated app user")
            else:
                header_lines.append("*User Type:* Site visitor")
            header_lines.append(f"*Page:* {source_url}")
            return "\n".join(header_lines + ["", message.body])

        return f"*{participant_name}:*\n{message.body}"

    def _participant_name(self, conversation: Any) -> str:
        if getattr(conversation, "visitor_session", None):
            if conversation.visitor_session.name:
                return conversation.visitor_session.name
            if conversation.visitor_session.email:
                return conversation.visitor_session.email
        if getattr(conversation, "user", None):
            return conversation.user.name or conversation.user.email
        return "Visitor"

    def _participant_email(self, conversation: Any) -> str | None:
        if getattr(conversation, "visitor_session", None) and conversation.visitor_session.email:
            return conversation.visitor_session.email
        if getattr(conversation, "user", None):
            return conversation.user.email
        return None

    def _post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        token = (self.settings.slack_bot_token or "").strip()
        try:
            response = requests.post(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json; charset=utf-8",
                },
                data=json.dumps(payload),
                timeout=10,
            )
            response.raise_for_status()
            body = response.json()
        except requests.RequestException as exc:
            logger.error("Slack API request failed: %s", exc, exc_info=True)
            raise RuntimeError("Failed to send message to Slack") from exc
        except ValueError as exc:
            raise RuntimeError("Slack API returned invalid JSON") from exc

        if not body.get("ok"):
            error = body.get("error") or "unknown_error"
            raise RuntimeError(f"Slack API error: {error}")
        return body
