/** HTTP calls for the analytics endpoints. */

import { request } from '@/lib/apiClient';
import type {
  AnalyticsParams,
  MetricDefinition,
  SiteAnalytics,
  SiteAnalyticsSummary,
} from '@/types/api';

export const analyticsApi = {
  metrics: () => request<MetricDefinition[]>({ method: 'GET', url: '/metrics' }),

  series: (siteId: string, params: AnalyticsParams = {}) =>
    request<SiteAnalytics>({
      method: 'GET',
      url: `/sites/${siteId}/analytics`,
      params,
      // FastAPI expects repeated `metrics=` parameters, not the bracketed
      // array form axios would otherwise produce.
      paramsSerializer: { indexes: null },
    }),

  summary: (siteId: string) =>
    request<SiteAnalyticsSummary>({
      method: 'GET',
      url: `/sites/${siteId}/analytics/summary`,
    }),
};
