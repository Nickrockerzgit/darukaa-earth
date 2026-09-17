import { describe, expect, it } from 'vitest';

import { averagePosition, positionsOf } from '@/lib/geometry';
import type { AreaGeometry } from '@/types/api';

const SQUARE: AreaGeometry = {
  type: 'Polygon',
  coordinates: [
    [
      [0, 0],
      [2, 0],
      [2, 2],
      [0, 2],
      [0, 0],
    ],
  ],
};

const TWO_SQUARES: AreaGeometry = {
  type: 'MultiPolygon',
  coordinates: [
    SQUARE.coordinates,
    [
      [
        [10, 10],
        [12, 10],
        [12, 12],
        [10, 12],
        [10, 10],
      ],
    ],
  ],
};

describe('positionsOf', () => {
  it('flattens a Polygon to its positions', () => {
    expect(positionsOf(SQUARE)).toHaveLength(5);
  });

  it('flattens a MultiPolygon across all its parts', () => {
    // A single flat(n) is wrong for one of the two shapes, which is the bug
    // this function exists to prevent.
    expect(positionsOf(TWO_SQUARES)).toHaveLength(10);
  });

  it('returns pairs, not nested arrays', () => {
    const [first] = positionsOf(SQUARE);
    expect(first).toEqual([0, 0]);
  });
});

describe('averagePosition', () => {
  it('averages a simple square around its middle', () => {
    const [lon, lat] = averagePosition(SQUARE);
    expect(lon).toBeCloseTo(0.8, 5);
    expect(lat).toBeCloseTo(0.8, 5);
  });

  it('falls between the parts of a MultiPolygon', () => {
    const [lon, lat] = averagePosition(TWO_SQUARES);
    expect(lon).toBeGreaterThan(0);
    expect(lon).toBeLessThan(12);
    expect(lat).toBeGreaterThan(0);
    expect(lat).toBeLessThan(12);
  });

  it('returns the origin for an empty geometry rather than NaN', () => {
    expect(averagePosition({ type: 'Polygon', coordinates: [] })).toEqual([0, 0]);
  });
});
