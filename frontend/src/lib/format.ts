/** Display formatting helpers, so numbers and dates look the same everywhere. */

import { format, parseISO } from 'date-fns';

const COMPACT_THRESHOLD = 10_000;

/**
 * Format a metric value for display.
 *
 * Large values switch to compact notation (`12.4K`) because a KPI tile has no
 * room for `12,431.57`, while small values keep two decimals so a change from
 * 0.52 to 0.54 NDVI is actually visible.
 */
export function formatMetricValue(value: number, unit?: string): string {
  const absolute = Math.abs(value);
  const formatted =
    absolute >= COMPACT_THRESHOLD
      ? new Intl.NumberFormat('en', { notation: 'compact', maximumFractionDigits: 1 }).format(value)
      : new Intl.NumberFormat('en', {
          minimumFractionDigits: absolute < 10 ? 2 : 0,
          maximumFractionDigits: absolute < 10 ? 2 : 1,
        }).format(value);

  if (!unit) return formatted;
  // A percentage sign hugs its number; a word unit needs the space.
  return unit === '%' ? `${formatted}%` : `${formatted} ${unit}`;
}

/** Format an area in hectares, promoting very large areas to km2. */
export function formatArea(hectares: number): string {
  const SQUARE_KM_THRESHOLD = 10_000;
  if (hectares >= SQUARE_KM_THRESHOLD) {
    return `${new Intl.NumberFormat('en', { maximumFractionDigits: 1 }).format(hectares / 100)} km²`;
  }
  return `${new Intl.NumberFormat('en', { maximumFractionDigits: 1 }).format(hectares)} ha`;
}

/** Format a signed percentage change, or an em dash when there is no baseline. */
export function formatChange(changePct: number | null): string {
  if (changePct === null || Number.isNaN(changePct)) return '—';
  const sign = changePct > 0 ? '+' : '';
  return `${sign}${changePct.toFixed(1)}%`;
}

/** Format an ISO date as `12 Mar 2025`. */
export function formatDate(iso: string): string {
  try {
    return format(parseISO(iso), 'd MMM yyyy');
  } catch {
    return iso;
  }
}

/** Format an ISO date as `Mar 2025`, for monthly chart axes. */
export function formatMonth(iso: string): string {
  try {
    return format(parseISO(iso), 'MMM yyyy');
  } catch {
    return iso;
  }
}

/** Convert an ISO date string to epoch milliseconds for Highcharts. */
export function toTimestamp(iso: string): number {
  return parseISO(iso).getTime();
}

/** Turn `carbon_sequestered_tco2e` into `Carbon sequestered tco2e`, as a fallback label. */
export function humanise(key: string): string {
  const spaced = key.replace(/_/g, ' ');
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}
