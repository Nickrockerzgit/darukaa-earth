"""Async SQLAlchemy engine and session management."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings


def create_engine(url: str | None = None) -> AsyncEngine:
    """Build an async engine.

    ``pool_pre_ping`` matters on managed Postgres (Render) where idle
    connections are reaped server-side; without it the first query after an
    idle period fails with a stale-connection error.
    """
    return create_async_engine(
        url or settings.sqlalchemy_url,
        echo=settings.db_echo,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_pre_ping=True,
        pool_recycle=1800,
    )


engine: AsyncEngine = create_engine()

SessionFactory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_session() -> AsyncGenerator[AsyncSession]:
    """FastAPI dependency yielding a request-scoped session.

    The session is rolled back on any exception and always closed, so a failing
    request can never leak a half-applied transaction into the pool.
    """
    async with SessionFactory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
