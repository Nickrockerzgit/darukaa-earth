"""Data access for sites, including the PostGIS-side geometry computations."""

from __future__ import annotations

import uuid
from typing import Any, NamedTuple

from geoalchemy2 import Geography
from geoalchemy2.elements import WKBElement
from sqlalchemy import Select, cast, func, select
from sqlalchemy.orm import joinedload, noload

from app.models.project import Project
from app.models.site import Site
from app.repositories.base import BaseRepository
from app.utils.geo import SQUARE_METRES_PER_HECTARE


class BoundingBox(NamedTuple):
    """Axis-aligned extent in WGS84 degrees, ready for Mapbox ``fitBounds``."""

    min_lon: float
    min_lat: float
    max_lon: float
    max_lat: float

    def as_list(self) -> list[float]:
        """Serialise as the GeoJSON ``bbox`` array."""
        return [self.min_lon, self.min_lat, self.max_lon, self.max_lat]


class SiteRepository(BaseRepository[Site]):
    """Queries over the ``sites`` table."""

    model = Site

    def _owned(self, owner_id: uuid.UUID) -> Select[tuple[Site]]:
        """Base SELECT limited to sites whose parent project the user owns."""
        return (
            select(Site)
            .join(Project, Project.id == Site.project_id)
            .where(Project.owner_id == owner_id)
        )

    async def get_for_owner(self, site_id: uuid.UUID, owner_id: uuid.UUID) -> Site | None:
        """Fetch a site the caller is allowed to see."""
        statement = (
            self._owned(owner_id).where(Site.id == site_id).options(joinedload(Site.project))
        )
        result = await self.session.execute(statement)
        return result.scalars().unique().first()

    async def list_for_project(
        self, project_id: uuid.UUID, *, offset: int = 0, limit: int = 100
    ) -> tuple[list[Site], int]:
        """Return one page of a project's sites plus the total count."""
        base = select(Site).where(Site.project_id == project_id)
        total = await self.count(base)
        statement = (
            base.order_by(Site.created_at.desc())
            .offset(offset)
            .limit(limit)
            .options(noload(Site.project))
        )
        result = await self.session.execute(statement)
        return list(result.scalars().unique().all()), total

    async def list_for_owner(self, owner_id: uuid.UUID) -> list[Site]:
        """Every site visible to the user - the map's single data source."""
        statement = self._owned(owner_id).options(joinedload(Site.project)).order_by(Site.name)
        result = await self.session.execute(statement)
        return list(result.scalars().unique().all())

    async def compute_geometry_facts(self, geometry: WKBElement) -> tuple[float, Any]:
        """Ask PostGIS for the area (hectares) and an interior point.

        Area is computed on the ``geography`` type, which measures on the
        spheroid in real metres. Doing the same maths on the raw ``geometry``
        would return square degrees, whose size varies with latitude.

        ``ST_PointOnSurface`` (not ``ST_Centroid``) guarantees the returned
        point lies inside the polygon even when it is concave or multi-part.
        """
        statement = select(
            func.ST_Area(cast(geometry, Geography)) / SQUARE_METRES_PER_HECTARE,
            func.ST_PointOnSurface(geometry),
        )
        area_hectares, centroid = (await self.session.execute(statement)).one()
        return float(area_hectares), centroid

    async def bounding_box_for_owner(self, owner_id: uuid.UUID) -> BoundingBox | None:
        """Extent of every site the user owns, or ``None`` when they have none."""
        statement = (
            select(func.ST_Extent(Site.geometry))
            .join(Project, Project.id == Site.project_id)
            .where(Project.owner_id == owner_id)
        )
        extent = await self.session.scalar(statement)
        return _parse_extent(extent)

    async def bounding_box_for_project(self, project_id: uuid.UUID) -> BoundingBox | None:
        """Extent of a single project's sites."""
        statement = select(func.ST_Extent(Site.geometry)).where(Site.project_id == project_id)
        return _parse_extent(await self.session.scalar(statement))


def _parse_extent(extent: str | None) -> BoundingBox | None:
    """Parse the ``BOX(minx miny,maxx maxy)`` string ST_Extent returns."""
    if not extent:
        return None
    inner = extent.removeprefix("BOX(").removesuffix(")")
    try:
        low, high = inner.split(",")
        min_lon, min_lat = (float(part) for part in low.split())
        max_lon, max_lat = (float(part) for part in high.split())
    except ValueError:
        return None
    return BoundingBox(min_lon, min_lat, max_lon, max_lat)
