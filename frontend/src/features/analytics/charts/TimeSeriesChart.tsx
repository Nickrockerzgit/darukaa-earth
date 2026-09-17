import HighchartsReact from 'highcharts-react-official';
import { useMemo } from 'react';

import { buildSeriesChartOptions, Highcharts } from '@/lib/highcharts';
import type { MetricSeries } from '@/types/api';

export interface TimeSeriesChartProps {
  series: MetricSeries;
  height?: number;
}

/**
 * One metric over time.
 *
 * The options object is memoised on the series identity: Highcharts re-renders
 * (and re-animates) whenever it receives a new options reference, so rebuilding
 * it on every parent render would make the chart flicker on unrelated state
 * changes such as a hover elsewhere on the page.
 */
export function TimeSeriesChart({ series, height = 280 }: TimeSeriesChartProps) {
  const options = useMemo(() => buildSeriesChartOptions(series, { height }), [series, height]);

  return <HighchartsReact highcharts={Highcharts} options={options} />;
}
