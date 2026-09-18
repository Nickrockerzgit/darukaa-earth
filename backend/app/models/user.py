"""User account model."""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin, pg_enum

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.refresh_token import RefreshToken


class UserRole(StrEnum):
    """Coarse-grained authorisation role."""

    ADMIN = "admin"
    VIEWER = "viewer"


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A registered platform user."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(128), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(160))
    # `server_default` as well as `default`: the Python default covers ORM
    # inserts, the database default covers everything else (a migration, a
    # bulk COPY, psql). Declaring only one of the two also makes Alembic
    # autogenerate a spurious diff on every run.
    role: Mapped[UserRole] = mapped_column(
        pg_enum(UserRole, "user_role"),
        default=UserRole.ADMIN,
        server_default=UserRole.ADMIN.value,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=true(), nullable=False
    )

    projects: Mapped[list[Project]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    refresh_tokens: Mapped[list[RefreshToken]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="noload",
    )
