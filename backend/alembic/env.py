"""Alembic environment.

Reads the database URL from application settings rather than ``alembic.ini``,
so migrations and the running app can never drift onto different databases.

The URL goes through the same normalisation as the application engine, because
Alembic builds its own engine: without it, a managed-Postgres URL carrying
``sslmode`` fails here with a TypeError from asyncpg even though the app itself
connects fine.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig
from typing import Any

from sqlalchemy import Connection, pool
from sqlalchemy.ext.asyncio import async_engine_from_config

# Importing ``app.models`` registers every model on ``Base.metadata``; without
# it autogenerate would happily produce a migration that drops half the schema.
import app.models  # noqa: F401
from alembic import context
from app.core.config import settings
from app.db.base import Base
from app.db.session import ConnectionSettings

config = context.config
# Tests and ad-hoc CLI runs may point Alembic at another database by setting
# the option explicitly; otherwise fall back to the app's own configuration.
_raw_url = config.get_main_option("sqlalchemy.url", None) or settings.sqlalchemy_url
_connection = ConnectionSettings(_raw_url)
config.set_main_option("sqlalchemy.url", _connection.url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

#: PostGIS installs its own bookkeeping table plus system views. Without this
#: filter, autogenerate would try to drop them on every run.
EXCLUDED_TABLES = {"spatial_ref_sys", "geography_columns", "geometry_columns"}


def include_object(
    _obj: Any, name: str | None, type_: str, _reflected: bool, _compare_to: Any
) -> bool:
    """Exclude PostGIS-managed objects from autogenerate."""
    if type_ == "table" and name in EXCLUDED_TABLES:
        return False
    # GeoAlchemy2 creates the GIST index itself when the column is created,
    # so reflecting it back would produce a spurious duplicate-index diff.
    return not (type_ == "index" and name is not None and name.startswith("idx_"))


def run_migrations_offline() -> None:
    """Emit SQL to stdout without connecting (``alembic upgrade --sql``)."""
    context.configure(
        url=_connection.url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations on an established synchronous connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=include_object,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine and drive the migrations through it."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        # NullPool: a migration run is short-lived, so a pool buys nothing and
        # would hold connections open against the managed database.
        poolclass=pool.NullPool,
        connect_args=_connection.connect_args,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Entry point for a normal ``alembic upgrade``."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
