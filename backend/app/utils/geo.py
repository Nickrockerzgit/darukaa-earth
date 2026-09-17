"""Geometry conversion helpers bridging GeoJSON, Shapely and PostGIS.

Keeping every conversion in one module means the rest of the codebase never
has to think about SRIDs, ring winding, or Polygon-vs-MultiPolygon coercion.
"""

from __future__ import annotations

from typing import Any

from geoalchemy2.elements import WKBElement
from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import MultiPolygon, Polygon, mapping, shape
from shapely.geometry.base import BaseGeometry
from shapely.validation import explain_validity, make_valid

from app.core.exceptions import InvalidGeometryError
from app.models.site import SRID

#: Square metres in one hectare.
SQUARE_METRES_PER_HECTARE = 10_000.0
#: Reject degenerate polygons that are almost certainly mis-clicks rather than
#: real parcels. 100 m2 is a 10 m x 10 m square.
MIN_AREA_SQUARE_METRES = 100.0

_SUPPORTED_TYPES = {"Polygon", "MultiPolygon"}


def geojson_to_multipolygon(geometry: dict[str, Any]) -> MultiPolygon:
    """Convert a GeoJSON geometry mapping into a valid Shapely ``MultiPolygon``.

    A single ``Polygon`` is promoted to a one-member ``MultiPolygon`` so the
    database column has exactly one geometry type to deal with.

    Raises:
        InvalidGeometryError: if the type is unsupported, the geometry cannot
            be repaired into polygonal form, or it is empty.
    """
    geom_type = geometry.get("type")
    if geom_type not in _SUPPORTED_TYPES:
        raise InvalidGeometryError(
            f"Unsupported geometry type {geom_type!r}; expected Polygon or MultiPolygon.",
            geometry_type=geom_type,
        )

    try:
        parsed: BaseGeometry = shape(geometry)
    except (AttributeError, KeyError, TypeError, ValueError) as exc:
        raise InvalidGeometryError(f"Geometry could not be parsed: {exc}") from exc

    if parsed.is_empty:
        raise InvalidGeometryError("Geometry is empty.")

    if not parsed.is_valid:
        # Self-intersections are common when a user draws quickly; repair
        # rather than reject, but surface the original reason if repair fails.
        reason = explain_validity(parsed)
        parsed = make_valid(parsed)
        if parsed.is_empty:
            raise InvalidGeometryError(f"Geometry is invalid and unrepairable: {reason}")

    polygonal = _extract_polygons(parsed)
    if not polygonal:
        raise InvalidGeometryError("Geometry contains no polygonal component.")
    return MultiPolygon(polygonal)


def _extract_polygons(geom: BaseGeometry) -> list[Polygon]:
    """Collect the polygonal parts of a possibly mixed geometry."""
    if isinstance(geom, Polygon):
        return [geom] if not geom.is_empty else []
    if isinstance(geom, MultiPolygon):
        return [part for part in geom.geoms if isinstance(part, Polygon) and not part.is_empty]
    # make_valid() can hand back a GeometryCollection mixing lines and polygons.
    parts = getattr(geom, "geoms", [])
    return [part for part in parts if isinstance(part, Polygon) and not part.is_empty]


def to_wkb_element(geom: BaseGeometry) -> WKBElement:
    """Convert a Shapely geometry into a SRID-tagged value for SQLAlchemy."""
    return from_shape(geom, srid=SRID)


def to_geojson_dict(element: WKBElement | BaseGeometry | None) -> dict[str, Any] | None:
    """Convert a stored PostGIS value back into a GeoJSON geometry mapping."""
    if element is None:
        return None
    geom = element if isinstance(element, BaseGeometry) else to_shape(element)
    return dict(mapping(geom))


def point_on_surface(geom: BaseGeometry) -> Any:
    """Return a representative point guaranteed to lie inside ``geom``.

    ``centroid`` can fall outside a concave or multi-part polygon, which would
    make the map fly to empty ocean; ``representative_point`` cannot.
    """
    return geom.representative_point()
