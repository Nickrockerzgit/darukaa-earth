import { Minus, TrendingDown, TrendingUp } from 'lucide-react';

import { cn } from '@/lib/cn';
import { formatChange, formatDate, formatMetricValue } from '@/lib/format';
import { CATEGORY_COLOR } from '@/lib/highcharts';
import type { MetricSnapshot } from '@/types/api';

/**
 * Metrics where a falling number is the good news.
 *
 * Nothing in the current catalogue is inverted, but hardcoding "up is green"
 * would silently mislabel the first such metric that gets added, so the
 * polarity is explicit.
 */
const LOWER_IS_BETTER = new Set<string>([]);

const NEUTRAL_CHANGE_THRESHOLD = 0.05;

export function KpiCard({ snapshot }: { snapshot: MetricSnapshot }) {
  const { change_pct: changePct } = snapshot;
  const isFlat = changePct === null || Math.abs(changePct) < NEUTRAL_CHANGE_THRESHOLD;
  const isRising = changePct !== null && changePct > 0;
  const isGood = LOWER_IS_BETTER.has(snapshot.metric_key) ? !isRising : isRising;

  const TrendIcon = isFlat ? Minus : isRising ? TrendingUp : TrendingDown;
  const trendClass = isFlat ? 'text-content-muted' : isGood ? 'text-positive' : 'text-negative';

  return (
    <div className="panel flex flex-col gap-3 p-4">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <span
            aria-hidden
            className="h-2 w-2 shrink-0 rounded-full"
            style={{ backgroundColor: CATEGORY_COLOR[snapshot.category] }}
          />
          <span className="text-xs font-medium text-content-secondary">{snapshot.label}</span>
        </div>
        <span className={cn('flex items-center gap-1 text-xs font-medium', trendClass)}>
          <TrendIcon className="h-3 w-3" aria-hidden />
          {formatChange(changePct)}
        </span>
      </div>

      <p className="text-2xl font-semibold tracking-tight text-content-primary tabular-nums">
        {formatMetricValue(snapshot.latest_value, snapshot.unit)}
      </p>

      <p className="text-[11px] text-content-muted">
        as of {formatDate(snapshot.latest_date)}
        {snapshot.previous_value !== null && (
          <>
            {' · prev '}
            {formatMetricValue(snapshot.previous_value, snapshot.unit)}
          </>
        )}
      </p>
    </div>
  );
}
