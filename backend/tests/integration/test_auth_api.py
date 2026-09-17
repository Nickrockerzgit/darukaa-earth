"""End-to-end tests for the authentication endpoints."""

from __future__ import annotations

from http import HTTPStatus

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.user import User

pytestmark = pytest.mark.integration

REGISTRATION = {
    "email": "new.user@darukaa.test",
    "password": "CorrectHorse123",
    "full_name": "New User",
}


class TestRegister:
    async def test_creates_an_account_and_returns_tokens(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/register", json=REGISTRATION)
        assert response.status_code == HTTPStatus.CREATED

        body = response.json()
        assert body["user"]["email"] == REGISTRATION["email"]
        assert body["tokens"]["access_token"]
        assert body["tokens"]["refresh_token"]
        assert body["tokens"]["token_type"] == "bearer"

    async def test_never_returns_the_password_hash(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/register", json=REGISTRATION)
        assert "hashed_password" not in response.json()["user"]

    async def test_rejects_a_duplicate_email(self, client: AsyncClient):
        await client.post("/api/v1/auth/register", json=REGISTRATION)
        response = await client.post("/api/v1/auth/register", json=REGISTRATION)
        assert response.status_code == HTTPStatus.CONFLICT
        assert response.json()["error"] == "conflict"

    @pytest.mark.parametrize(
        "password",
        ["short1A", "alllowercase123", "ALLUPPERCASE123", "NoDigitsHereAtAll"],
        ids=["too-short", "no-upper", "no-lower", "no-digit"],
    )
    async def test_rejects_a_weak_password(self, client: AsyncClient, password: str):
        response = await client.post(
            "/api/v1/auth/register", json={**REGISTRATION, "password": password}
        )
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    async def test_rejects_a_malformed_email(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/register", json={**REGISTRATION, "email": "not-an-email"}
        )
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


class TestLogin:
    async def test_signs_in_with_correct_credentials(self, client: AsyncClient, user: User):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": user.email, "password": "CorrectHorse123"},
        )
        assert response.status_code == HTTPStatus.OK
        assert response.json()["user"]["id"] == str(user.id)

    async def test_email_matching_is_case_insensitive(self, client: AsyncClient, user: User):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": user.email.upper(), "password": "CorrectHorse123"},
        )
        assert response.status_code == HTTPStatus.OK

    async def test_rejects_a_wrong_password(self, client: AsyncClient, user: User):
        response = await client.post(
            "/api/v1/auth/login", json={"email": user.email, "password": "WrongHorse123"}
        )
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    async def test_unknown_email_is_indistinguishable_from_a_wrong_password(
        self, client: AsyncClient, user: User
    ):
        # Differing responses here would turn login into an account-enumeration oracle.
        unknown = await client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@darukaa.test", "password": "CorrectHorse123"},
        )
        wrong = await client.post(
            "/api/v1/auth/login", json={"email": user.email, "password": "WrongHorse123"}
        )
        assert unknown.status_code == wrong.status_code == HTTPStatus.UNAUTHORIZED
        assert unknown.json()["message"] == wrong.json()["message"]

    async def test_rejects_a_deactivated_account(self, client: AsyncClient, session: AsyncSession):
        user = User(
            email="disabled@darukaa.test",
            hashed_password=hash_password("CorrectHorse123"),
            is_active=False,
        )
        session.add(user)
        await session.flush()

        response = await client.post(
            "/api/v1/auth/login",
            json={"email": user.email, "password": "CorrectHorse123"},
        )
        assert response.status_code == HTTPStatus.FORBIDDEN


class TestRefresh:
    async def test_rotates_the_refresh_token(self, client: AsyncClient, user: User):
        login = await client.post(
            "/api/v1/auth/login", json={"email": user.email, "password": "CorrectHorse123"}
        )
        original = login.json()["tokens"]["refresh_token"]

        refreshed = await client.post("/api/v1/auth/refresh", json={"refresh_token": original})
        assert refreshed.status_code == HTTPStatus.OK
        assert refreshed.json()["refresh_token"] != original

    async def test_a_rotated_token_cannot_be_reused(self, client: AsyncClient, user: User):
        login = await client.post(
            "/api/v1/auth/login", json={"email": user.email, "password": "CorrectHorse123"}
        )
        original = login.json()["tokens"]["refresh_token"]
        await client.post("/api/v1/auth/refresh", json={"refresh_token": original})

        replay = await client.post("/api/v1/auth/refresh", json={"refresh_token": original})
        assert replay.status_code == HTTPStatus.UNAUTHORIZED

    async def test_an_access_token_is_not_accepted_for_refresh(
        self, client: AsyncClient, user: User
    ):
        login = await client.post(
            "/api/v1/auth/login", json={"email": user.email, "password": "CorrectHorse123"}
        )
        access = login.json()["tokens"]["access_token"]
        response = await client.post("/api/v1/auth/refresh", json={"refresh_token": access})
        assert response.status_code == HTTPStatus.UNAUTHORIZED


class TestProtectedRoutes:
    async def test_me_requires_authentication(self, client: AsyncClient):
        assert (await client.get("/api/v1/auth/me")).status_code == HTTPStatus.UNAUTHORIZED

    async def test_me_rejects_a_forged_token(self, client: AsyncClient):
        response = await client.get(
            "/api/v1/auth/me", headers={"Authorization": "Bearer not.a.real.token"}
        )
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    async def test_me_returns_the_signed_in_user(self, client: AsyncClient, user: User):
        login = await client.post(
            "/api/v1/auth/login", json={"email": user.email, "password": "CorrectHorse123"}
        )
        token = login.json()["tokens"]["access_token"]

        response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == HTTPStatus.OK
        assert response.json()["email"] == user.email
