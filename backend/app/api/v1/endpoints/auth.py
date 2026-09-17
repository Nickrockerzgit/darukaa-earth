"""Authentication endpoints."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
    UserRead,
)
from app.schemas.common import Message
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an account and sign in",
)
async def register(payload: RegisterRequest, session: DbSession) -> AuthResponse:
    """Register a new user and return the user plus a fresh token pair."""
    response = await AuthService(session).register(payload)
    await session.commit()
    return response


@router.post("/login", response_model=AuthResponse, summary="Sign in with email and password")
async def login(payload: LoginRequest, session: DbSession) -> AuthResponse:
    """Verify credentials and issue an access/refresh token pair."""
    response = await AuthService(session).login(payload)
    await session.commit()
    return response


@router.post("/refresh", response_model=TokenPair, summary="Rotate a refresh token")
async def refresh(payload: RefreshRequest, session: DbSession) -> TokenPair:
    """Exchange a valid refresh token for a new pair, revoking the old one."""
    tokens = await AuthService(session).refresh(payload.refresh_token)
    await session.commit()
    return tokens


@router.post("/logout", response_model=Message, summary="Revoke refresh tokens")
async def logout(
    payload: RefreshRequest | None,
    user: CurrentUser,
    session: DbSession,
) -> Message:
    """Revoke one refresh token, or every token for the user when none is given."""
    revoked = await AuthService(session).logout(payload.refresh_token if payload else None, user.id)
    await session.commit()
    return Message(message=f"Revoked {revoked} refresh token(s).")


@router.get("/me", response_model=UserRead, summary="Get the signed-in user")
async def me(user: CurrentUser) -> UserRead:
    """Return the profile of the authenticated user."""
    return UserRead.model_validate(user)
