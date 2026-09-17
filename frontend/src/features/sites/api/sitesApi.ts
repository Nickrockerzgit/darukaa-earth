/** HTTP calls for sites and the map's GeoJSON feed. */

import { request, requestNoContent } from '@/lib/apiClient';
import type { Site, SiteFeatureCollection, SiteUpdatePayload } from '@/types/api';

export const sitesApi = {
  /** The map's single data source. `projectId` narrows it to one project. */
  geojson: (projectId?: string) =>
    request<SiteFeatureCollection>({
      method: 'GET',
      url: '/sites/geojson',
      params: projectId != null ? { project_id: projectId } : undefined,
    }),

  get: (siteId: string) => request<Site>({ method: 'GET', url: `/sites/${siteId}` }),

  update: (siteId: string, payload: SiteUpdatePayload) =>
    request<Site>({ method: 'PATCH', url: `/sites/${siteId}`, data: payload }),

  remove: (siteId: string) => requestNoContent({ method: 'DELETE', url: `/sites/${siteId}` }),
};
