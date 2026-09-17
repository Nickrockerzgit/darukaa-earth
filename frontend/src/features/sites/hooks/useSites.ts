/** React Query hooks for sites. */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { projectsApi } from '@/features/projects/api/projectsApi';
import { sitesApi } from '@/features/sites/api/sitesApi';
import { queryKeys } from '@/lib/queryKeys';
import { toast } from '@/lib/toast';
import type { SiteCreatePayload } from '@/types/api';

/** Guard for `queryFn`s whose `enabled` flag already ensures an id exists. */
function requireSiteId(siteId: string | undefined): string {
  if (!siteId) throw new Error('A site id is required.');
  return siteId;
}

/** Every visible site as GeoJSON - one request feeds the whole map. */
export function useSitesGeoJson(projectId?: string) {
  return useQuery({
    queryKey: queryKeys.sites.geojson(projectId),
    queryFn: () => sitesApi.geojson(projectId),
    // Polygons change only when someone draws or edits one, and those paths
    // invalidate explicitly. Refetching on every window focus would re-render
    // the map layer for no reason.
    staleTime: 60_000,
  });
}

export function useSite(siteId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.sites.detail(siteId ?? ''),
    queryFn: () => sitesApi.get(requireSiteId(siteId)),
    enabled: Boolean(siteId),
  });
}

/** Everything a new or removed site touches, invalidated in one place. */
function useSiteInvalidation() {
  const queryClient = useQueryClient();
  return (projectId: string) => {
    void queryClient.invalidateQueries({ queryKey: queryKeys.sites.all() });
    void queryClient.invalidateQueries({ queryKey: queryKeys.projects.all() });
    void queryClient.invalidateQueries({ queryKey: queryKeys.projects.sites(projectId) });
    void queryClient.invalidateQueries({ queryKey: queryKeys.projects.summary(projectId) });
  };
}

export function useCreateSite(projectId: string) {
  const invalidate = useSiteInvalidation();

  return useMutation({
    mutationFn: (payload: SiteCreatePayload) => projectsApi.createSite(projectId, payload),
    onSuccess: (site) => {
      invalidate(projectId);
      toast.success(`Site "${site.name}" added (${site.area_hectares.toFixed(1)} ha).`);
    },
    onError: (error) => {
      toast.error(error.message);
    },
  });
}

export function useDeleteSite(projectId: string) {
  const invalidate = useSiteInvalidation();

  return useMutation({
    mutationFn: (siteId: string) => sitesApi.remove(siteId),
    onSuccess: () => {
      invalidate(projectId);
      toast.success('Site deleted.');
    },
    onError: (error) => {
      toast.error(error.message);
    },
  });
}
