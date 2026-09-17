import type { Feature, Polygon } from 'geojson';
import { ArrowLeft, MapPin, Trash2 } from 'lucide-react';
import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';

import { EmptyState } from '@/components/common/EmptyState';
import { ProjectStatusBadge, ProjectTypeBadge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Skeleton } from '@/components/ui/Skeleton';
import { SiteAnalyticsPanel } from '@/features/analytics/components/SiteAnalyticsPanel';
import { MapView } from '@/features/map/components/MapView';
import {
  useDeleteProject,
  useProject,
  useProjectSites,
  useProjectSummary,
} from '@/features/projects/hooks/useProjects';
import { AddSitePanel } from '@/features/sites/components/AddSitePanel';
import { useSitesGeoJson } from '@/features/sites/hooks/useSites';
import { cn } from '@/lib/cn';
import { formatArea } from '@/lib/format';

/**
 * Project workspace.
 *
 * Three regions: a site list, the map, and the analytics for whichever site is
 * selected. Selection is one piece of page state shared by all three, so
 * clicking a polygon, clicking a list row, and the charts always agree.
 */
export function ProjectDetailPage() {
  const { projectId = '' } = useParams<{ projectId: string }>();
  const navigate = useNavigate();

  const [selectedSiteId, setSelectedSiteId] = useState<string | null>(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const [drawnFeature, setDrawnFeature] = useState<Feature<Polygon> | null>(null);

  const project = useProject(projectId);
  const summary = useProjectSummary(projectId);
  const sites = useProjectSites(projectId);
  const geojson = useSitesGeoJson(projectId);
  const deleteProject = useDeleteProject();

  const siteList = sites.data?.items ?? [];

  const resetDrawing = () => {
    setIsDrawing(false);
    setDrawnFeature(null);
  };

  const handleDelete = () => {
    if (!window.confirm('Delete this project? Its sites and metric history go with it.')) {
      return;
    }
    deleteProject.mutate(projectId, {
      onSuccess: () => {
        navigate('/dashboard', { replace: true });
      },
    });
  };

  if (project.isError) {
    return (
      <div className="p-8">
        <EmptyState
          icon={MapPin}
          title="Project not found"
          description={project.error.message}
          action={
            <Link to="/dashboard">
              <Button variant="secondary">Back to projects</Button>
            </Link>
          }
        />
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-surface-800 px-6 py-4">
        <div className="flex min-w-0 items-center gap-3">
          <Link
            to="/dashboard"
            aria-label="Back to projects"
            className="text-content-muted transition-colors hover:text-content-primary"
          >
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <div className="min-w-0">
            {project.isLoading ? (
              <Skeleton className="h-5 w-56" />
            ) : (
              <h1 className="truncate text-base font-semibold tracking-tight text-content-primary">
                {project.data?.name}
              </h1>
            )}
            <div className="mt-1 flex flex-wrap items-center gap-1.5">
              {project.data && (
                <>
                  <ProjectTypeBadge type={project.data.project_type} />
                  <ProjectStatusBadge status={project.data.status} />
                </>
              )}
              {summary.data && (
                <span className="text-xs text-content-muted">
                  {summary.data.site_count} site
                  {summary.data.site_count === 1 ? '' : 's'} ·{' '}
                  {formatArea(summary.data.total_area_hectares)}
                </span>
              )}
            </div>
          </div>
        </div>

        <Button
          variant="danger"
          size="sm"
          leftIcon={<Trash2 className="h-3.5 w-3.5" />}
          isLoading={deleteProject.isPending}
          onClick={handleDelete}
        >
          Delete project
        </Button>
      </header>

      <div className="grid min-h-0 flex-1 lg:grid-cols-[280px_1fr]">
        <aside className="flex min-h-0 flex-col gap-3 border-r border-surface-800 p-4">
          <AddSitePanel
            projectId={projectId}
            isDrawing={isDrawing}
            drawnFeature={drawnFeature}
            onStartDrawing={() => {
              setIsDrawing(true);
            }}
            onCancel={resetDrawing}
            onCreated={resetDrawing}
          />

          <div className="min-h-0 flex-1 overflow-y-auto">
            <p className="mb-2 text-[10px] font-medium tracking-wider text-content-muted uppercase">
              Sites
            </p>
            {sites.isLoading ? (
              <div className="space-y-2">
                {Array.from({ length: 3 }, (_, index) => (
                  <Skeleton key={index} className="h-12" />
                ))}
              </div>
            ) : siteList.length === 0 ? (
              <p className="py-6 text-center text-xs leading-relaxed text-content-muted">
                No sites yet. Draw one on the map to start collecting metrics.
              </p>
            ) : (
              <ul className="space-y-1">
                {siteList.map((site) => (
                  <li key={site.id}>
                    <button
                      type="button"
                      onClick={() => {
                        setSelectedSiteId(site.id === selectedSiteId ? null : site.id);
                      }}
                      aria-pressed={site.id === selectedSiteId}
                      className={cn(
                        'w-full rounded-lg border px-3 py-2 text-left transition-colors',
                        site.id === selectedSiteId
                          ? 'border-brand-500/50 bg-brand-500/10'
                          : 'border-surface-800 hover:border-surface-700 hover:bg-surface-850',
                      )}
                    >
                      <p className="truncate text-xs font-medium text-content-primary">
                        {site.name}
                      </p>
                      <p className="mt-0.5 text-[11px] text-content-muted tabular-nums">
                        {formatArea(site.area_hectares)}
                      </p>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </aside>

        <div className="grid min-h-0 grid-rows-[minmax(240px,40%)_1fr]">
          <MapView
            className="min-h-0 border-b border-surface-800"
            data={geojson.data}
            selectedSiteId={selectedSiteId}
            onSelectSite={setSelectedSiteId}
            isDrawing={isDrawing}
            onPolygonDrawn={(feature) => {
              setDrawnFeature(feature);
              setIsDrawing(false);
            }}
          />

          <div className="min-h-0 overflow-y-auto p-5">
            {selectedSiteId ? (
              <SiteAnalyticsPanel siteId={selectedSiteId} />
            ) : (
              <EmptyState
                icon={MapPin}
                title="Select a site"
                description="Click a polygon on the map, or a site in the list, to see its carbon, vegetation and biodiversity trends."
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
