"""Async SQLAlchemy engine and session management.

Managed Postgres providers hand out libpq-style connection strings that asyncpg
cannot consume directly. Normalising them here means the URL from Neon, Render
or Supabase can be pasted into ``DATABASE_URL`` untouched -- see
``docs/decisions/ADR-0008-database-hosting.md``.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import settings

#: libpq query parameters that asyncpg does not accept. Left in the URL they
#: raise ``TypeError: connect() got an unexpected keyword argument``.
LIBPQ_ONLY_PARAMS = frozenset(
    {
        "sslmode",
        "channel_binding",
        "gssencmode",
        "target_session_attrs",
        "options",
        "application_name",
    }
)

#: sslmode values that mean "TLS required".
_TLS_REQUIRED = frozenset({"require", "verify-ca", "verify-full", "prefer", "allow"})

#: Neon and Supabase expose a PgBouncer endpoint under these hostnames.
_POOLER_MARKERS = ("-pooler.", "pgbouncer", "pooler.supabase")


class ConnectionSettings:
    """A normalised database URL plus the engine arguments it implies."""

    def __init__(self, url: str) -> None:
        split = urlsplit(url)
        params = dict(parse_qsl(split.query))

        self.requires_tls = params.get("sslmode", "").lower() in _TLS_REQUIRED
        self.is_pooled = any(marker in (split.hostname or "") for marker in _POOLER_MARKERS)

        kept = {k: v for k, v in params.items() if k not in LIBPQ_ONLY_PARAMS}
        self.url = urlunsplit(split._replace(query=urlencode(kept)))

    @property
    def connect_args(self) -> dict[str, Any]:
        """Driver arguments derived from the stripped parameters."""
        args: dict[str, Any] = {}
        if self.requires_tls:
            # asyncpg spells this `ssl`, not `sslmode`.
            args["ssl"] = True
        if self.is_pooled:
            # PgBouncer in transaction mode does not keep a client on one
            # backend between statements, so asyncpg's prepared-statement cache
            # starts referring to statements the new backend has never seen.
            # The failure looks random, which makes it miserable to diagnose.
            args["statement_cache_size"] = 0
        return args


def create_engine(url: str | None = None) -> AsyncEngine:
    """Build an async engine for ``url`` (defaults to the configured database).

    ``pool_pre_ping`` matters on managed Postgres, where idle connections are
    reaped server-side; without it the first query after a quiet period fails
    with a stale-connection error.
    """
    connection = ConnectionSettings(url or settings.sqlalchemy_url)

    if connection.is_pooled:
        # Pooling in front of PgBouncer just adds a second, redundant pool.
        return create_async_engine(
            connection.url,
            echo=settings.db_echo,
            poolclass=NullPool,
            connect_args=connection.connect_args,
        )

    return create_async_engine(
        connection.url,
        echo=settings.db_echo,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_pre_ping=True,
        pool_recycle=1800,
        connect_args=connection.connect_args,
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
