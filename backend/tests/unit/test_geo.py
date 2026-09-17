"""Tests for GeoJSON parsing, repair and conversion."""

from __future__ import annotations

import pytest
from shapely.geometry import MultiPolygon

from app.core.exceptions import InvalidGeometryError
from app.utils.geo import geojson_to_multipolygon, to_geojson_dict, to_wkb_element

SQUARE = {
    "type": "Polygon",
    "coordinates": [[[0.0, 0.0], [0.01, 0.0], [0.01, 0.01], [0.0, 0.01], [0.0, 0.0]]],
}


class TestGeoJSONToMultiPolygon:
    def test_promotes_a_polygon_to_a_multipolygon(self):
        result = geojson_to_multipolygon(SQUARE)
        assert isinstance(result, MultiPolygon)
        assert len(result.geoms) == 1

    def test_keeps_every_part_of_a_multipolygon(self):
        two_parts = {
            "type": "MultiPolygon",
            "coordinates": [
                SQUARE["coordinates"],
                [[[1.0, 1.0], [1.01, 1.0], [1.01, 1.01], [1.0, 1.01], [1.0, 1.0]]],
            ],
        }
        assert len(geojson_to_multipolygon(two_parts).geoms) == 2

    def test_repairs_a_self_intersecting_polygon(self):
        # A bow-tie: users draw these constantly by crossing their own edges.
        bowtie = {
            "type": "Polygon",
            "coordinates": [[[0, 0], [1, 1], [1, 0], [0, 1], [0, 0]]],
        }
        result = geojson_to_multipolygon(bowtie)
        assert result.is_valid
        assert not result.is_empty

    def test_rejects_a_non_polygonal_type(self):
        with pytest.raises(InvalidGeometryError, match="Unsupported geometry type"):
            geojson_to_multipolygon({"type": "LineString", "coordinates": [[0, 0], [1, 1]]})

    def test_rejects_an_empty_polygon(self):
        with pytest.raises(InvalidGeometryError, match="empty"):
            geojson_to_multipolygon({"type": "Polygon", "coordinates": []})

    def test_rejects_a_degenerate_ring(self):
        # A ring collapsed onto a single line has no polygonal component.
        degenerate = {
            "type": "Polygon",
            "coordinates": [[[0, 0], [1, 1], [0, 0], [0, 0]]],
        }
        with pytest.raises(InvalidGeometryError):
            geojson_to_multipolygon(degenerate)


class TestConversions:
    def test_round_trips_through_wkb(self):
        original = geojson_to_multipolygon(SQUARE)
        restored = to_geojson_dict(to_wkb_element(original))
        assert restored is not None
        assert restored["type"] == "MultiPolygon"

    def test_none_converts_to_none(self):
        assert to_geojson_dict(None) is None

    def test_shapely_geometry_converts_directly(self):
        result = to_geojson_dict(geojson_to_multipolygon(SQUARE))
        assert result is not None
        assert result["type"] == "MultiPolygon"
