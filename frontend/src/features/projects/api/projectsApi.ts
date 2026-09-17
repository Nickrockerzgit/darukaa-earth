/** HTTP calls for projects and their sites. */

import { request, requestNoContent } from '@/lib/apiClient';
import type {
  Page,
  Project,
  ProjectCreatePayload,
  ProjectListParams,
  ProjectSummary,
  ProjectUpdatePayload,
  ProjectWithStats,
  Site,
  SiteCreatePayload,
  SiteListItem,
} from '@/types/api';

export const projectsApi = {
  list: (params: ProjectListParams = {}) =>
    request<Page<ProjectWithStats>>({ method: 'GET', url: '/projects', params }),

  get: (projectId: string) => request<Project>({ method: 'GET', url: `/projects/${projectId}` }),

  create: (payload: ProjectCreatePayload) =>
    request<Project>({ method: 'POST', url: '/projects', data: payload }),

  update: (projectId: string, payload: ProjectUpdatePayload) =>
    request<Project>({ method: 'PATCH', url: `/projects/${projectId}`, data: payload }),

  remove: (projectId: string) =>
    requestNoContent({ method: 'DELETE', url: `/projects/${projectId}` }),

  summary: (projectId: string) =>
    request<ProjectSummary>({ method: 'GET', url: `/projects/${projectId}/summary` }),

  listSites: (projectId: string, params: { page?: number; size?: number } = {}) =>
    request<Page<SiteListItem>>({
      method: 'GET',
      url: `/projects/${projectId}/sites`,
      params,
    }),

  createSite: (projectId: string, payload: SiteCreatePayload) =>
    request<Site>({ method: 'POST', url: `/projects/${projectId}/sites`, data: payload }),
};
