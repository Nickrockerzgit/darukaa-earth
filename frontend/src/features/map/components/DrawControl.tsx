import MapboxDraw from '@mapbox/mapbox-gl-draw';
import '@mapbox/mapbox-gl-draw/dist/mapbox-gl-draw.css';
import type { Feature, Polygon } from 'geojson';
import { useEffect, useRef } from 'react';
import { useControl, type IControl } from 'react-map-gl';

/** The payload Mapbox Draw emits on `draw.create`. */
interface DrawCreateEvent {
  features: Feature[];
}

export interface DrawControlProps {
  /** Called once a polygon is finished, with the drawn feature. */
  onCreate: (feature: Feature<Polygon>) => void;
  /** Whether the draw tool is currently armed. */
  isActive: boolean;
}

/**
 * The polygon drawing tool.
 *
 * `useControl` registers MapboxDraw as a real map control rather than a React
 * child, which keeps the drawn geometry in Mapbox's own coordinate space.
 * Re-implementing this with React state and click handlers would drift out of
 * sync with the map on every pan and zoom.
 *
 * The cast to `IControl` is unavoidable: MapboxDraw types its `onAdd` against
 * the concrete `mapbox-gl` Map, while react-map-gl's control interface uses
 * its own structural `MapInstance`. The two are compatible at runtime.
 */
export function DrawControl({ onCreate, isActive }: DrawControlProps) {
  const drawRef = useRef<MapboxDraw | null>(null);

  // Read the callback through a ref so the control is created once and not
  // torn down whenever the parent re-renders with a new closure.
  const onCreateRef = useRef(onCreate);
  onCreateRef.current = onCreate;

  useControl<IControl>(
    () => {
      const instance = new MapboxDraw({
        displayControlsDefault: false,
        // The app arms drawing from its own button, so Mapbox's controls stay
        // hidden and there is exactly one way to start.
        controls: {},
        defaultMode: 'simple_select',
        styles: DRAW_STYLES,
      });
      drawRef.current = instance;
      return instance as unknown as IControl;
    },
    ({ map }) => {
      // 'draw.create' is contributed by MapboxDraw, so it is absent from the
      // map's own event-name union.
      map.on('draw.create', handleCreate);
    },
    ({ map }) => {
      map.off('draw.create', handleCreate);
      drawRef.current = null;
    },
    { position: 'top-left' },
  );

  function handleCreate(event: DrawCreateEvent): void {
    const [feature] = event.features;
    if (feature?.geometry.type === 'Polygon') {
      onCreateRef.current(feature as Feature<Polygon>);
      // Clear the scratch geometry: the saved site will come back through the
      // GeoJSON feed, and leaving it here would draw the polygon twice.
      drawRef.current?.deleteAll();
    }
  }

  useEffect(() => {
    const draw = drawRef.current;
    if (!draw) return;

    if (isActive) {
      draw.changeMode('draw_polygon');
    } else {
      draw.changeMode('simple_select');
      draw.deleteAll();
    }
  }, [isActive]);

  return null;
}

/** Draw styles matching the app's palette rather than Mapbox's blue default. */
const DRAW_STYLES = [
  {
    id: 'gl-draw-polygon-fill',
    type: 'fill',
    filter: ['all', ['==', '$type', 'Polygon'], ['!=', 'mode', 'static']],
    paint: { 'fill-color': '#37d9a0', 'fill-outline-color': '#37d9a0', 'fill-opacity': 0.2 },
  },
  {
    id: 'gl-draw-polygon-stroke',
    type: 'line',
    filter: ['all', ['==', '$type', 'Polygon'], ['!=', 'mode', 'static']],
    layout: { 'line-cap': 'round', 'line-join': 'round' },
    paint: { 'line-color': '#37d9a0', 'line-width': 2.5 },
  },
  {
    id: 'gl-draw-line',
    type: 'line',
    filter: ['all', ['==', '$type', 'LineString'], ['!=', 'mode', 'static']],
    layout: { 'line-cap': 'round', 'line-join': 'round' },
    paint: { 'line-color': '#37d9a0', 'line-dasharray': [0.2, 2], 'line-width': 2.5 },
  },
  {
    id: 'gl-draw-polygon-and-line-vertex-halo-active',
    type: 'circle',
    filter: ['all', ['==', 'meta', 'vertex'], ['==', '$type', 'Point']],
    paint: { 'circle-radius': 6, 'circle-color': '#10141a' },
  },
  {
    id: 'gl-draw-polygon-and-line-vertex-active',
    type: 'circle',
    filter: ['all', ['==', 'meta', 'vertex'], ['==', '$type', 'Point']],
    paint: { 'circle-radius': 4, 'circle-color': '#37d9a0' },
  },
];
