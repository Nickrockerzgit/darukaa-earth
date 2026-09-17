import { beforeAll, describe, expect, it } from 'vitest';

import {
  applyHighchartsTheme,
  buildComparisonChartOptions,
  buildSeriesChartOptions,
  CATEGORY_COLOR,
} from '@/lib/highcharts';
import type { MetricSeries } from '@/types/api';

function series(overrides: Partial<MetricSeries> = {}): MetricSeries {
  return {
    metric_key: 'carbon_sequestered_tco2e',
    label: 'Carbon Sequestered',
    unit: 'tCO2e',
    category: 'carbon',
    aggregation: 'sum',
    points: [
      { t: '2025-01-01', v: 10 },
      { t: '2025-02-01', v: 12 },
    ],
    ...overrides,
  };
}

beforeAll(() => {
  applyHighchartsTheme();
});

describe('buildSeriesChartOptions', () => {
  it('renders a flow metric as columns', () => {
    // Each bar is a discrete quantity added during that period.
    const options = buildSeriesChartOptions(series({ aggregation: 'sum' }));
    expect(options.chart?.type).toBe('column');
  });

  it('renders a stock or index metric as a filled area', () => {
    const options = buildSeriesChartOptions(series({ aggregation: 'avg' }));
    expect(options.chart?.type).toBe('areaspline');
  });

  it('colours the series by its category', () => {
    const options = buildSeriesChartOptions(series({ category: 'biodiversity' }));
    expect(options.series?.[0]).toMatchObject({ color: CATEGORY_COLOR.biodiversity });
  });

  it('converts points to [timestamp, value] tuples', () => {
    const options = buildSeriesChartOptions(series());
    const data = (options.series?.[0] as { data: [number, number][] }).data;

    expect(data).toHaveLength(2);
    expect(data[0]?.[0]).toBe(Date.parse('2025-01-01'));
    expect(data[0]?.[1]).toBe(10);
  });

  it('pins NDVI to its physical 0-1 range', () => {
    // Auto-scaling an index exaggerates noise into an apparent trend.
    const options = buildSeriesChartOptions(
      series({ metric_key: 'ndvi', aggregation: 'avg', unit: 'index' }),
    );
    expect(options.yAxis).toMatchObject({ min: 0, max: 1 });
  });

  it('leaves other metrics auto-scaled', () => {
    const options = buildSeriesChartOptions(series());
    expect(options.yAxis).not.toHaveProperty('min');
  });

  it('uses the unit as the axis title', () => {
    const options = buildSeriesChartOptions(series());
    expect(options.yAxis).toMatchObject({ title: { text: 'tCO2e' } });
  });

  it('honours a requested height', () => {
    expect(buildSeriesChartOptions(series(), { height: 500 }).chart?.height).toBe(500);
  });
});

describe('buildComparisonChartOptions', () => {
  const list = [
    series(),
    series({ metric_key: 'ndvi', label: 'NDVI', unit: 'index', category: 'vegetation' }),
    series({
      metric_key: 'biodiversity_index',
      label: 'Biodiversity Index',
      unit: 'score',
      category: 'biodiversity',
    }),
  ];

  it('gives every metric its own axis', () => {
    // NDVI (0-1) and carbon (thousands of tonnes) on one axis would flatten
    // NDVI into the baseline.
    const options = buildComparisonChartOptions(list);
    expect(Array.isArray(options.yAxis)).toBe(true);
    expect(options.yAxis).toHaveLength(3);
  });

  it('alternates axes between the two sides of the chart', () => {
    const axes = buildComparisonChartOptions(list).yAxis as { opposite: boolean }[];
    expect(axes[0]?.opposite).toBe(false);
    expect(axes[1]?.opposite).toBe(true);
  });

  it('binds each series to its own axis index', () => {
    const options = buildComparisonChartOptions(list);
    expect(options.series?.[1]).toMatchObject({ yAxis: 1 });
  });

  it('labels each series with its unit', () => {
    const options = buildComparisonChartOptions(list);
    expect(options.series?.[0]).toMatchObject({ name: 'Carbon Sequestered (tCO2e)' });
  });

  it('shows the legend, since there is more than one series', () => {
    expect(buildComparisonChartOptions(list).legend?.enabled).toBe(true);
  });
});

describe('CATEGORY_COLOR', () => {
  it('gives each metric category a distinct colour', () => {
    const colours = Object.values(CATEGORY_COLOR);
    expect(new Set(colours).size).toBe(colours.length);
  });
});
