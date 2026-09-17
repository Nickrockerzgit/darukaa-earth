/** React Query hooks for analytics. */

import { useQuery } from '@tanstack/react-query';

import { analyticsApi } from '@/features/analytics/api/analyticsApi';
import { queryKeys } from '@/lib/queryKeys';
import type { AnalyticsParams } from '@/types/api';

/** Guard for `queryFn`s whose `enabled` flag already ensures an id exists. */
function requireSiteId(siteId: string | undefined): string {
  if (!siteId) throw new Error('A site id is required.');
  return siteId;
}

/** The metric catalogue. Effectively static, so it is cached for the session. */
export function useMetricDefinitions() {
  return useQuery({
    queryKey: queryKeys.analytics.metrics(),
    queryFn: () => analyticsApi.metrics(),
    staleTime: Infinity,
  });
}

export function useSiteAnalytics(siteId: string | undefined, params: AnalyticsParams = {}) {
  return useQuery({
    queryKey: queryKeys.analytics.series(siteId ?? '', params),
    queryFn: () => analyticsApi.series(requireSiteId(siteId), params),
    enabled: Boolean(siteId),
    // Switching interval keeps the old chart visible instead of collapsing the
    // panel to a skeleton and back.
    placeholderData: (previous) => previous,
  });
}

export function useSiteAnalyticsSummary(siteId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.analytics.summary(siteId ?? ''),
    queryFn: () => analyticsApi.summary(requireSiteId(siteId)),
    enabled: Boolean(siteId),
  });
}
