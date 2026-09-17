import 'mapbox-gl/dist/mapbox-gl.css';

import type { Feature, Polygon } from 'geojson';
import { MapPinOff } from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';
import Map, {
  Layer,
  NavigationControl,
  ScaleControl,
  Source,
  type MapMouseEvent,
  type MapRef,
} from 'react-map-gl';

import { DrawControl } from '@/features/map/components/DrawControl';
import { env } from '@/lib/env';
import { averagePosition } from '@/lib/geometry';
import {
  bboxToBounds,
  DEFAULT_VIEW_STATE,
  MAP_STYLE,
  pointToBounds,
  SITES_FILL_LAYER_ID,
  SITES_SOURCE_ID,
  sitesFillLayer,
  sitesLabelLayer,
  sitesOutlineLayer,
} from '@/lib/mapbox';
import type { SiteFeatureCollection } from '@/types/api';

const EMPTY_COLLECTION: SiteFeatureCollection = { type: 'FeatureCollection', features: [] };
const FIT_PADDING = 64;
const FLY_ZOOM = 12;

export interface MapViewProps {
  data: SiteFeatureCollection | undefined;
  selectedSiteId?: string | null;
  onSelectSite?: (siteId: string | null) => void;
  isDrawing?: boolean;
  onPolygonDrawn?: (feature: Feature<Polygon>) => void;
  className?: string;
}

/**
 * The interactive map.
 *
 * Polygons come from one GeoJSON `Source` styled by three Mapbox layers, not
 * from React components: Mapbox then owns hit-testing, label collision and
 * zoom-dependent styling, so the cost of rendering 500 sites is the same as 5.
 * Hover and selection are expressed as feature state, which repaints on the
 * GPU without touching the source data.
 */
export function MapView({
  data,
  selectedSiteId = null,
  onSelectSite,
  isDrawing = false,
  onPolygonDrawn,
  className,
}: MapViewProps) {
  const mapRef = useRef<MapRef>(null);
  const hoveredIdRef = useRef<string | number | null>(null);
  const [isLoaded, setIsLoaded] = useState(false);

  const collection = data ?? EMPTY_COLLECTION;

  // Frame the data once it arrives. Guarded on `isLoaded` because calling
  // fitBounds before the style finishes loading is a silent no-op.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !isLoaded) return;

    const bounds = bboxToBounds(collection.bbox);
    if (bounds) {
      map.fitBounds(bounds, { padding: FIT_PADDING, duration: 900, maxZoom: 13 });
    }
  }, [collection.bbox, isLoaded]);

  // Fly to the selected site, so clicking a row in the sidebar moves the map.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !isLoaded || !selectedSiteId) return;

    const feature = collection.features.find((item) => item.properties.site_id === selectedSiteId);
    if (!feature) return;

    const [longitude, latitude] = averagePosition(feature.geometry);
    map.fitBounds(pointToBounds(longitude, latitude), {
      padding: FIT_PADDING,
      duration: 800,
      maxZoom: FLY_ZOOM,
    });
  }, [selectedSiteId, collection.features, isLoaded]);

  // Mirror the selection into Mapbox feature state so the style can highlight it.
  useEffect(() => {
    const map = mapRef.current?.getMap();
    if (!map || !isLoaded || !map.getSource(SITES_SOURCE_ID)) return;

    for (const feature of collection.features) {
      const id = feature.id ?? feature.properties.site_id;
      map.setFeatureState(
        { source: SITES_SOURCE_ID, id },
        { selected: feature.properties.site_id === selectedSiteId },
      );
    }
  }, [selectedSiteId, collection.features, isLoaded]);

  const handleMouseMove = useCallback((event: MapMouseEvent) => {
    const map = event.target;
    const feature = event.features?.[0];

    if (hoveredIdRef.current !== null) {
      map.setFeatureState({ source: SITES_SOURCE_ID, id: hoveredIdRef.current }, { hover: false });
      hoveredIdRef.current = null;
    }
    if (feature?.id != null) {
      hoveredIdRef.current = feature.id;
      map.setFeatureState({ source: SITES_SOURCE_ID, id: feature.id }, { hover: true });
    }
    map.getCanvas().style.cursor = feature ? 'pointer' : '';
  }, []);

  const handleMouseLeave = useCallback((event: MapMouseEvent) => {
    const map = event.target;
    if (hoveredIdRef.current !== null) {
      map.setFeatureState({ source: SITES_SOURCE_ID, id: hoveredIdRef.current }, { hover: false });
      hoveredIdRef.current = null;
    }
    map.getCanvas().style.cursor = '';
  }, []);

  const handleClick = useCallback(
    (event: MapMouseEvent) => {
      if (isDrawing) return;
      // Feature properties come back as `unknown` from the style, so the
      // id is checked rather than asserted.
      const properties: unknown = event.features?.[0]?.properties;
      const siteId =
        typeof properties === 'object' && properties !== null && 'site_id' in properties
          ? (properties as { site_id?: unknown }).site_id
          : undefined;
      onSelectSite?.(typeof siteId === 'string' ? siteId : null);
    },
    [isDrawing, onSelectSite],
  );

  if (!env.isMapConfigured) {
    return <MapTokenNotice className={className} />;
  }

  return (
    <div className={className}>
      <Map
        ref={mapRef}
        mapboxAccessToken={env.mapboxToken}
        mapStyle={MAP_STYLE}
        initialViewState={DEFAULT_VIEW_STATE}
        interactiveLayerIds={[SITES_FILL_LAYER_ID]}
        onLoad={() => {
          setIsLoaded(true);
        }}
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
        onClick={handleClick}
        reuseMaps
        style={{ width: '100%', height: '100%' }}
      >
        <NavigationControl position="top-right" showCompass={false} />
        <ScaleControl position="bottom-right" unit="metric" />

        <Source id={SITES_SOURCE_ID} type="geojson" data={collection} promoteId="site_id">
          <Layer {...sitesFillLayer} />
          <Layer {...sitesOutlineLayer} />
          <Layer {...sitesLabelLayer} />
        </Source>

        {onPolygonDrawn != null && <DrawControl isActive={isDrawing} onCreate={onPolygonDrawn} />}
      </Map>
    </div>
  );
}

/** Shown when no Mapbox token is configured, instead of a blank grey canvas. */
function MapTokenNotice({ className }: { className?: string }) {
  return (
    <div className={className}>
      <div className="flex h-full flex-col items-center justify-center gap-3 bg-surface-900 px-6 text-center">
        <div className="rounded-full border border-surface-800 bg-surface-850 p-3">
          <MapPinOff className="h-6 w-6 text-content-muted" aria-hidden />
        </div>
        <div className="max-w-sm space-y-1">
          <h3 className="text-sm font-semibold text-content-primary">Map not configured</h3>
          <p className="text-xs leading-relaxed text-content-muted">
            Set <code className="text-brand-400">VITE_MAPBOX_TOKEN</code> to a public Mapbox token
            (it starts with <code className="text-brand-400">pk.</code>) in{' '}
            <code className="text-brand-400">frontend/.env</code> and reload. Everything else in the
            app works without it.
          </p>
        </div>
      </div>
    </div>
  );
}
