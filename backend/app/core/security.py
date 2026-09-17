"""Password hashing and JWT issuing / verification.

Uses ``bcrypt`` directly rather than passlib: one less dependency layer and no
version-pinning dance between passlib and bcrypt 4.x.
"""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any, Final

import bcrypt
import jwt

from app.core.config import settings
from app.core.exceptions import AuthenticationError

# bcrypt silently truncates inputs beyond 72 bytes, which would make two long
# passwords sharing a prefix equivalent. Reject them instead.
MAX_PASSWORD_BYTES: Final = 72
_BCRYPT_ROUNDS: Final = 12


class TokenType(StrEnum):
    """Discriminates access tokens from refresh tokens inside the JWT payload."""

    ACCESS = "access"
    REFRESH = "refresh"


def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt.

    Raises:
        ValueError: if the password exceeds bcrypt's 72-byte input limit.
    """
    encoded = password.encode("utf-8")
    if len(encoded) > MAX_PASSWORD_BYTES:
        msg = f"Password must not exceed {MAX_PASSWORD_BYTES} bytes"
        raise ValueError(msg)
    return bcrypt.hashpw(encoded, bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Check a plaintext password against a stored bcrypt hash."""
    encoded = password.encode("utf-8")
    if len(encoded) > MAX_PASSWORD_BYTES:
        return False
    try:
        return bcrypt.checkpw(encoded, password_hash.encode("utf-8"))
    except ValueError:
        # Malformed or truncated hash in the database - treat as a failed login.
        return False


def _create_token(
    subject: str,
    token_type: TokenType,
    expires_delta: timedelta,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Encode a signed JWT for ``subject``."""
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type.value,
        "iat": now,
        "nbf": now,
        "exp": now + expires_delta,
        "jti": str(uuid.uuid4()),
        **(extra_claims or {}),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(subject: str, **extra_claims: Any) -> str:
    """Issue a short-lived access token."""
    return _create_token(
        subject,
        TokenType.ACCESS,
        timedelta(minutes=settings.access_token_expire_minutes),
        extra_claims,
    )


def create_refresh_token(subject: str) -> str:
    """Issue a long-lived refresh token."""
    return _create_token(
        subject,
        TokenType.REFRESH,
        timedelta(days=settings.refresh_token_expire_days),
    )


def decode_token(token: str, expected_type: TokenType) -> dict[str, Any]:
    """Decode and validate a JWT, asserting it is of ``expected_type``.

    Raises:
        AuthenticationError: if the token is expired, malformed, or of the
            wrong type (e.g. a refresh token presented as a bearer token).
    """
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "sub", "type"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise AuthenticationError("Token has expired.") from exc
    except jwt.InvalidTokenError as exc:
        raise AuthenticationError("Token is invalid.") from exc

    if payload.get("type") != expected_type.value:
        raise AuthenticationError(f"Expected a {expected_type.value} token.")
    return payload


def generate_opaque_token(nbytes: int = 32) -> str:
    """Return a cryptographically secure URL-safe token (for refresh rotation)."""
    return secrets.token_urlsafe(nbytes)
