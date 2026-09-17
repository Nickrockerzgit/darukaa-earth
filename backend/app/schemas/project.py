"""Project request/response schemas."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.project import ProjectStatus, ProjectType
from app.schemas.common import ORMModel


class ProjectBase(BaseModel):
    """Fields shared by create and update payloads."""

    name: str = Field(min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=4000)
    project_type: ProjectType = ProjectType.CARBON
    status: ProjectStatus = ProjectStatus.DRAFT
    start_date: date | None = None


class ProjectCreate(ProjectBase):
    """Payload for creating a project."""


class ProjectUpdate(BaseModel):
    """Partial update payload; every field is optional."""

    name: str | None = Field(default=None, min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=4000)
    project_type: ProjectType | None = None
    status: ProjectStatus | None = None
    start_date: date | None = None


class ProjectRead(ORMModel):
    """A project as returned by the API."""

    id: uuid.UUID
    owner_id: uuid.UUID
    name: str
    description: str | None
    project_type: ProjectType
    status: ProjectStatus
    start_date: date | None
    created_at: datetime
    updated_at: datetime


class ProjectWithStats(ProjectRead):
    """A project enriched with cheap rollups, so list cards need no N+1 calls."""

    site_count: int = 0
    total_area_hectares: float = 0.0


class ProjectSummary(BaseModel):
    """Aggregated headline numbers for a project's detail page."""

    project_id: uuid.UUID
    site_count: int
    total_area_hectares: float
    latest_metrics: dict[str, float] = Field(
        default_factory=dict,
        description="metric key -> aggregated latest value across the project's sites",
    )
