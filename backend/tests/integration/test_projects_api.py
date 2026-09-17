"""End-to-end tests for the project endpoints."""

from __future__ import annotations

import uuid
from http import HTTPStatus

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project, ProjectStatus, ProjectType
from app.models.user import User

pytestmark = pytest.mark.integration

NEW_PROJECT = {
    "name": "Coastal Mangrove Belt",
    "description": "Blue carbon restoration.",
    "project_type": "mixed",
    "status": "active",
    "start_date": "2024-01-01",
}


class TestCreate:
    async def test_creates_a_project_owned_by_the_caller(
        self, auth_client: AsyncClient, user: User
    ):
        response = await auth_client.post("/api/v1/projects", json=NEW_PROJECT)
        assert response.status_code == HTTPStatus.CREATED

        body = response.json()
        assert body["name"] == NEW_PROJECT["name"]
        assert body["owner_id"] == str(user.id)

    async def test_requires_authentication(self, client: AsyncClient):
        response = await client.post("/api/v1/projects", json=NEW_PROJECT)
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    @pytest.mark.parametrize(
        ("field", "value"),
        [("name", "x"), ("project_type", "nonsense"), ("status", "nonsense")],
    )
    async def test_rejects_invalid_input(self, auth_client: AsyncClient, field: str, value: str):
        response = await auth_client.post("/api/v1/projects", json={**NEW_PROJECT, field: value})
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


class TestList:
    async def test_returns_only_the_callers_projects(
        self,
        auth_client: AsyncClient,
        session: AsyncSession,
        project: Project,
        other_user: User,
    ):
        session.add(Project(owner_id=other_user.id, name="Somebody Else's Project"))
        await session.flush()

        body = (await auth_client.get("/api/v1/projects")).json()
        names = [item["name"] for item in body["items"]]
        assert project.name in names
        assert "Somebody Else's Project" not in names

    async def test_includes_site_rollups(self, auth_client: AsyncClient, project: Project):
        body = (await auth_client.get("/api/v1/projects")).json()
        row = next(item for item in body["items"] if item["id"] == str(project.id))
        assert row["site_count"] == 0
        assert row["total_area_hectares"] == 0

    async def test_filters_by_status(
        self, auth_client: AsyncClient, session: AsyncSession, user: User
    ):
        session.add(Project(owner_id=user.id, name="Archived One", status=ProjectStatus.ARCHIVED))
        await session.flush()

        body = (await auth_client.get("/api/v1/projects?status=archived")).json()
        assert [item["name"] for item in body["items"]] == ["Archived One"]

    async def test_search_is_case_insensitive(self, auth_client: AsyncClient, project: Project):
        body = (await auth_client.get("/api/v1/projects?search=RESTORATION")).json()
        assert body["total"] == 1

    async def test_paginates(self, auth_client: AsyncClient, session: AsyncSession, user: User):
        for index in range(5):
            session.add(Project(owner_id=user.id, name=f"Project {index}"))
        await session.flush()

        body = (await auth_client.get("/api/v1/projects?page=1&size=2")).json()
        assert len(body["items"]) == 2
        assert body["total"] == 5
        assert body["pages"] == 3

    async def test_rejects_an_out_of_range_page_size(self, auth_client: AsyncClient):
        response = await auth_client.get("/api/v1/projects?size=1000")
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


class TestDetail:
    async def test_returns_a_project(self, auth_client: AsyncClient, project: Project):
        response = await auth_client.get(f"/api/v1/projects/{project.id}")
        assert response.status_code == HTTPStatus.OK
        assert response.json()["id"] == str(project.id)

    async def test_unknown_id_is_not_found(self, auth_client: AsyncClient):
        response = await auth_client.get(f"/api/v1/projects/{uuid.uuid4()}")
        assert response.status_code == HTTPStatus.NOT_FOUND

    async def test_another_users_project_reads_as_not_found(
        self, auth_client: AsyncClient, session: AsyncSession, other_user: User
    ):
        # 404 rather than 403: a 403 would confirm the id exists.
        foreign = Project(owner_id=other_user.id, name="Foreign Project")
        session.add(foreign)
        await session.flush()

        response = await auth_client.get(f"/api/v1/projects/{foreign.id}")
        assert response.status_code == HTTPStatus.NOT_FOUND

    async def test_malformed_id_is_rejected(self, auth_client: AsyncClient):
        response = await auth_client.get("/api/v1/projects/not-a-uuid")
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


class TestUpdateAndDelete:
    async def test_patches_only_the_supplied_fields(
        self, auth_client: AsyncClient, project: Project
    ):
        response = await auth_client.patch(
            f"/api/v1/projects/{project.id}", json={"status": "archived"}
        )
        assert response.status_code == HTTPStatus.OK

        body = response.json()
        assert body["status"] == "archived"
        assert body["name"] == project.name
        assert body["project_type"] == ProjectType.CARBON.value

    async def test_deletes_a_project(self, auth_client: AsyncClient, project: Project):
        assert (
            await auth_client.delete(f"/api/v1/projects/{project.id}")
        ).status_code == HTTPStatus.NO_CONTENT
        assert (
            await auth_client.get(f"/api/v1/projects/{project.id}")
        ).status_code == HTTPStatus.NOT_FOUND

    async def test_cannot_delete_another_users_project(
        self, auth_client: AsyncClient, session: AsyncSession, other_user: User
    ):
        foreign = Project(owner_id=other_user.id, name="Foreign Project")
        session.add(foreign)
        await session.flush()

        response = await auth_client.delete(f"/api/v1/projects/{foreign.id}")
        assert response.status_code == HTTPStatus.NOT_FOUND
