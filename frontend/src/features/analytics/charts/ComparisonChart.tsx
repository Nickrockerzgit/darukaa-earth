import HighchartsReact from 'highcharts-react-official';
import { useMemo } from 'react';

import { buildComparisonChartOptions, Highcharts } from '@/lib/highcharts';
import type { MetricSeries } from '@/types/api';

export interface ComparisonChartProps {
  series: MetricSeries[];
  height?: number;
}

/**
 * Several metrics on one chart, each on its own axis.
 *
 * This is where the product question gets answered: does canopy cover actually
 * track carbon sequestration on this site, or are they diverging? A single
 * shared axis would hide that by flattening the smaller-scaled series.
 */
export function ComparisonChart({ series, height = 340 }: ComparisonChartProps) {
  const options = useMemo(() => buildComparisonChartOptions(series, { height }), [series, height]);

  return <HighchartsReact highcharts={Highcharts} options={options} />;
}
