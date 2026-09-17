"""Project model - a carbon or biodiversity initiative owned by a user."""

from __future__ import annotations

import uuid
from datetime import date
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin, pg_enum

if TYPE_CHECKING:
    from app.models.site import Site
    from app.models.user import User


class ProjectType(StrEnum):
    """What the project is measuring."""

    CARBON = "carbon"
    BIODIVERSITY = "biodiversity"
    MIXED = "mixed"


class ProjectStatus(StrEnum):
    """Lifecycle stage of a project."""

    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class Project(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A monitoring programme grouping one or more geographic sites."""

    __tablename__ = "projects"
    __table_args__ = (
        Index("ix_projects_owner_status", "owner_id", "status"),
        # Trigram index backing the case-insensitive ILIKE search filter.
        Index(
            "ix_projects_name_trgm",
            "name",
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"},
        ),
    )

    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    project_type: Mapped[ProjectType] = mapped_column(
        pg_enum(ProjectType, "project_type"),
        default=ProjectType.CARBON,
        nullable=False,
    )
    status: Mapped[ProjectStatus] = mapped_column(
        pg_enum(ProjectStatus, "project_status"),
        default=ProjectStatus.DRAFT,
        nullable=False,
    )
    start_date: Mapped[date | None] = mapped_column(Date)

    owner: Mapped[User] = relationship(back_populates="projects", lazy="joined")
    sites: Mapped[list[Site]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Site.created_at",
    )
