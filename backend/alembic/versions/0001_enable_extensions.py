"""Enable the PostgreSQL extensions the schema depends on.

Revision ID: 0001
Revises:
Create Date: 2026-09-18
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: postgis  - geometry types, spatial indexes, ST_* functions.
#: pg_trgm  - trigram index backing the case-insensitive project name search.
#: pgcrypto - gen_random_uuid() on PostgreSQL < 13; harmless on newer servers.
EXTENSIONS = ("postgis", "pg_trgm", "pgcrypto")


def upgrade() -> None:
    """Install the required extensions."""
    for extension in EXTENSIONS:
        op.execute(f'CREATE EXTENSION IF NOT EXISTS "{extension}"')


def downgrade() -> None:
    """Drop the extensions.

    ``postgis`` is deliberately left installed: dropping it would cascade into
    any other schema in the same database that still uses geometry columns.
    """
    for extension in ("pg_trgm", "pgcrypto"):
        op.execute(f'DROP EXTENSION IF EXISTS "{extension}"')
