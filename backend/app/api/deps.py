"""Shared FastAPI dependencies: database sessions and the current user."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.core.pagination import PaginationParams, pagination_params
from app.core.security import TokenType, decode_token
from app.db.session import get_session
from app.models.user import User, UserRole
from app.repositories.user_repo import UserRepository

#: ``auto_error=False`` so a missing header raises our own 401 envelope rather
#: than FastAPI's default, keeping every error response the same shape.
bearer_scheme = HTTPBearer(auto_error=False, description="JWT access token")

DbSession = Annotated[AsyncSession, Depends(get_session)]
Pagination = Annotated[PaginationParams, Depends(pagination_params)]
BearerToken = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)]


async def get_current_user(session: DbSession, credentials: BearerToken) -> User:
    """Resolve the signed-in user from the ``Authorization: Bearer`` header.

    Raises:
        AuthenticationError: when the header is missing, the token is invalid
            or expired, or the user no longer exists.
        PermissionDeniedError: when the account has been deactivated.
    """
    if credentials is None or not credentials.credentials:
        raise AuthenticationError("Authentication credentials were not provided.")

    payload = decode_token(credentials.credentials, TokenType.ACCESS)
    try:
        user_id = uuid.UUID(str(payload["sub"]))
    except (KeyError, ValueError) as exc:
        raise AuthenticationError("Token subject is not a valid user id.") from exc

    user = await UserRepository(session).get(user_id)
    if user is None:
        raise AuthenticationError("User no longer exists.")
    if not user.is_active:
        raise PermissionDeniedError("This account has been deactivated.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def require_admin(user: CurrentUser) -> User:
    """Restrict an endpoint to administrators."""
    if user.role is not UserRole.ADMIN:
        raise PermissionDeniedError("Administrator role required.")
    return user


AdminUser = Annotated[User, Depends(require_admin)]
