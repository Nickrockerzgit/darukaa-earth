"""End-to-end tests for site creation and the map's GeoJSON feed."""

from __future__ import annotations

import uuid
from http import HTTPStatus
from typing import Any

import pytest
from httpx import AsyncClient

from app.models.project import Project

pytestmark = pytest.mark.integration

#: A 1 km x 1 km square at the equator is very close to 100 hectares, which
#: makes the PostGIS geography area calculation easy to sanity-check.
ONE_SQUARE_KM_AT_EQUATOR = {
    "type": "Polygon",
    "coordinates": [
        [
            [0.0, 0.0],
            [0.0089932, 0.0],
            [0.0089932, 0.0090437],
            [0.0, 0.0090437],
            [0.0, 0.0],
        ]
    ],
}


def _payload(geometry: dict[str, Any], name: str = "Drawn Site") -> dict[str, Any]:
    """Build a site-creation body."""
    return {"name": name, "description": "Drawn on the map.", "geometry": geometry}


class TestCreateSite:
    async def test_stores_a_drawn_polygon(
        self, auth_client: AsyncClient, project: Project, polygon_geojson: dict[str, Any]
    ):
        response = await auth_client.post(
            f"/api/v1/projects/{project.id}/sites", json=_payload(polygon_geojson)
        )
        assert response.status_code == HTTPStatus.CREATED

        body = response.json()
        assert body["project_id"] == str(project.id)
        # Polygons are normalised to MultiPolygon so the column has one type.
        assert body["geometry"]["type"] == "MultiPolygon"
        assert body["area_hectares"] > 0

    async def test_computes_area_in_hectares_on_the_spheroid(
        self, auth_client: AsyncClient, project: Project
    ):
        response = await auth_client.post(
            f"/api/v1/projects/{project.id}/sites", json=_payload(ONE_SQUARE_KM_AT_EQUATOR)
        )
        # Planar degrees would give a number nowhere near 100.
        assert response.json()["area_hectares"] == pytest.approx(100.0, rel=0.02)

    async def test_centroid_lies_inside_the_polygon(
        self, auth_client: AsyncClient, project: Project, polygon_geojson: dict[str, Any]
    ):
        body = (
            await auth_client.post(
                f"/api/v1/projects/{project.id}/sites", json=_payload(polygon_geojson)
            )
        ).json()
        lon, lat = body["centroid"]["coordinates"]
        assert 77.0 <= lon <= 77.01
        assert 12.0 <= lat <= 12.01

    async def test_accepts_a_multipolygon(
        self, auth_client: AsyncClient, project: Project, polygon_geojson: dict[str, Any]
    ):
        multi = {
            "type": "MultiPolygon",
            "coordinates": [
                polygon_geojson["coordinates"],
                [[[78.0, 12.0], [78.01, 12.0], [78.01, 12.01], [78.0, 12.01], [78.0, 12.0]]],
            ],
        }
        response = await auth_client.post(
            f"/api/v1/projects/{project.id}/sites", json=_payload(multi)
        )
        assert response.status_code == HTTPStatus.CREATED
        assert len(response.json()["geometry"]["coordinates"]) == 2

    async def test_backfills_metric_history(
        self, auth_client: AsyncClient, project: Project, polygon_geojson: dict[str, Any]
    ):
        site = (
            await auth_client.post(
                f"/api/v1/projects/{project.id}/sites", json=_payload(polygon_geojson)
            )
        ).json()

        analytics = await auth_client.get(f"/api/v1/sites/{site['id']}/analytics")
        assert analytics.status_code == HTTPStatus.OK
        series = analytics.json()["series"]
        assert series
        assert all(entry["points"] for entry in series)

    async def test_rejects_an_unclosed_ring(self, auth_client: AsyncClient, project: Project):
        unclosed = {
            "type": "Polygon",
            "coordinates": [[[0, 0], [0.01, 0], [0.01, 0.01], [0, 0.01]]],
        }
        response = await auth_client.post(
            f"/api/v1/projects/{project.id}/sites", json=_payload(unclosed)
        )
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    async def test_rejects_coordinates_outside_earth(
        self, auth_client: AsyncClient, project: Project
    ):
        off_planet = {
            "type": "Polygon",
            "coordinates": [[[0, 0], [500, 0], [500, 10], [0, 10], [0, 0]]],
        }
        response = await auth_client.post(
            f"/api/v1/projects/{project.id}/sites", json=_payload(off_planet)
        )
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    async def test_rejects_a_polygon_too_small_to_be_a_parcel(
        self, auth_client: AsyncClient, project: Project
    ):
        # Roughly a 1 m square: a mis-click, not a monitoring site.
        speck = {
            "type": "Polygon",
            "coordinates": [[[0, 0], [0.000009, 0], [0.000009, 0.000009], [0, 0.000009], [0, 0]]],
        }
        response = await auth_client.post(
            f"/api/v1/projects/{project.id}/sites", json=_payload(speck)
        )
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        assert response.json()["error"] == "invalid_geometry"

    async def test_cannot_add_a_site_to_an_unknown_project(
        self, auth_client: AsyncClient, polygon_geojson: dict[str, Any]
    ):
        response = await auth_client.post(
            f"/api/v1/projects/{uuid.uuid4()}/sites", json=_payload(polygon_geojson)
        )
        assert response.status_code == HTTPStatus.NOT_FOUND


