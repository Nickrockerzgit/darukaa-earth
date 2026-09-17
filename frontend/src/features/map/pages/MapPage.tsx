import { Globe2, X } from 'lucide-react';
import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import { EmptyState } from '@/components/common/EmptyState';
import { Button } from '@/components/ui/Button';
import { SiteAnalyticsPanel } from '@/features/analytics/components/SiteAnalyticsPanel';
import { MapView } from '@/features/map/components/MapView';
import { useSitesGeoJson } from '@/features/sites/hooks/useSites';
import { PROJECT_TYPE_COLOR } from '@/lib/mapbox';
import type { ProjectType } from '@/types/api';

const LEGEND: { type: ProjectType; label: string }[] = [
  { type: 'carbon', label: 'Carbon' },
  { type: 'biodiversity', label: 'Biodiversity' },
  { type: 'mixed', label: 'Mixed' },
];

/**
 * The portfolio map: every site across every project on one canvas.
 *
 * Selecting a polygon opens its analytics in a side drawer rather than
 * navigating away, so a user can compare several sites without losing their
 * place on the map.
 */
export function MapPage() {
  const [selectedSiteId, setSelectedSiteId] = useState<string | null>(null);
  const geojson = useSitesGeoJson();

  const selectedFeature = useMemo(
    () => geojson.data?.features.find((feature) => feature.properties.site_id === selectedSiteId),
    [geojson.data, selectedSiteId],
  );

  const siteCount = geojson.data?.features.length ?? 0;

  return (
    <div className="relative h-full">
      <MapView
        className="h-full"
        data={geojson.data}
        selectedSiteId={selectedSiteId}
        onSelectSite={setSelectedSiteId}
      />

      <div className="panel pointer-events-auto absolute top-4 left-4 max-w-xs px-4 py-3">
        <h1 className="text-sm font-semibold text-content-primary">Portfolio map</h1>
        <p className="mt-0.5 text-xs text-content-muted">
          {geojson.isLoading
            ? 'Loading sites…'
            : `${siteCount} site${siteCount === 1 ? '' : 's'} across all projects`}
        </p>
        <ul className="mt-3 space-y-1.5">
          {LEGEND.map(({ type, label }) => (
            <li key={type} className="flex items-center gap-2">
              <span
                aria-hidden
                className="h-2.5 w-2.5 rounded-sm"
                style={{ backgroundColor: PROJECT_TYPE_COLOR[type] }}
              />
              <span className="text-xs text-content-secondary">{label}</span>
            </li>
          ))}
        </ul>
      </div>

      {!geojson.isLoading && siteCount === 0 && (
        <div className="panel absolute top-1/2 left-1/2 w-full max-w-sm -translate-x-1/2 -translate-y-1/2">
          <EmptyState
            icon={Globe2}
            title="Nothing mapped yet"
            description="Create a project and draw its first site to see it appear here."
            action={
              <Link to="/dashboard">
                <Button>Go to projects</Button>
              </Link>
            }
          />
        </div>
      )}

      {selectedSiteId != null && (
        <aside className="absolute inset-y-0 right-0 w-full overflow-y-auto border-l border-surface-800 bg-surface-950/97 backdrop-blur sm:w-[28rem]">
          <div className="sticky top-0 flex items-start justify-between gap-3 border-b border-surface-800 bg-surface-950/95 px-5 py-4 backdrop-blur">
            <div className="min-w-0">
              <p className="text-[10px] font-medium tracking-wider text-content-muted uppercase">
                {selectedFeature?.properties.project_name}
              </p>
              <h2 className="truncate text-sm font-semibold text-content-primary">
                {selectedFeature?.properties.name}
              </h2>
            </div>
            <div className="flex shrink-0 items-center gap-1">
              {selectedFeature != null && (
                <Link to={`/projects/${selectedFeature.properties.project_id}`}>
                  <Button variant="outline" size="sm">
                    Open project
                  </Button>
                </Link>
              )}
              <button
                type="button"
                aria-label="Close site panel"
                onClick={() => {
                  setSelectedSiteId(null);
                }}
                className="rounded-md p-1.5 text-content-muted transition-colors hover:bg-surface-800 hover:text-content-primary"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>

          <div className="p-5">
            <SiteAnalyticsPanel siteId={selectedSiteId} />
          </div>
        </aside>
      )}
    </div>
  );
}
