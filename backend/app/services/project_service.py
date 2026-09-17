"""Project business logic."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.pagination import PaginationParams
from app.models.project import Project, ProjectStatus, ProjectType
from app.models.user import User
from app.repositories.metric_repo import SiteMetricRepository
from app.repositories.project_repo import ProjectRepository
from app.schemas.common import Page
from app.schemas.project import (
    ProjectCreate,
    ProjectRead,
    ProjectSummary,
    ProjectUpdate,
    ProjectWithStats,
)


class ProjectService:
    """Create, read, update and archive projects for the signed-in user."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.projects = ProjectRepository(session)
        self.metrics = SiteMetricRepository(session)

    async def create(self, owner: User, payload: ProjectCreate) -> ProjectRead:
        """Create a project owned by ``owner``."""
        project = await self.projects.add(Project(owner_id=owner.id, **payload.model_dump()))
        return ProjectRead.model_validate(project)

    async def list(
        self,
        owner: User,
        pagination: PaginationParams,
        *,
        status: ProjectStatus | None = None,
        project_type: ProjectType | None = None,
        search: str | None = None,
    ) -> Page[ProjectWithStats]:
        """Return one page of the user's projects, each with site rollups."""
        rows, total = await self.projects.list_with_stats(
            owner.id,
            status=status,
            project_type=project_type,
            search=search,
            offset=pagination.offset,
            limit=pagination.limit,
        )
        items = [
            ProjectWithStats(
                **ProjectRead.model_validate(row.project).model_dump(),
                site_count=row.site_count,
                total_area_hectares=row.total_area_hectares,
            )
            for row in rows
        ]
        return Page.create(items, total=total, page=pagination.page, size=pagination.size)

    async def get(self, owner: User, project_id: uuid.UUID) -> ProjectRead:
        """Fetch one project the user owns."""
        return ProjectRead.model_validate(await self._require(owner, project_id))

    async def update(
        self, owner: User, project_id: uuid.UUID, payload: ProjectUpdate
    ) -> ProjectRead:
        """Apply a partial update to a project."""
        project = await self._require(owner, project_id)
        changes = payload.model_dump(exclude_unset=True)
        self.projects.apply_updates(project, changes)
        await self.session.flush()
        await self.session.refresh(project)
        return ProjectRead.model_validate(project)

    async def delete(self, owner: User, project_id: uuid.UUID) -> None:
        """Delete a project and, by cascade, its sites and their metrics."""
        await self.projects.delete(await self._require(owner, project_id))

    async def summary(self, owner: User, project_id: uuid.UUID) -> ProjectSummary:
        """Headline numbers for a project's detail page."""
        project = await self._require(owner, project_id)
        site_count, total_area = await self.projects.stats_for(project.id)
        latest = await self.metrics.project_latest_totals(project.id)
        return ProjectSummary(
            project_id=project.id,
            site_count=site_count,
            total_area_hectares=total_area,
            latest_metrics={key: float(value) for key, value in latest},
        )

    async def _require(self, owner: User, project_id: uuid.UUID) -> Project:
        """Load a project or raise 404.

        A project owned by somebody else is reported as missing rather than
        forbidden, so ids cannot be probed for existence across accounts.
        """
        project = await self.projects.get_for_owner(project_id, owner.id)
        if project is None:
            raise NotFoundError("Project not found.", project_id=str(project_id))
        return project
