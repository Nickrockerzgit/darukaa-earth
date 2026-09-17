/**
 * Shared Highcharts theme and option builders.
 *
 * Every chart in the app goes through here, so they share one visual language
 * and a metric keeps the same colour whether it appears in a line chart, a
 * column chart or the map legend.
 */

import Highcharts from 'highcharts';

import { formatMetricValue } from '@/lib/format';
import type { MetricCategory, MetricSeries } from '@/types/api';

/** Category colours, mirroring the `--color-metric-*` tokens in index.css. */
export const CATEGORY_COLOR: Record<MetricCategory, string> = {
  carbon: '#37d9a0',
  vegetation: '#7fd94f',
  biodiversity: '#5fb5f0',
};

const SURFACE_900 = '#1b2028';
const SURFACE_800 = '#2b323d';
const CONTENT_PRIMARY = '#f2f4f7';
const CONTENT_MUTED = '#8f98a6';

let themeApplied = false;

/**
 * Apply the dark theme once per session.
 *
 * Highcharts merges global options into every subsequently created chart, so
 * this must run before the first chart mounts and must not run twice (a second
 * merge is wasted work and makes option precedence harder to reason about).
 */
export function applyHighchartsTheme(): void {
  if (themeApplied) return;
  themeApplied = true;

  Highcharts.setOptions({
    colors: [
      CATEGORY_COLOR.carbon,
      CATEGORY_COLOR.vegetation,
      CATEGORY_COLOR.biodiversity,
      '#f0c04f',
      '#e07a7a',
      '#b48ff0',
    ],
    chart: {
      backgroundColor: 'transparent',
      style: { fontFamily: 'Inter var, ui-sans-serif, system-ui, sans-serif' },
      spacing: [12, 8, 8, 4],
    },
    title: { text: undefined },
    credits: { enabled: false },
    accessibility: { enabled: false },
    xAxis: {
      lineColor: SURFACE_800,
      tickColor: SURFACE_800,
      gridLineColor: SURFACE_800,
      gridLineWidth: 0,
      labels: { style: { color: CONTENT_MUTED, fontSize: '11px' } },
    },
    yAxis: {
      gridLineColor: SURFACE_800,
      gridLineDashStyle: 'Dash',
      title: { style: { color: CONTENT_MUTED, fontSize: '11px' } },
      labels: { style: { color: CONTENT_MUTED, fontSize: '11px' } },
    },
    legend: {
      itemStyle: { color: CONTENT_MUTED, fontWeight: '500', fontSize: '12px' },
      itemHoverStyle: { color: CONTENT_PRIMARY },
      itemHiddenStyle: { color: '#4a525e' },
    },
    tooltip: {
      backgroundColor: SURFACE_900,
      borderColor: SURFACE_800,
      borderRadius: 10,
      shadow: false,
      style: { color: CONTENT_PRIMARY, fontSize: '12px' },
      shared: true,
      useHTML: true,
    },
    plotOptions: {
      series: {
        animation: { duration: 350 },
        marker: { enabled: false, symbol: 'circle', radius: 3 },
        states: { hover: { lineWidthPlus: 1 } },
      },
      area: { fillOpacity: 0.16, lineWidth: 2 },
      line: { lineWidth: 2 },
      column: { borderWidth: 0, borderRadius: 3 },
    },
  });
}

/** Turn an API series into Highcharts `[timestamp, value]` point tuples. */
function toPoints(series: MetricSeries): [number, number][] {
  return series.points.map((point) => [Date.parse(point.t), point.v]);
}

/**
 * Build the options for a single-metric time-series chart.
 *
 * A flow metric (`aggregation: 'sum'`) renders as columns because each bar is
 * a discrete quantity added during that period; a stock or index metric
 * renders as a filled area because it is a continuous level.
 */
export function buildSeriesChartOptions(
  series: MetricSeries,
  options: { height?: number } = {},
): Highcharts.Options {
  const isFlow = series.aggregation === 'sum';
  const color = CATEGORY_COLOR[series.category];

  return {
    chart: { type: isFlow ? 'column' : 'areaspline', height: options.height ?? 280 },
    xAxis: { type: 'datetime', crosshair: { color: SURFACE_800 } },
    yAxis: {
      title: { text: series.unit },
      // Index metrics live on a fixed 0-1 scale; auto-scaling them would
      // exaggerate noise into apparent trends.
      ...(series.metric_key === 'ndvi' ? { min: 0, max: 1 } : {}),
    },
    legend: { enabled: false },
    tooltip: {
      headerFormat: '<span style="font-size:11px;color:#8f98a6">{point.key}</span><br/>',
      pointFormatter(this: Highcharts.Point) {
        const value = formatMetricValue(this.y ?? 0, series.unit);
        return `<span style="color:${color}">●</span> <b>${value}</b>`;
      },
      xDateFormat: '%b %Y',
    },
    series: [
      {
        type: isFlow ? 'column' : 'areaspline',
        name: series.label,
        color,
        data: toPoints(series),
      },
    ],
  };
}

/**
 * Build the options for comparing several metrics on one chart.
 *
 * Each metric gets its own y-axis, because NDVI (0-1) and carbon (thousands of
 * tonnes) on a shared axis would flatten one of them into the baseline.
 */
export function buildComparisonChartOptions(
  seriesList: MetricSeries[],
  options: { height?: number } = {},
): Highcharts.Options {
  return {
    chart: { type: 'spline', height: options.height ?? 340 },
    xAxis: { type: 'datetime', crosshair: { color: SURFACE_800 } },
    yAxis: seriesList.map((series, index) => ({
      title: { text: series.unit },
      opposite: index % 2 === 1,
      gridLineWidth: index === 0 ? 1 : 0,
      labels: { style: { color: CATEGORY_COLOR[series.category], fontSize: '11px' } },
    })),
    tooltip: { xDateFormat: '%b %Y', shared: true },
    legend: { enabled: true, align: 'left', verticalAlign: 'top', margin: 16 },
    series: seriesList.map((series, index) => ({
      type: 'spline',
      name: `${series.label} (${series.unit})`,
      yAxis: index,
      color: CATEGORY_COLOR[series.category],
      data: toPoints(series),
    })),
  };
}

export { Highcharts };
