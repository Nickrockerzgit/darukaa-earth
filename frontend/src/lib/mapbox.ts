/**
 * Mapbox layer styling and view helpers.
 *
 * Site polygons are rendered by Mapbox itself from one GeoJSON source rather
 * than as React components. That keeps hit-testing, label collision and
 * zoom-dependent styling on the GPU, and means a project with 500 sites costs
 * the same number of React nodes as one with 5.
 */

import type { LayerProps } from 'react-map-gl';

import { env } from '@/lib/env';
import type { ProjectType, SiteBBox } from '@/types/api';

export const SITES_SOURCE_ID = 'darukaa-sites';
export const SITES_FILL_LAYER_ID = 'darukaa-sites-fill';
export const SITES_OUTLINE_LAYER_ID = 'darukaa-sites-outline';
export const SITES_LABEL_LAYER_ID = 'darukaa-sites-label';

/** Fill colours by project type, matching the chart category palette. */
export const PROJECT_TYPE_COLOR: Record<ProjectType, string> = {
  carbon: '#37d9a0',
  biodiversity: '#5fb5f0',
  mixed: '#b48ff0',
};

/** A world-ish default view for a brand-new account with no sites yet. */
export const DEFAULT_VIEW_STATE = {
  longitude: 20,
  latitude: 15,
  zoom: 1.4,
} as const;

export const MAP_STYLE = env.mapboxStyle;

/**
 * A Mapbox data-driven `match` expression mapping `project_type` to a colour.
 * Evaluated per feature inside the style, so no per-feature React work.
 */
const projectTypeColor = [
  'match',
  ['get', 'project_type'],
  'carbon',
  PROJECT_TYPE_COLOR.carbon,
  'biodiversity',
  PROJECT_TYPE_COLOR.biodiversity,
  'mixed',
  PROJECT_TYPE_COLOR.mixed,
  PROJECT_TYPE_COLOR.carbon,
];

export const sitesFillLayer: LayerProps = {
  id: SITES_FILL_LAYER_ID,
  type: 'fill',
  source: SITES_SOURCE_ID,
  paint: {
    'fill-color': projectTypeColor as unknown as string,
    // Selected and hovered states are expressed in the style rather than by
    // swapping sources, so they cost one repaint instead of a data reload.
    'fill-opacity': [
      'case',
      ['boolean', ['feature-state', 'selected'], false],
      0.55,
      ['boolean', ['feature-state', 'hover'], false],
      0.38,
      0.22,
    ],
  },
};

export const sitesOutlineLayer: LayerProps = {
  id: SITES_OUTLINE_LAYER_ID,
  type: 'line',
  source: SITES_SOURCE_ID,
  paint: {
    'line-color': projectTypeColor as unknown as string,
    'line-width': ['case', ['boolean', ['feature-state', 'selected'], false], 3, 1.5],
    'line-opacity': 0.95,
  },
};

export const sitesLabelLayer: LayerProps = {
  id: SITES_LABEL_LAYER_ID,
  type: 'symbol',
  source: SITES_SOURCE_ID,
  // Labels are noise when the whole country fits on screen.
  minzoom: 8,
  layout: {
    'text-field': ['get', 'name'],
    'text-size': 12,
    'text-anchor': 'center',
    'text-allow-overlap': false,
  },
  paint: {
    'text-color': '#f2f4f7',
    'text-halo-color': '#10141a',
    'text-halo-width': 1.4,
  },
};

/** Mapbox `fitBounds` corners: `[[west, south], [east, north]]`. */
export type BoundsTuple = [[number, number], [number, number]];

/**
 * Convert the API's `bbox` into `fitBounds` corners.
 *
 * Returns `null` for a degenerate box (a single site collapses to a point at
 * low precision), where `fitBounds` would zoom to maximum and disorient the user.
 */
export function bboxToBounds(bbox: SiteBBox): BoundsTuple | null {
  // GeoJSON allows a 6-element 3D bbox; the API only ever sends the 2D form.
  if (bbox == null || bbox.length !== 4) return null;
  const [west, south, east, north] = bbox;
  if (west === east && south === north) return null;
  return [
    [west, south],
    [east, north],
  ];
}

/** A small padded box around a point, for flying to a single site. */
export function pointToBounds(
  longitude: number,
  latitude: number,
  paddingDegrees = 0.02,
): BoundsTuple {
  return [
    [longitude - paddingDegrees, latitude - paddingDegrees],
    [longitude + paddingDegrees, latitude + paddingDegrees],
  ];
}
