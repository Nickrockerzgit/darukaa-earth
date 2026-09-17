"""Site request/response schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel
from app.schemas.geojson import AreaGeometry, Point


class SiteCreate(BaseModel):
    """Payload for adding a site, produced directly by the map draw tool."""

    name: str = Field(min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=4000)
    geometry: AreaGeometry = Field(
        description="GeoJSON Polygon or MultiPolygon in WGS84 (EPSG:4326)"
    )


class SiteUpdate(BaseModel):
    """Partial update payload for a site."""

    name: str | None = Field(default=None, min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=4000)
    geometry: AreaGeometry | None = None


class SiteRead(ORMModel):
    """A site as returned by the API, geometry included."""

    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    description: str | None
    geometry: AreaGeometry
    centroid: Point
    area_hectares: float
    created_at: datetime
    updated_at: datetime


class SiteListItem(ORMModel):
    """Lightweight site row for lists - geometry omitted to keep payloads small."""

    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    area_hectares: float
    centroid: Point
    created_at: datetime
