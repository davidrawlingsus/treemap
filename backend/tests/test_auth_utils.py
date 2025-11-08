from datetime import datetime, timedelta

import pytest

from app.auth import (
    generate_magic_link_token,
    hash_token,
    is_magic_link_token_valid,
    clear_magic_link_state,
)
from app.models.user import User


def test_generate_magic_link_token_returns_expected_format():
    token, token_hash, expires_at = generate_magic_link_token(expires_minutes=30)

    assert isinstance(token, str) and len(token) > 0
    assert isinstance(token_hash, str) and len(token_hash) == 64
    assert expires_at > datetime.utcnow()
    assert token_hash == hash_token(token)


def test_is_magic_link_token_valid_accepts_matching_token():
    user = User(email="test@example.com")
    token, token_hash, expires_at = generate_magic_link_token(expires_minutes=10)
    user.magic_link_token = token_hash
    user.magic_link_expires_at = expires_at

    assert is_magic_link_token_valid(user, token) is True


def test_is_magic_link_token_valid_rejects_expired_token():
    user = User(email="expired@example.com")
    token, token_hash, _ = generate_magic_link_token(expires_minutes=1)
    user.magic_link_token = token_hash
    user.magic_link_expires_at = datetime.utcnow() - timedelta(minutes=1)

    assert is_magic_link_token_valid(user, token) is False


def test_clear_magic_link_state_resets_user_fields():
    user = User(email="clear@example.com")
    token, token_hash, expires_at = generate_magic_link_token()
    user.magic_link_token = token_hash
    user.magic_link_expires_at = expires_at
    user.last_magic_link_sent_at = datetime.utcnow()

    clear_magic_link_state(user)

    assert user.magic_link_token is None
    assert user.magic_link_expires_at is None
    assert user.last_magic_link_sent_at is None

