"""Tests for password hashing and JWT handling."""

from __future__ import annotations

import time
from datetime import timedelta

import jwt
import pytest

from app.core.config import settings
from app.core.exceptions import AuthenticationError
from app.core.security import (
    MAX_PASSWORD_BYTES,
    TokenType,
    _create_token,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


class TestPasswordHashing:
    def test_hash_is_not_the_plaintext(self):
        digest = hash_password("CorrectHorse123")
        assert digest != "CorrectHorse123"
        assert digest.startswith("$2b$")

    def test_hash_is_salted(self):
        assert hash_password("CorrectHorse123") != hash_password("CorrectHorse123")

    def test_verify_accepts_the_right_password(self):
        assert verify_password("CorrectHorse123", hash_password("CorrectHorse123"))

    def test_verify_rejects_the_wrong_password(self):
        assert not verify_password("WrongHorse123", hash_password("CorrectHorse123"))

    def test_rejects_passwords_beyond_the_bcrypt_limit(self):
        # bcrypt silently truncates past 72 bytes, which would make two long
        # passwords sharing a prefix interchangeable.
        with pytest.raises(ValueError, match="72 bytes"):
            hash_password("a" * (MAX_PASSWORD_BYTES + 1))

    def test_verify_rejects_oversized_input_instead_of_truncating(self):
        digest = hash_password("a" * MAX_PASSWORD_BYTES)
        assert not verify_password("a" * (MAX_PASSWORD_BYTES + 1), digest)

    def test_verify_survives_a_corrupt_hash(self):
        assert not verify_password("CorrectHorse123", "not-a-bcrypt-hash")


class TestTokens:
    def test_access_token_round_trips(self):
        token = create_access_token("user-123")
        payload = decode_token(token, TokenType.ACCESS)
        assert payload["sub"] == "user-123"
        assert payload["type"] == TokenType.ACCESS.value

    def test_refresh_token_round_trips(self):
        payload = decode_token(create_refresh_token("user-123"), TokenType.REFRESH)
        assert payload["type"] == TokenType.REFRESH.value

    def test_each_token_gets_a_unique_id(self):
        first = decode_token(create_access_token("u"), TokenType.ACCESS)
        second = decode_token(create_access_token("u"), TokenType.ACCESS)
        assert first["jti"] != second["jti"]

    def test_a_refresh_token_is_not_accepted_as_an_access_token(self):
        # Without the type claim check, a long-lived refresh token would work
        # as a bearer credential for its whole lifetime.
        with pytest.raises(AuthenticationError, match="access token"):
            decode_token(create_refresh_token("user-123"), TokenType.ACCESS)

    def test_expired_token_is_rejected(self):
        token = _create_token("user-123", TokenType.ACCESS, timedelta(seconds=-1))
        with pytest.raises(AuthenticationError, match="expired"):
            decode_token(token, TokenType.ACCESS)

    def test_token_signed_with_another_key_is_rejected(self):
        forged = jwt.encode(
            {"sub": "attacker", "type": "access", "exp": time.time() + 600},
            "a-completely-different-signing-key",
            algorithm=settings.jwt_algorithm,
        )
        with pytest.raises(AuthenticationError, match="invalid"):
            decode_token(forged, TokenType.ACCESS)

    def test_token_missing_required_claims_is_rejected(self):
        incomplete = jwt.encode(
            {"sub": "user-123"}, settings.secret_key, algorithm=settings.jwt_algorithm
        )
        with pytest.raises(AuthenticationError):
            decode_token(incomplete, TokenType.ACCESS)

    def test_garbage_is_rejected(self):
        with pytest.raises(AuthenticationError):
            decode_token("not.a.jwt", TokenType.ACCESS)
