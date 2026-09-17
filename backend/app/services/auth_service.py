"""Registration, login, refresh-token rotation and logout."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AuthenticationError, ConflictError, PermissionDeniedError
from app.core.security import (
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.repositories.user_repo import RefreshTokenRepository, UserRepository
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest, TokenPair, UserRead


class AuthService:
    """Owns every credential and token transition."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.tokens = RefreshTokenRepository(session)

    # -- registration / login -------------------------------------------------

    async def register(self, payload: RegisterRequest) -> AuthResponse:
        """Create an account and immediately sign the user in.

        Raises:
            ConflictError: if the email is already registered.
        """
        if await self.users.email_exists(payload.email):
            raise ConflictError("An account with this email already exists.", field="email")

        user = await self.users.add(
            User(
                email=payload.email.lower(),
                hashed_password=hash_password(payload.password),
                full_name=payload.full_name,
            )
        )
        return await self._sign_in(user)

    async def login(self, payload: LoginRequest) -> AuthResponse:
        """Verify credentials and issue a token pair.

        The same error is returned for an unknown email and a wrong password so
        the endpoint cannot be used to enumerate registered accounts.
        """
        user = await self.users.get_by_email(payload.email)
        if user is None or not verify_password(payload.password, user.hashed_password):
            raise AuthenticationError("Incorrect email or password.")
        if not user.is_active:
            raise PermissionDeniedError("This account has been deactivated.")
        return await self._sign_in(user)

    # -- token lifecycle ------------------------------------------------------

    async def refresh(self, raw_refresh_token: str) -> TokenPair:
        """Exchange a valid refresh token for a fresh pair, rotating the old one.

        Rotation means a stolen refresh token is usable at most once, and the
        legitimate client's next refresh fails loudly instead of silently
        sharing a session with the attacker.
        """
        decode_token(raw_refresh_token, TokenType.REFRESH)

        stored = await self.tokens.get_active(raw_refresh_token)
        if stored is None:
            raise AuthenticationError("Refresh token is invalid or has been revoked.")

        user = await self.users.get(stored.user_id)
        if user is None or not user.is_active:
            raise AuthenticationError("Account is no longer active.")

        await self.tokens.revoke(stored)
        return await self._issue_tokens(user.id)

    async def logout(self, raw_refresh_token: str | None, user_id: uuid.UUID) -> int:
        """Revoke one refresh token, or every token for the user.

        Returns:
            The number of tokens revoked.
        """
        if raw_refresh_token:
            stored = await self.tokens.get_active(raw_refresh_token)
            if stored is not None and stored.user_id == user_id:
                await self.tokens.revoke(stored)
                return 1
            return 0
        return await self.tokens.revoke_all_for_user(user_id)

    # -- internals ------------------------------------------------------------

    async def _sign_in(self, user: User) -> AuthResponse:
        """Build the standard authentication response for a verified user."""
        tokens = await self._issue_tokens(user.id)
        return AuthResponse(user=UserRead.model_validate(user), tokens=tokens)

    async def _issue_tokens(self, user_id: uuid.UUID) -> TokenPair:
        """Mint an access/refresh pair and persist the refresh digest."""
        subject = str(user_id)
        refresh_token = create_refresh_token(subject)
        await self.tokens.issue(
            user_id=user_id,
            raw_token=refresh_token,
            expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days),
        )
        return TokenPair(
            access_token=create_access_token(subject),
            refresh_token=refresh_token,
            expires_in=settings.access_token_expire_minutes * 60,
        )
