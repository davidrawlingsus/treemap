import logging
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

        subject = "Your Visualizd secure sign-in link"
        client_list = ", ".join(params.client_names) if params.client_names else "your account"

        text_body = (
            "Hi,\n\n"
            f"Use the secure link below to access {client_list}:\n\n"
            f"{params.magic_link}\n\n"
            f"This link expires at {params.expires_at.isoformat()} UTC.\n"
            "If you did not request this email you can safely ignore it.\n\n"
            "— The Visualizd Team"
        )

        html_body = f"""
        <p>Hi,</p>
        <p>Use the secure link below to access {client_list}:</p>
        <p><a href="{params.magic_link}">Sign in to Visualizd</a></p>
        <p>This link expires at <strong>{params.expires_at.isoformat()} UTC</strong>.</p>
        <p>If you did not request this email you can safely ignore it.</p>
        <p>— The Visualizd Team</p>
        """

        payload = {
            "from": self.from_email,
            "to": [params.to_email],
            "subject": subject,
            "html": html_body,
            "text": text_body,
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


