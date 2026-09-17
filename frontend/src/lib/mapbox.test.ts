import { describe, expect, it } from 'vitest';

import { bboxToBounds, pointToBounds, PROJECT_TYPE_COLOR } from '@/lib/mapbox';

describe('bboxToBounds', () => {
  it('converts a bbox into fitBounds corners', () => {
    expect(bboxToBounds([77, 12, 78, 13])).toEqual([
      [77, 12],
      [78, 13],
    ]);
  });

  it('returns null when there is no bbox', () => {
    expect(bboxToBounds(null)).toBeNull();
    expect(bboxToBounds(undefined)).toBeNull();
  });

  it('returns null for a degenerate box', () => {
    // fitBounds on a zero-area box zooms to maximum and disorients the user.
    expect(bboxToBounds([77, 12, 77, 12])).toBeNull();
  });

  it('ignores a 3D bbox, which the API never sends', () => {
    expect(bboxToBounds([77, 12, 0, 78, 13, 100])).toBeNull();
  });

  it('handles a bbox spanning the antimeridian region without throwing', () => {
    expect(bboxToBounds([-179, -10, 179, 10])).toEqual([
      [-179, -10],
      [179, 10],
    ]);
  });
});

describe('pointToBounds', () => {
  it('pads a point into a small box', () => {
    expect(pointToBounds(77, 12, 0.01)).toEqual([
      [76.99, 11.99],
      [77.01, 12.01],
    ]);
  });
});

describe('PROJECT_TYPE_COLOR', () => {
  it('assigns a distinct colour to every project type', () => {
    const colours = Object.values(PROJECT_TYPE_COLOR);
    expect(new Set(colours).size).toBe(colours.length);
  });
});
