# ADR-0002: Geometry storage and area computation

**Status:** Accepted · **Date:** 2026-09-18

## Context

Users draw polygons on a Mapbox map. Those polygons must be stored, queried
spatially, and reported with an area a user can sanity-check against a land title.

## Decisions

### Store `geometry(MultiPolygon, 4326)`

SRID 4326 (WGS84 lon/lat degrees) is what GeoJSON specifies and what Mapbox GL
emits, so nothing has to reproject at the API boundary.

MultiPolygon rather than Polygon: a site can legitimately be several disjoint
parcels. A single Polygon promoted to a one-member MultiPolygon on write means
the column has exactly one geometry type and no downstream code branches.

### Compute area on `geography`, not `geometry`

```sql
ST_Area(geometry::geography) / 10000  -- hectares
```

`ST_Area` on a 4326 `geometry` returns **square degrees**, which is meaningless:
a degree of longitude is 111 km at the equator and 0 km at the pole. The
`geography` cast measures on the spheroid in real square metres. The integration
test `test_computes_area_in_hectares_on_the_spheroid` asserts that a 1 km × 1 km
square at the equator comes back as ~100 ha, which fails loudly if the cast is
ever dropped.

### Denormalise `area_hectares` and `centroid`

Both are written once, at insert, and recomputed only when the geometry changes.
They appear in every list response; recomputing them per request would dominate
the query cost of values that rarely change.

### Use `ST_PointOnSurface`, not `ST_Centroid`

A centroid can fall outside a concave or multi-part polygon. The map uses this
point to fly to a site, so an outside point means flying to open ocean.
`ST_PointOnSurface` is guaranteed to be inside.

### Repair rather than reject invalid geometry

Users draw self-intersecting "bow-tie" polygons constantly. `shapely.make_valid`
repairs them; only an unrepairable or non-polygonal result is rejected. Polygons
under 100 m² are rejected as mis-clicks rather than parcels.

## Rejected

**A projected CRS such as Web Mercator (3857).** Area in Mercator is wildly
distorted away from the equator — a Finnish site would read several times its
real size. A per-site UTM zone would be accurate but adds a reprojection step
and a zone-boundary edge case for a value `geography` already gives correctly.

**Computing area in Shapely.** Shapely is planar and would return square
degrees. PostGIS already has the spheroid maths.

## Cost

- Area is approximate near the poles and for sites spanning the antimeridian.
- A moved polygon needs its denormalised values recomputed; `SiteService.update`
  is the single place that does it, so it cannot be forgotten in one code path.
