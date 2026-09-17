"""Shared pytest fixtures.

Schema strategy: the test database is built by running the real Alembic
migrations. It costs a couple of seconds once per session and buys a genuine
guarantee that ``alembic upgrade head`` produces the schema the code expects --
the failure mode that otherwise only shows up in production.

Isolation strategy: every test runs inside a transaction that is rolled back on
teardown, so tests never see each other's rows and the suite is re-runnable
without a reset step.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncGenerator, Iterator
from pathlib import Path
from typing import Any

import pytest
from alembic.config import Config
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, AsyncSession, async_sessionmaker

from alembic import command
from app.api.deps import get_current_user
from app.core.config import settings
from app.core.security import hash_password
from app.db.session import create_engine, get_session
from app.main import create_app
from app.models.project import Project, ProjectStatus, ProjectType
from app.models.user import User

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _test_database_url() -> str:
    """Resolve the database the suite runs against.

    Falls back to the primary URL with a ``_test`` suffix, so a developer who
    has not set ``TEST_DATABASE_URL`` still cannot clobber their dev data.
    """
    if settings.test_database_url is not None:
        return str(settings.test_database_url)
    return f"{settings.sqlalchemy_url}_test"


@pytest.fixture(scope="session")
def migrated_database() -> Iterator[str]:
    """Drop and rebuild the test schema by running every migration.

    Synchronous on purpose: Alembic's async ``env.py`` calls ``asyncio.run``,
    which would explode inside an already-running event loop.
    """
    url = _test_database_url()
    asyncio.run(_reset_schema(url))

    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")
    yield url


async def _reset_schema(url: str) -> None:
    """Drop and recreate the public schema so migrations start from nothing."""
    engine = create_engine(url)
    async with engine.begin() as connection:
        await connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        await connection.execute(text("CREATE SCHEMA public"))
    await engine.dispose()


@pytest.fixture(scope="session")
async def engine(migrated_database: str) -> AsyncGenerator[AsyncEngine]:
    """Session-wide async engine pointed at the migrated test database."""
    test_engine = create_engine(migrated_database)
    yield test_engine
    await test_engine.dispose()


@pytest.fixture
async def connection(engine: AsyncEngine) -> AsyncGenerator[AsyncConnection]:
    """An open connection wrapped in a transaction that is always rolled back."""
    async with engine.connect() as conn:
        transaction = await conn.begin()
        yield conn
        await transaction.rollback()


@pytest.fixture
async def session(connection: AsyncConnection) -> AsyncGenerator[AsyncSession]:
    """A session bound to the test transaction.

    ``join_transaction_mode="create_savepoint"`` lets application code call
    ``commit()`` normally: the commit releases a savepoint instead of ending
    the outer transaction, so the rollback still discards everything.
    """
    factory = async_sessionmaker(
        bind=connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    async with factory() as db_session:
        yield db_session


@pytest.fixture
def app(session: AsyncSession) -> FastAPI:
    """An app instance with the database dependency pointed at the test session."""
    application = create_app()

    async def override_get_session() -> AsyncGenerator[AsyncSession]:
        yield session

    application.dependency_overrides[get_session] = override_get_session
    return application


@pytest.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient]:
    """An unauthenticated HTTP client bound to the app."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http_client:
        yield http_client


@pytest.fixture
async def user(session: AsyncSession) -> User:
    """A persisted, active user."""
    return await _make_user(session, "user")


@pytest.fixture
async def other_user(session: AsyncSession) -> User:
    """A second user, for verifying tenancy boundaries."""
    return await _make_user(session, "other")


async def _make_user(session: AsyncSession, prefix: str) -> User:
    """Persist a user with a unique email."""
    record = User(
        email=f"{prefix}-{uuid.uuid4().hex[:8]}@darukaa.test",
        hashed_password=hash_password("CorrectHorse123"),
        full_name=f"{prefix.title()} User",
    )
    session.add(record)
    await session.flush()
    return record


@pytest.fixture
async def auth_client(app: FastAPI, client: AsyncClient, user: User) -> AsyncClient:
    """A client authenticated as ``user``.

    Overriding the dependency rather than minting a real JWT keeps endpoint
    tests focused on the endpoint; token issuing has its own tests.
    """
    app.dependency_overrides[get_current_user] = lambda: user
    return client


@pytest.fixture
async def project(session: AsyncSession, user: User) -> Project:
    """A persisted project owned by ``user``."""
    record = Project(
        owner_id=user.id,
        name="Test Restoration Project",
        description="Fixture project.",
        project_type=ProjectType.CARBON,
        status=ProjectStatus.ACTIVE,
    )
    session.add(record)
    await session.flush()
    return record


@pytest.fixture
def polygon_geojson() -> dict[str, Any]:
    """A valid ~120 ha polygon near Bengaluru."""
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [77.0000, 12.0000],
                [77.0100, 12.0000],
                [77.0100, 12.0100],
                [77.0000, 12.0100],
                [77.0000, 12.0000],
            ]
        ],
    }