class TestGeoJSONFeed:
    async def test_returns_a_feature_collection_with_a_bbox(
        self, auth_client: AsyncClient, project: Project, polygon_geojson: dict[str, Any]
    ):
        await auth_client.post(
            f"/api/v1/projects/{project.id}/sites", json=_payload(polygon_geojson)
        )

        body = (await auth_client.get("/api/v1/sites/geojson")).json()
        assert body["type"] == "FeatureCollection"
        assert len(body["features"]) == 1
        assert len(body["bbox"]) == 4

    async def test_features_carry_the_properties_the_map_styles_on(
        self, auth_client: AsyncClient, project: Project, polygon_geojson: dict[str, Any]
    ):
        await auth_client.post(
            f"/api/v1/projects/{project.id}/sites", json=_payload(polygon_geojson)
        )
        feature = (await auth_client.get("/api/v1/sites/geojson")).json()["features"][0]
        assert feature["properties"]["project_name"] == project.name
        assert feature["properties"]["project_type"] == project.project_type.value
        assert feature["properties"]["area_hectares"] > 0

    async def test_bbox_is_null_when_there_are_no_sites(self, auth_client: AsyncClient):
        body = (await auth_client.get("/api/v1/sites/geojson")).json()
        assert body["features"] == []
        assert body["bbox"] is None


class TestUpdateAndDelete:
    async def test_moving_a_site_recomputes_its_area(
        self, auth_client: AsyncClient, project: Project, polygon_geojson: dict[str, Any]
    ):
        site = (
            await auth_client.post(
                f"/api/v1/projects/{project.id}/sites", json=_payload(polygon_geojson)
            )
        ).json()

        response = await auth_client.patch(
            f"/api/v1/sites/{site['id']}", json={"geometry": ONE_SQUARE_KM_AT_EQUATOR}
        )
        assert response.status_code == HTTPStatus.OK
        assert response.json()["area_hectares"] == pytest.approx(100.0, rel=0.02)

    async def test_renaming_leaves_the_geometry_alone(
        self, auth_client: AsyncClient, project: Project, polygon_geojson: dict[str, Any]
    ):
        site = (
            await auth_client.post(
                f"/api/v1/projects/{project.id}/sites", json=_payload(polygon_geojson)
            )
        ).json()

        renamed = (
            await auth_client.patch(f"/api/v1/sites/{site['id']}", json={"name": "Renamed"})
        ).json()
        assert renamed["name"] == "Renamed"
        assert renamed["area_hectares"] == site["area_hectares"]

    async def test_deletes_a_site(
        self, auth_client: AsyncClient, project: Project, polygon_geojson: dict[str, Any]
    ):
        site = (
            await auth_client.post(
                f"/api/v1/projects/{project.id}/sites", json=_payload(polygon_geojson)
            )
        ).json()

        assert (
            await auth_client.delete(f"/api/v1/sites/{site['id']}")
        ).status_code == HTTPStatus.NO_CONTENT
        assert (
            await auth_client.get(f"/api/v1/sites/{site['id']}")
        ).status_code == HTTPStatus.NOT_FOUND
