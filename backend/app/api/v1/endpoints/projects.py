"""Project endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query, Response, status

from app.api.deps import CurrentUser, DbSession, Pagination
from app.models.project import ProjectStatus, ProjectType
from app.schemas.common import Page
from app.schemas.project import (
    ProjectCreate,
    ProjectRead,
    ProjectSummary,
    ProjectUpdate,
    ProjectWithStats,
)
from app.schemas.site import SiteCreate, SiteListItem, SiteRead
from app.services.project_service import ProjectService
from app.services.site_service import SiteService

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=Page[ProjectWithStats], summary="List projects")
async def list_projects(
    user: CurrentUser,
    session: DbSession,
    pagination: Pagination,
    status_filter: ProjectStatus | None = Query(default=None, alias="status"),
    project_type: ProjectType | None = Query(default=None),
    search: str | None = Query(
        default=None, max_length=160, description="Case-insensitive name match"
    ),
) -> Page[ProjectWithStats]:
    """Return a page of the caller's projects with site count and total area."""
    return await ProjectService(session).list(
        user, pagination, status=status_filter, project_type=project_type, search=search
    )


@router.post(
    "",
    response_model=ProjectRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a project",
)
async def create_project(
    payload: ProjectCreate, user: CurrentUser, session: DbSession
) -> ProjectRead:
    """Create a project owned by the caller."""
    project = await ProjectService(session).create(user, payload)
    await session.commit()
    return project


@router.get("/{project_id}", response_model=ProjectRead, summary="Get a project")
async def get_project(project_id: uuid.UUID, user: CurrentUser, session: DbSession) -> ProjectRead:
    """Fetch a single project."""
    return await ProjectService(session).get(user, project_id)


@router.patch("/{project_id}", response_model=ProjectRead, summary="Update a project")
async def update_project(
    project_id: uuid.UUID, payload: ProjectUpdate, user: CurrentUser, session: DbSession
) -> ProjectRead:
    """Apply a partial update to a project."""
    project = await ProjectService(session).update(user, project_id, payload)
    await session.commit()
    return project


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a project and all its sites",
)
async def delete_project(project_id: uuid.UUID, user: CurrentUser, session: DbSession) -> Response:
    """Delete a project; sites and metric history cascade."""
    await ProjectService(session).delete(user, project_id)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{project_id}/summary",
    response_model=ProjectSummary,
    summary="Aggregated KPIs for a project",
)
async def project_summary(
    project_id: uuid.UUID, user: CurrentUser, session: DbSession
) -> ProjectSummary:
    """Site count, total area, and the latest metric values across all sites."""
    return await ProjectService(session).summary(user, project_id)


@router.get(
    "/{project_id}/sites",
    response_model=Page[SiteListItem],
    summary="List a project's sites",
)
async def list_project_sites(
    project_id: uuid.UUID, user: CurrentUser, session: DbSession, pagination: Pagination
) -> Page[SiteListItem]:
    """Return a page of sites, without geometry, for list rendering."""
    return await SiteService(session).list_for_project(user, project_id, pagination)


@router.post(
    "/{project_id}/sites",
    response_model=SiteRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a site by drawing a polygon",
)
async def create_project_site(
    project_id: uuid.UUID,
    payload: SiteCreate,
    user: CurrentUser,
    session: DbSession,
) -> SiteRead:
    """Store a drawn polygon as a site and backfill its metric history."""
    site = await SiteService(session).create(user, project_id, payload)
    await session.commit()
    return site
