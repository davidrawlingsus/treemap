from datetime import datetime, timedelta, timezone

import pytest

from app.services.email import EmailService, MagicLinkEmailParams


def test_email_service_requires_configuration():
    service = EmailService(api_key=None, from_email=None)
    params = MagicLinkEmailParams(
        to_email="user@example.com",
        magic_link="https://example.com/magic",
        client_names=["Example Client"],
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
    )

    assert service.is_configured() is False
    with pytest.raises(RuntimeError):
        service.send_magic_link_email(params)


def test_email_service_sends_email(monkeypatch):
    service = EmailService(api_key="test_api_key", from_email="noreply@example.com")
    captured = {}

    class FakeResponse:
        status_code = 202

        def raise_for_status(self):
            return None

    def fake_post(url, headers, json, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr("app.services.email.requests.post", fake_post)

    params = MagicLinkEmailParams(
        to_email="user@example.com",
        magic_link="https://example.com/magic",
        client_names=["Example Client"],
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
    )

    service.send_magic_link_email(params)

    assert captured["url"] == "https://api.resend.com/emails"
    assert captured["headers"]["Authorization"] == "Bearer test_api_key"
    assert captured["json"]["from"] == "noreply@example.com"
    assert captured["json"]["to"] == [params.to_email]
    assert params.magic_link in captured["json"]["html"]

