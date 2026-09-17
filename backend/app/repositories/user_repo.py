"""Data access for users and refresh tokens."""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select, update

from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.repositories.base import BaseRepository, rows_affected


def hash_refresh_token(token: str) -> str:
    """Return the SHA-256 digest stored in place of the raw refresh token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class UserRepository(BaseRepository[User]):
    """Queries over the ``users`` table."""

    model = User

    async def get_by_email(self, email: str) -> User | None:
        """Look up a user by email, case-insensitively."""
        statement = select(User).where(func.lower(User.email) == email.lower())
        result = await self.session.execute(statement)
        return result.scalars().first()

    async def email_exists(self, email: str) -> bool:
        """True when an account already uses ``email``."""
        statement = (
            select(func.count()).select_from(User).where(func.lower(User.email) == email.lower())
        )
        return bool(await self.session.scalar(statement))


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    """Queries over the ``refresh_tokens`` table."""

    model = RefreshToken

    async def get_active(self, raw_token: str) -> RefreshToken | None:
        """Fetch a token that is neither revoked nor expired."""
        statement = select(RefreshToken).where(
            RefreshToken.token_hash == hash_refresh_token(raw_token),
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > datetime.now(UTC),
        )
        result = await self.session.execute(statement)
        return result.scalars().first()

    async def issue(self, user_id: uuid.UUID, raw_token: str, expires_at: datetime) -> RefreshToken:
        """Persist the digest of a newly minted refresh token."""
        return await self.add(
            RefreshToken(
                user_id=user_id,
                token_hash=hash_refresh_token(raw_token),
                expires_at=expires_at,
            )
        )

    async def revoke(self, token: RefreshToken) -> None:
        """Mark a single token as revoked."""
        token.revoked_at = datetime.now(UTC)
        await self.session.flush()

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> int:
        """Revoke every live token for a user (logout-everywhere)."""
        result = await self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )
        await self.session.flush()
        return rows_affected(result)
