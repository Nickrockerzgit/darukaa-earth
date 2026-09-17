"""Reusable ORM column mixins."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column


class UUIDPrimaryKeyMixin:
    """Adds a database-generated UUID primary key.

    UUIDs (rather than serial ints) keep ids non-enumerable in URLs and let the
    client generate optimistic ids for drawn sites before the round trip.
    """

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )


class TimestampMixin:
    """Adds ``created_at`` / ``updated_at`` maintained by the database clock."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


def pg_enum(enum_cls: type[StrEnum], name: str) -> Enum:
    """Build a native Postgres enum column type that stores member *values*.

    Without ``values_callable`` SQLAlchemy persists the member *names*
    (``CARBON``), which then disagree with the lowercase values the API and the
    frontend exchange.
    """
    return Enum(
        enum_cls,
        name=name,
        native_enum=True,
        values_callable=lambda e: [member.value for member in e],
    )
