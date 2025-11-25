import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

import requests


logger = logging.getLogger(__name__)


@dataclass
class MagicLinkEmailParams:
    """Parameters required to send a magic-link email."""

    to_email: str
    magic_link: str
    client_names: List[str]
    expires_at: datetime


class EmailService:
    """Thin wrapper around the Resend API for transactional email delivery."""

    def __init__(
        self,
        api_key: Optional[str],
        from_email: Optional[str],
        reply_to_email: Optional[str] = None,
    ) -> None:
        self.api_key = api_key
        self.from_email = from_email
        self.reply_to_email = reply_to_email

    def is_configured(self) -> bool:
        """Return True when the Resend client can send emails."""
        return bool(self.api_key and self.from_email)

    def send_magic_link_email(self, params: MagicLinkEmailParams) -> None:
        """
        Send a magic-link email to the user.

        Raises:
            RuntimeError: When the email fails to send.
        """
        if not self.is_configured():
            logger.warning(
                "EmailService is not configured; skipping magic-link email for %s",
                params.to_email,
            )
            raise RuntimeError("Email service is not configured")

        subject = "Sign in to Marketably.ai"
        client_list = ", ".join(params.client_names) if params.client_names else "your account"
        
        # Format expiration time in a more readable format
        expires_at_formatted = params.expires_at.strftime("%B %d, %Y at %I:%M %p UTC")

        text_body = (
            f"Hi,\n\n"
            f"You requested a sign-in link for {client_list}.\n\n"
            f"Click the link below to sign in:\n"
            f"{params.magic_link}\n\n"
            f"This link will expire on {expires_at_formatted}.\n\n"
            f"If you didn't request this email, you can safely ignore it.\n\n"
            f"Best regards,\n"
            f"The Marketably.ai Team"
        )

        html_body = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333333; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f5f5f5;">
    <div style="background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 30px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
        <h1 style="color: #1a1a1a; font-size: 24px; margin-top: 0; margin-bottom: 20px;">Sign in to Marketably.ai</h1>
        
        <p style="font-size: 16px; color: #555555; margin-bottom: 16px;">Hi,</p>
        
        <p style="font-size: 16px; color: #555555; margin-bottom: 24px;">
            You requested a sign-in link for <strong>{client_list}</strong>.
        </p>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="{params.magic_link}" 
               style="display: inline-block; background-color: #007bff; color: #ffffff; text-decoration: none; padding: 14px 28px; border-radius: 6px; font-weight: 600; font-size: 16px; transition: background-color 0.2s;">
                Sign in to Marketably.ai
            </a>
        </div>
        
        <p style="font-size: 14px; color: #888888; margin-bottom: 16px;">
            Or copy and paste this link into your browser:<br>
            <a href="{params.magic_link}" style="color: #007bff; word-break: break-all; text-decoration: none;">{params.magic_link}</a>
        </p>
        
        <p style="font-size: 14px; color: #888888; margin-bottom: 24px;">
            This link will expire on <strong>{expires_at_formatted}</strong>.
        </p>
        
        <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 30px 0;">
        
        <p style="font-size: 12px; color: #999999; margin-bottom: 0;">
            If you didn't request this email, you can safely ignore it. This link can only be used once and will expire soon.
        </p>
    </div>
    
    <p style="font-size: 12px; color: #999999; text-align: center; margin-top: 20px;">
        Best regards,<br>
        The Marketably.ai Team
    </p>
</body>
</html>"""

        # Generate a unique message ID for tracking
        message_id = f"magic-link-{int(time.time())}-{hash(params.to_email) % 10000}"

        payload = {
            "from": self.from_email,
            "to": [params.to_email],
            "subject": subject,
            "html": html_body,
            "text": text_body,
            "tags": [
                {"name": "category", "value": "authentication"},
                {"name": "type", "value": "magic-link"}
            ],
            "headers": {
                "X-Entity-Ref-ID": message_id,
            }
        }

        if self.reply_to_email:
            payload["reply_to"] = self.reply_to_email

        try:
            response = requests.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=10,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.error(
                "Failed to send magic-link email to %s: %s",
                params.to_email,
                exc,
            )
            raise RuntimeError("Failed to send magic-link email") from exc


