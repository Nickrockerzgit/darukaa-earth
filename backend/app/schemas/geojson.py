"""Typed GeoJSON models (RFC 7946 subset).

Validating geometry at the schema boundary means a malformed polygon is
rejected with a 422 and a precise field path, before it ever reaches PostGIS.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

#: [longitude, latitude] in WGS84 degrees.
Position = Annotated[list[float], Field(min_length=2, max_length=3)]
LinearRing = Annotated[list[Position], Field(min_length=4)]
PolygonCoordinates = Annotated[list[LinearRing], Field(min_length=1)]

MIN_RING_POSITIONS = 4
LON_BOUNDS = (-180.0, 180.0)
LAT_BOUNDS = (-90.0, 90.0)


def _validate_ring(ring: list[list[float]], path: str) -> None:
    """Assert a linear ring is closed and inside valid lon/lat bounds."""
    if len(ring) < MIN_RING_POSITIONS:
        msg = f"{path}: a linear ring needs at least {MIN_RING_POSITIONS} positions"
        raise ValueError(msg)
    if ring[0][:2] != ring[-1][:2]:
        msg = f"{path}: linear ring must be closed (first position must equal last)"
        raise ValueError(msg)
    for index, (lon, lat, *_rest) in enumerate(ring):
        if not LON_BOUNDS[0] <= lon <= LON_BOUNDS[1]:
            msg = f"{path}[{index}]: longitude {lon} outside {LON_BOUNDS}"
            raise ValueError(msg)
        if not LAT_BOUNDS[0] <= lat <= LAT_BOUNDS[1]:
            msg = f"{path}[{index}]: latitude {lat} outside {LAT_BOUNDS}"
            raise ValueError(msg)


class Polygon(BaseModel):
    """GeoJSON Polygon geometry."""

    type: Literal["Polygon"] = "Polygon"
    coordinates: PolygonCoordinates

    @field_validator("coordinates")
    @classmethod
    def _check_rings(cls, value: list[list[list[float]]]) -> list[list[list[float]]]:
        for ring_index, ring in enumerate(value):
            _validate_ring(ring, f"coordinates[{ring_index}]")
        return value


class MultiPolygon(BaseModel):
    """GeoJSON MultiPolygon geometry."""

    type: Literal["MultiPolygon"] = "MultiPolygon"
    coordinates: Annotated[list[PolygonCoordinates], Field(min_length=1)]

    @field_validator("coordinates")
    @classmethod
    def _check_rings(cls, value: list[list[list[list[float]]]]) -> list[list[list[list[float]]]]:
        for poly_index, polygon in enumerate(value):
            for ring_index, ring in enumerate(polygon):
                _validate_ring(ring, f"coordinates[{poly_index}][{ring_index}]")
        return value


class Point(BaseModel):
    """GeoJSON Point geometry."""

    type: Literal["Point"] = "Point"
    coordinates: Position


AreaGeometry = Annotated[Polygon | MultiPolygon, Field(discriminator="type")]


class Feature(BaseModel):
    """GeoJSON Feature wrapping a geometry plus arbitrary properties."""

    type: Literal["Feature"] = "Feature"
    id: str | None = None
    geometry: AreaGeometry
    properties: dict[str, Any] = Field(default_factory=dict)


class FeatureCollection(BaseModel):
    """GeoJSON FeatureCollection, the payload the map layer consumes."""

    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[Feature] = Field(default_factory=list)
    bbox: list[float] | None = Field(
        default=None,
        description="[minLon, minLat, maxLon, maxLat] of all features, for fitBounds",
    )

    @model_validator(mode="after")
    def _check_bbox(self) -> FeatureCollection:
        expected = 4
        if self.bbox is not None and len(self.bbox) != expected:
            msg = "bbox must be [minLon, minLat, maxLon, maxLat]"
            raise ValueError(msg)
        return self
