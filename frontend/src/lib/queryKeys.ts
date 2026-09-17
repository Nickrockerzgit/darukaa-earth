/**
 * Query key factory.
 *
 * Keys are built here rather than inline so invalidation is reliable: adding a
 * site must refresh the project list (its `site_count` changed), the map feed
 * and that project's summary. Hand-written keys drift and the UI quietly goes
 * stale, which is the hardest class of bug to notice in a demo.
 */

import type { AnalyticsParams, ProjectListParams } from '@/types/api';

export const queryKeys = {
  auth: {
    me: () => ['auth', 'me'] as const,
  },
  projects: {
    all: () => ['projects'] as const,
    list: (params: ProjectListParams) => ['projects', 'list', params] as const,
    detail: (projectId: string) => ['projects', 'detail', projectId] as const,
    summary: (projectId: string) => ['projects', 'summary', projectId] as const,
    sites: (projectId: string) => ['projects', projectId, 'sites'] as const,
  },
  sites: {
    all: () => ['sites'] as const,
    geojson: (projectId?: string) => ['sites', 'geojson', projectId ?? 'all'] as const,
    detail: (siteId: string) => ['sites', 'detail', siteId] as const,
  },
  analytics: {
    all: () => ['analytics'] as const,
    metrics: () => ['analytics', 'metrics'] as const,
    series: (siteId: string, params: AnalyticsParams) =>
      ['analytics', 'series', siteId, params] as const,
    summary: (siteId: string) => ['analytics', 'summary', siteId] as const,
  },
} as const;
