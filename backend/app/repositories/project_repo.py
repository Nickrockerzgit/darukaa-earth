"""Data access for projects."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any, NamedTuple

from sqlalchemy import Select, func, select
from sqlalchemy.orm import noload

from app.models.project import Project, ProjectStatus, ProjectType
from app.models.site import Site
from app.repositories.base import BaseRepository


class ProjectRow(NamedTuple):
    """A project plus its pre-aggregated site rollups."""

    project: Project
    site_count: int
    total_area_hectares: float


class ProjectRepository(BaseRepository[Project]):
    """Queries over the ``projects`` table."""

    model = Project

    def _scoped(self, owner_id: uuid.UUID) -> Select[tuple[Project]]:
        """Base SELECT restricted to one owner - the tenancy boundary."""
        return select(Project).where(Project.owner_id == owner_id)

    @staticmethod
    def _apply_filters[S: Select[Any]](
        statement: S,
        *,
        status: ProjectStatus | None,
        project_type: ProjectType | None,
        search: str | None,
    ) -> S:
        """Narrow a project SELECT by the supported query parameters."""
        if status is not None:
            statement = statement.where(Project.status == status)
        if project_type is not None:
            statement = statement.where(Project.project_type == project_type)
        if search:
            statement = statement.where(Project.name.ilike(f"%{search}%"))
        return statement

    async def get_for_owner(self, project_id: uuid.UUID, owner_id: uuid.UUID) -> Project | None:
        """Fetch one project, but only if ``owner_id`` owns it."""
        statement = self._scoped(owner_id).where(Project.id == project_id)
        result = await self.session.execute(statement)
        return result.scalars().unique().first()

    async def list_with_stats(
        self,
        owner_id: uuid.UUID,
        *,
        status: ProjectStatus | None = None,
        project_type: ProjectType | None = None,
        search: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[ProjectRow], int]:
        """Return one page of projects with site rollups, plus the total count.

        The rollups come from a LEFT JOIN + GROUP BY rather than a per-project
        follow-up query, so rendering the dashboard is a single round trip
        regardless of how many projects are on the page.
        """
        filtered = self._apply_filters(
            self._scoped(owner_id), status=status, project_type=project_type, search=search
        )
        total = await self.count(filtered)

        statement = (
            self._apply_filters(
                select(
                    Project,
                    func.count(Site.id).label("site_count"),
                    func.coalesce(func.sum(Site.area_hectares), 0).label("total_area"),
                ).select_from(Project),
                status=status,
                project_type=project_type,
                search=search,
            )
            .where(Project.owner_id == owner_id)
            .outerjoin(Site, Site.project_id == Project.id)
            .group_by(Project.id)
            .order_by(Project.created_at.desc())
            .offset(offset)
            .limit(limit)
            # Both relationships must be suppressed. `Project.owner` is
            # `lazy="joined"` on the model, so leaving it alone would add the
            # users columns to a SELECT that only groups by projects.id, and
            # Postgres rejects that: "column users_1.email must appear in the
            # GROUP BY clause". The owner is not needed here either - the
            # response carries owner_id, which lives on projects.
            .options(noload(Project.sites), noload(Project.owner))
        )

        result = await self.session.execute(statement)
        rows = [
            ProjectRow(project=project, site_count=int(count), total_area_hectares=float(area))
            for project, count, area in result.unique().all()
        ]
        return rows, total

    async def stats_for(self, project_id: uuid.UUID) -> tuple[int, float]:
        """Return ``(site_count, total_area_hectares)`` for a single project."""
        statement = select(
            func.count(Site.id), func.coalesce(func.sum(Site.area_hectares), 0)
        ).where(Site.project_id == project_id)
        row = (await self.session.execute(statement)).one()
        return int(row[0]), float(row[1])

    async def list_ids_for_owner(self, owner_id: uuid.UUID) -> Sequence[uuid.UUID]:
        """All project ids owned by a user - used to scope the map query."""
        result = await self.session.execute(select(Project.id).where(Project.owner_id == owner_id))
        return result.scalars().all()
