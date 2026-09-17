/**
 * React Query hooks for projects.
 *
 * Generics are left to inference: the error type comes from the `Register`
 * augmentation in `types/react-query.d.ts`, and everything else follows from
 * the annotated `queryFn` / `mutationFn`.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { projectsApi } from '@/features/projects/api/projectsApi';
import { queryKeys } from '@/lib/queryKeys';
import { toast } from '@/lib/toast';
import type { ProjectCreatePayload, ProjectListParams, ProjectUpdatePayload } from '@/types/api';

/**
 * Assert an id is present inside a `queryFn`.
 *
 * `enabled` already stops the query running without one, but the type system
 * cannot see that, and a non-null assertion would hide a real bug if the guard
 * were ever removed.
 */
function requireId(projectId: string | undefined): string {
  if (!projectId) throw new Error('A project id is required.');
  return projectId;
}

export function useProjects(params: ProjectListParams = {}) {
  return useQuery({
    queryKey: queryKeys.projects.list(params),
    queryFn: () => projectsApi.list(params),
    // Keep the previous page on screen while the next one loads, so paging and
    // filtering do not flash an empty grid.
    placeholderData: (previous) => previous,
  });
}

export function useProject(projectId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.projects.detail(projectId ?? ''),
    queryFn: () => projectsApi.get(requireId(projectId)),
    enabled: Boolean(projectId),
  });
}

export function useProjectSummary(projectId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.projects.summary(projectId ?? ''),
    queryFn: () => projectsApi.summary(requireId(projectId)),
    enabled: Boolean(projectId),
  });
}

export function useProjectSites(projectId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.projects.sites(projectId ?? ''),
    queryFn: () => projectsApi.listSites(requireId(projectId), { size: 100 }),
    enabled: Boolean(projectId),
  });
}

export function useCreateProject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: ProjectCreatePayload) => projectsApi.create(payload),
    onSuccess: (project) => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.projects.all() });
      toast.success(`Project "${project.name}" created.`);
    },
    onError: (error) => {
      toast.error(error.message);
    },
  });
}

export function useUpdateProject(projectId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: ProjectUpdatePayload) => projectsApi.update(projectId, payload),
    onSuccess: (project) => {
      queryClient.setQueryData(queryKeys.projects.detail(projectId), project);
      void queryClient.invalidateQueries({ queryKey: queryKeys.projects.all() });
      // Project type drives the map fill colour, so the feed must refresh too.
      void queryClient.invalidateQueries({ queryKey: queryKeys.sites.all() });
      toast.success('Project updated.');
    },
    onError: (error) => {
      toast.error(error.message);
    },
  });
}

export function useDeleteProject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (projectId: string) => projectsApi.remove(projectId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.projects.all() });
      void queryClient.invalidateQueries({ queryKey: queryKeys.sites.all() });
      toast.success('Project deleted.');
    },
    onError: (error) => {
      toast.error(error.message);
    },
  });
}
