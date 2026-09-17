"""Authentication request/response schemas."""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.security import MAX_PASSWORD_BYTES
from app.models.user import UserRole
from app.schemas.common import ORMModel

MIN_PASSWORD_LENGTH = 10
_HAS_LOWER = re.compile(r"[a-z]")
_HAS_UPPER = re.compile(r"[A-Z]")
_HAS_DIGIT = re.compile(r"\d")

Password = Annotated[str, Field(min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_BYTES)]


def _assert_password_strength(value: str) -> str:
    """Reject passwords that miss a character class."""
    missing = [
        label
        for label, pattern in (
            ("a lowercase letter", _HAS_LOWER),
            ("an uppercase letter", _HAS_UPPER),
            ("a digit", _HAS_DIGIT),
        )
        if not pattern.search(value)
    ]
    if missing:
        msg = f"Password must contain {', '.join(missing)}"
        raise ValueError(msg)
    return value


class RegisterRequest(BaseModel):
    """Payload for creating a new account."""

    email: EmailStr
    password: Password
    full_name: str | None = Field(default=None, max_length=160)

    @field_validator("password")
    @classmethod
    def _strong_password(cls, value: str) -> str:
        return _assert_password_strength(value)


class LoginRequest(BaseModel):
    """Credentials payload. JSON rather than form-encoded, to match the SPA."""

    email: EmailStr
    password: str = Field(max_length=MAX_PASSWORD_BYTES)


class RefreshRequest(BaseModel):
    """Payload for exchanging a refresh token for a new token pair."""

    refresh_token: str


class TokenPair(BaseModel):
    """Issued credentials returned by login and refresh."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105 - the OAuth scheme name, not a secret
    expires_in: int = Field(description="Access token lifetime in seconds")


class UserRead(ORMModel):
    """Public representation of a user."""

    id: uuid.UUID
    email: EmailStr
    full_name: str | None
    role: UserRole
    is_active: bool
    created_at: datetime


class AuthResponse(BaseModel):
    """Login/register response: the user plus their fresh tokens."""

    user: UserRead
    tokens: TokenPair
