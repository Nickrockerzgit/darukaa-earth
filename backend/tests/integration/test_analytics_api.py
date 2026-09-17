"""End-to-end tests for the analytics endpoints."""

from __future__ import annotations

import uuid
from http import HTTPStatus
from typing import Any

import pytest
from httpx import AsyncClient

from app.models.project import Project

pytestmark = pytest.mark.integration


@pytest.fixture
async def site(
    auth_client: AsyncClient, project: Project, polygon_geojson: dict[str, Any]
) -> dict[str, Any]:
    """A created site with its metric history backfilled."""
    response = await auth_client.post(
        f"/api/v1/projects/{project.id}/sites",
        json={"name": "Analytics Site", "geometry": polygon_geojson},
    )
    assert response.status_code == HTTPStatus.CREATED
    return dict(response.json())


class TestMetricCatalogue:
    async def test_lists_the_catalogue(self, auth_client: AsyncClient):
        response = await auth_client.get("/api/v1/metrics")
        assert response.status_code == HTTPStatus.OK

        body = response.json()
        assert len(body) >= 6
        assert {"carbon_sequestered_tco2e", "ndvi", "biodiversity_index"} <= {
            item["key"] for item in body
        }

    async def test_entries_carry_their_unit_and_aggregation(self, auth_client: AsyncClient):
        body = (await auth_client.get("/api/v1/metrics")).json()
        sequestration = next(item for item in body if item["key"] == "carbon_sequestered_tco2e")
        assert sequestration["unit"] == "tCO2e"
        # A flow must sum across buckets, not average.
        assert sequestration["aggregation"] == "sum"

    async def test_is_returned_in_display_order(self, auth_client: AsyncClient):
        body = (await auth_client.get("/api/v1/metrics")).json()
        orders = [item["display_order"] for item in body]
        assert orders == sorted(orders)

    async def test_requires_authentication(self, client: AsyncClient):
        assert (await client.get("/api/v1/metrics")).status_code == HTTPStatus.UNAUTHORIZED


class TestSiteSeries:
    async def test_returns_every_metric_by_default(
        self, auth_client: AsyncClient, site: dict[str, Any]
    ):
        body = (await auth_client.get(f"/api/v1/sites/{site['id']}/analytics")).json()
        assert len(body["series"]) >= 6
        assert body["interval"] == "month"

    async def test_can_request_a_subset(self, auth_client: AsyncClient, site: dict[str, Any]):
        body = (
            await auth_client.get(
                f"/api/v1/sites/{site['id']}/analytics?metrics=ndvi&metrics=canopy_cover_pct"
            )
        ).json()
        assert {entry["metric_key"] for entry in body["series"]} == {
            "ndvi",
            "canopy_cover_pct",
        }

    async def test_rejects_an_unknown_metric_key(
        self, auth_client: AsyncClient, site: dict[str, Any]
    ):
        response = await auth_client.get(
            f"/api/v1/sites/{site['id']}/analytics?metrics=not_a_metric"
        )
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        assert response.json()["error"] == "validation_error"

    async def test_points_are_chronological(self, auth_client: AsyncClient, site: dict[str, Any]):
        body = (await auth_client.get(f"/api/v1/sites/{site['id']}/analytics")).json()
        for entry in body["series"]:
            dates = [point["t"] for point in entry["points"]]
            assert dates == sorted(dates)

    async def test_yearly_buckets_are_coarser_than_monthly(
        self, auth_client: AsyncClient, site: dict[str, Any]
    ):
        monthly = (
            await auth_client.get(
                f"/api/v1/sites/{site['id']}/analytics?metrics=ndvi&interval=month"
            )
        ).json()
        yearly = (
            await auth_client.get(
                f"/api/v1/sites/{site['id']}/analytics?metrics=ndvi&interval=year"
            )
        ).json()
        assert len(yearly["series"][0]["points"]) < len(monthly["series"][0]["points"])

    async def test_flows_sum_while_stocks_average(
        self, auth_client: AsyncClient, site: dict[str, Any]
    ):
        # Rolling months into years must add sequestration but average NDVI.
        monthly = (
            await auth_client.get(
                f"/api/v1/sites/{site['id']}/analytics"
                "?metrics=carbon_sequestered_tco2e&metrics=ndvi&interval=month"
            )
        ).json()
        yearly = (
            await auth_client.get(
                f"/api/v1/sites/{site['id']}/analytics"
                "?metrics=carbon_sequestered_tco2e&metrics=ndvi&interval=year"
            )
        ).json()

        def peak(payload: dict[str, Any], key: str) -> float:
            entry = next(e for e in payload["series"] if e["metric_key"] == key)
            return max(point["v"] for point in entry["points"])

        assert peak(yearly, "carbon_sequestered_tco2e") > peak(monthly, "carbon_sequestered_tco2e")
        assert peak(yearly, "ndvi") <= peak(monthly, "ndvi") + 1e-6

    async def test_rejects_an_inverted_date_window(
        self, auth_client: AsyncClient, site: dict[str, Any]
    ):
        response = await auth_client.get(
            f"/api/v1/sites/{site['id']}/analytics?date_from=2025-01-01&date_to=2024-01-01"
        )
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    async def test_unknown_site_is_not_found(self, auth_client: AsyncClient):
        response = await auth_client.get(f"/api/v1/sites/{uuid.uuid4()}/analytics")
        assert response.status_code == HTTPStatus.NOT_FOUND


class TestSiteSummary:
    async def test_returns_a_snapshot_per_metric(
        self, auth_client: AsyncClient, site: dict[str, Any]
    ):
        body = (await auth_client.get(f"/api/v1/sites/{site['id']}/analytics/summary")).json()
        assert body["site_name"] == "Analytics Site"
        assert len(body["snapshots"]) >= 6

    async def test_snapshots_carry_a_change_percentage(
        self, auth_client: AsyncClient, site: dict[str, Any]
    ):
        body = (await auth_client.get(f"/api/v1/sites/{site['id']}/analytics/summary")).json()
        assert all(snapshot["previous_value"] is not None for snapshot in body["snapshots"])
        assert any(snapshot["change_pct"] is not None for snapshot in body["snapshots"])


class TestProjectSummary:
    async def test_aggregates_across_sites(
        self,
        auth_client: AsyncClient,
        project: Project,
        site: dict[str, Any],
    ):
        second = {
            "type": "Polygon",
            "coordinates": [
                [[78.0, 12.0], [78.01, 12.0], [78.01, 12.01], [78.0, 12.01], [78.0, 12.0]]
            ],
        }
        await auth_client.post(
            f"/api/v1/projects/{project.id}/sites",
            json={"name": "Second Site", "geometry": second},
        )

        body = (await auth_client.get(f"/api/v1/projects/{project.id}/summary")).json()
        assert body["site_count"] == 2
        assert body["total_area_hectares"] > site["area_hectares"]
        assert "carbon_sequestered_tco2e" in body["latest_metrics"]

    async def test_is_empty_for_a_project_without_sites(
        self, auth_client: AsyncClient, project: Project
    ):
        body = (await auth_client.get(f"/api/v1/projects/{project.id}/summary")).json()
        assert body["site_count"] == 0
        assert body["latest_metrics"] == {}
