import type { Position } from 'geojson';

import type { AreaGeometry } from '@/types/api';

/**
 * Every coordinate of a Polygon or MultiPolygon, flattened.
 *
 * `Array.prototype.flat` cannot do this in a type-safe way across the union:
 * a Polygon nests three deep and a MultiPolygon four, so a single `flat(n)`
 * is wrong for one of them.
 */
export function positionsOf(geometry: AreaGeometry): Position[] {
  if (geometry.type === 'Polygon') {
    return geometry.coordinates.flat();
  }
  return geometry.coordinates.flat(2);
}

/**
 * Mean of a geometry's vertices.
 *
 * Good enough as a camera target, which is all it is used for. Anything that
 * must land *inside* the polygon uses the `centroid` the API computes with
 * PostGIS `ST_PointOnSurface`.
 */
export function averagePosition(geometry: AreaGeometry): [number, number] {
  const positions = positionsOf(geometry);
  if (positions.length === 0) return [0, 0];

  let sumLon = 0;
  let sumLat = 0;
  for (const [longitude, latitude] of positions) {
    // GeoJSON guarantees at least two ordinates; the fallbacks exist only to
    // satisfy noUncheckedIndexedAccess.
    sumLon += longitude ?? 0;
    sumLat += latitude ?? 0;
  }
  return [sumLon / positions.length, sumLat / positions.length];
}
