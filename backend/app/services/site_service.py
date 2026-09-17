"""Site business logic: geometry handling and metric backfill."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Any

from shapely.geometry.base import BaseGeometry
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidGeometryError, NotFoundError
from app.core.pagination import PaginationParams
from app.models.site import Site
from app.models.user import User
from app.repositories.metric_repo import MetricDefinitionRepository, SiteMetricRepository
from app.repositories.project_repo import ProjectRepository
from app.repositories.site_repo import SiteRepository
from app.schemas.common import Page
from app.schemas.geojson import Feature, FeatureCollection
from app.schemas.site import SiteCreate, SiteListItem, SiteRead, SiteUpdate
from app.services.providers import AnalyticsProvider, SiteContext, SyntheticAnalyticsProvider
from app.utils.geo import (
    MIN_AREA_SQUARE_METRES,
    SQUARE_METRES_PER_HECTARE,
    geojson_to_multipolygon,
    to_geojson_dict,
    to_wkb_element,
)

#: How far back a newly drawn site is backfilled with history, so the analytics
#: view has something to show the moment the polygon is saved.
BACKFILL_YEARS = 3


class SiteService:
    """Create and read sites, keeping geometry and metrics consistent."""

    def __init__(self, session: AsyncSession, provider: AnalyticsProvider | None = None) -> None:
        self.session = session
        self.sites = SiteRepository(session)
        self.projects = ProjectRepository(session)
        self.metric_defs = MetricDefinitionRepository(session)
        self.metrics = SiteMetricRepository(session)
        self.provider = provider or SyntheticAnalyticsProvider()

    # -- commands -------------------------------------------------------------

    async def create(self, owner: User, project_id: uuid.UUID, payload: SiteCreate) -> SiteRead:
        """Persist a drawn polygon as a site and backfill its metric history."""
        project = await self.projects.get_for_owner(project_id, owner.id)
        if project is None:
            raise NotFoundError("Project not found.", project_id=str(project_id))

        multipolygon = geojson_to_multipolygon(payload.geometry.model_dump())
        element = to_wkb_element(multipolygon)
        area_hectares, centroid = await self.sites.compute_geometry_facts(element)
        self._assert_minimum_area(area_hectares)

        site = await self.sites.add(
            Site(
                project_id=project.id,
                name=payload.name,
                description=payload.description,
                geometry=element,
                area_hectares=area_hectares,
                centroid=centroid,
            )
        )
        await self.backfill_metrics(site, multipolygon, start_date=project.start_date)
        return self._to_read(site)

    async def update(self, owner: User, site_id: uuid.UUID, payload: SiteUpdate) -> SiteRead:
        """Apply a partial update, recomputing geometry facts if it moved."""
        site = await self._require(owner, site_id)
        changes = payload.model_dump(exclude_unset=True)

        if (geometry := changes.pop("geometry", None)) is not None:
            multipolygon = geojson_to_multipolygon(geometry)
            element = to_wkb_element(multipolygon)
            area_hectares, centroid = await self.sites.compute_geometry_facts(element)
            self._assert_minimum_area(area_hectares)
            site.geometry = element
            site.area_hectares = area_hectares
            site.centroid = centroid

        self.sites.apply_updates(site, changes)
        await self.session.flush()
        await self.session.refresh(site)
        return self._to_read(site)

    async def delete(self, owner: User, site_id: uuid.UUID) -> None:
        """Delete a site and its metric history."""
        await self.sites.delete(await self._require(owner, site_id))

    async def backfill_metrics(
        self,
        site: Site,
        geometry: BaseGeometry,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> int:
        """Generate and store the site's metric time series.

        Returns:
            The number of samples inserted (zero if they already existed).
        """
        today = end_date or datetime.now(UTC).date()
        begin = start_date or date(today.year - BACKFILL_YEARS, today.month, 1)
        if begin > today:
            begin = date(today.year - BACKFILL_YEARS, today.month, 1)

        catalogue = await self.metric_defs.list_all()
        definitions = {definition.key: definition.id for definition in catalogue}
        samples = self.provider.generate(
            SiteContext(
                site_id=site.id,
                geometry=geometry,
                area_hectares=float(site.area_hectares),
                start_date=begin,
                end_date=today,
            )
        )
        rows = [
            {
                "site_id": site.id,
                "metric_id": definitions[sample.metric_key],
                "recorded_at": sample.recorded_at,
                "value": sample.value,
            }
            for sample in samples
            if sample.metric_key in definitions
        ]
        return await self.metrics.bulk_upsert(rows)

    # -- queries --------------------------------------------------------------

    async def get(self, owner: User, site_id: uuid.UUID) -> SiteRead:
        """Fetch one site with its full geometry."""
        return self._to_read(await self._require(owner, site_id))

    async def list_for_project(
        self, owner: User, project_id: uuid.UUID, pagination: PaginationParams
    ) -> Page[SiteListItem]:
        """List a project's sites without shipping their polygons."""
        project = await self.projects.get_for_owner(project_id, owner.id)
        if project is None:
            raise NotFoundError("Project not found.", project_id=str(project_id))

        sites, total = await self.sites.list_for_project(
            project.id, offset=pagination.offset, limit=pagination.limit
        )
        items = [
            SiteListItem(
                id=site.id,
                project_id=site.project_id,
                name=site.name,
                area_hectares=float(site.area_hectares),
                centroid=to_geojson_dict(site.centroid),
                created_at=site.created_at,
            )
            for site in sites
        ]
        return Page.create(items, total=total, page=pagination.page, size=pagination.size)

    async def feature_collection(
        self, owner: User, project_id: uuid.UUID | None = None
    ) -> FeatureCollection:
        """Every visible site as GeoJSON, which is what the map layer consumes.

        One request populates the whole map: shipping a FeatureCollection lets
        Mapbox own hit-testing and styling instead of us mounting a component
        per polygon.
        """
        sites = await self.sites.list_for_owner(owner.id)
        if project_id is not None:
            sites = [site for site in sites if site.project_id == project_id]

        features = [
            Feature(
                id=str(site.id),
                geometry=to_geojson_dict(site.geometry),
                properties={
                    "site_id": str(site.id),
                    "project_id": str(site.project_id),
                    "name": site.name,
                    "project_name": site.project.name,
                    "project_type": site.project.project_type.value,
                    "status": site.project.status.value,
                    "area_hectares": float(site.area_hectares),
                },
            )
            for site in sites
        ]
        box = (
            await self.sites.bounding_box_for_project(project_id)
            if project_id is not None
            else await self.sites.bounding_box_for_owner(owner.id)
        )
        return FeatureCollection(features=features, bbox=box.as_list() if box else None)

    # -- internals ------------------------------------------------------------

    async def _require(self, owner: User, site_id: uuid.UUID) -> Site:
        """Load a site the user may see, or raise 404."""
        site = await self.sites.get_for_owner(site_id, owner.id)
        if site is None:
            raise NotFoundError("Site not found.", site_id=str(site_id))
        return site

    @staticmethod
    def _assert_minimum_area(area_hectares: float) -> None:
        """Reject polygons too small to be a real parcel."""
        minimum = MIN_AREA_SQUARE_METRES / SQUARE_METRES_PER_HECTARE
        if area_hectares < minimum:
            raise InvalidGeometryError(
                f"Site area must be at least {MIN_AREA_SQUARE_METRES:.0f} m2.",
                area_hectares=area_hectares,
            )

    @staticmethod
    def _to_read(site: Site) -> SiteRead:
        """Serialise an ORM site, converting PostGIS geometry to GeoJSON."""
        payload: dict[str, Any] = {
            "id": site.id,
            "project_id": site.project_id,
            "name": site.name,
            "description": site.description,
            "geometry": to_geojson_dict(site.geometry),
            "centroid": to_geojson_dict(site.centroid),
            "area_hectares": float(site.area_hectares),
            "created_at": site.created_at,
            "updated_at": site.updated_at,
        }
        return SiteRead.model_validate(payload)
