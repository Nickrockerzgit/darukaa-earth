import { BarChart3 } from 'lucide-react';
import { useMemo, useState } from 'react';

import { EmptyState } from '@/components/common/EmptyState';
import { ErrorBoundary } from '@/components/common/ErrorBoundary';
import { Card, CardBody, CardHeader } from '@/components/ui/Card';
import { Select } from '@/components/ui/Select';
import { ChartSkeleton, Skeleton } from '@/components/ui/Skeleton';
import { ComparisonChart } from '@/features/analytics/charts/ComparisonChart';
import { KpiCard } from '@/features/analytics/charts/KpiCard';
import { TimeSeriesChart } from '@/features/analytics/charts/TimeSeriesChart';
import { useSiteAnalytics, useSiteAnalyticsSummary } from '@/features/analytics/hooks/useAnalytics';
import { formatArea } from '@/lib/format';
import type { Interval } from '@/types/api';

const INTERVAL_OPTIONS = [
  { value: 'month', label: 'Monthly' },
  { value: 'quarter', label: 'Quarterly' },
  { value: 'year', label: 'Yearly' },
];

/** Metrics compared on the combined chart: one per category, so the axes differ. */
const COMPARISON_KEYS = ['carbon_sequestered_tco2e', 'ndvi', 'biodiversity_index'];

export function SiteAnalyticsPanel({ siteId }: { siteId: string }) {
  const [interval, setInterval] = useState<Interval>('month');

  const summary = useSiteAnalyticsSummary(siteId);
  const analytics = useSiteAnalytics(siteId, { interval });

  const comparisonSeries = useMemo(
    () =>
      (analytics.data?.series ?? []).filter((series) =>
        COMPARISON_KEYS.includes(series.metric_key),
      ),
    [analytics.data],
  );

  if (summary.isError || analytics.isError) {
    return (
      <Card>
        <EmptyState
          icon={BarChart3}
          title="Analytics unavailable"
          description={(summary.error ?? analytics.error)?.message ?? 'Please try again.'}
        />
      </Card>
    );
  }

  return (
    <div className="space-y-5">
      <section aria-label="Key metrics">
        {summary.isLoading ? (
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {Array.from({ length: 6 }, (_, index) => (
              <Skeleton key={index} className="h-28" />
            ))}
          </div>
        ) : (
          <>
            <div className="mb-3 flex items-baseline justify-between gap-3">
              <h2 className="text-sm font-semibold text-content-primary">
                {summary.data?.site_name}
              </h2>
              <span className="text-xs text-content-muted">
                {summary.data ? formatArea(summary.data.area_hectares) : null}
              </span>
            </div>
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {summary.data?.snapshots.map((snapshot) => (
                <KpiCard key={snapshot.metric_key} snapshot={snapshot} />
              ))}
            </div>
          </>
        )}
      </section>

      <div className="flex items-center justify-between gap-3">
        <h2 className="text-sm font-semibold text-content-primary">Performance over time</h2>
        <div className="w-36">
          <Select
            value={interval}
            onChange={(event) => {
              setInterval(event.target.value as Interval);
            }}
            options={INTERVAL_OPTIONS}
            aria-label="Aggregation interval"
          />
        </div>
      </div>

      {analytics.isLoading ? (
        <div className="space-y-4">
          <ChartSkeleton height={340} />
          <div className="grid gap-4 xl:grid-cols-2">
            <ChartSkeleton />
            <ChartSkeleton />
          </div>
        </div>
      ) : (
        <ErrorBoundary area="the analytics charts">
          {comparisonSeries.length > 1 && (
            <Card>
              <CardHeader
                title="Carbon, vegetation and biodiversity"
                description="Each metric on its own axis, so different scales stay comparable."
              />
              <CardBody className="pt-2">
                <ComparisonChart series={comparisonSeries} />
              </CardBody>
            </Card>
          )}

          <div className="mt-4 grid gap-4 xl:grid-cols-2">
            {analytics.data?.series.map((series) => (
              <Card key={series.metric_key}>
                <CardHeader
                  title={series.label}
                  description={
                    series.aggregation === 'sum'
                      ? `Summed per period · ${series.unit}`
                      : `Averaged per period · ${series.unit}`
                  }
                />
                <CardBody className="pt-2">
                  {series.points.length === 0 ? (
                    <p className="py-10 text-center text-xs text-content-muted">
                      No samples in this window.
                    </p>
                  ) : (
                    <TimeSeriesChart series={series} />
                  )}
                </CardBody>
              </Card>
            ))}
          </div>
        </ErrorBoundary>
      )}
    </div>
  );
}
