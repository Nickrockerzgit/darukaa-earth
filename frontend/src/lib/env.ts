/**
 * Validated environment configuration.
 *
 * Reading `import.meta.env` directly all over the app makes a missing variable
 * surface as an undefined-shaped bug three screens deep. Parsing it once, here,
 * turns that into a clear message at startup.
 */

interface AppEnv {
  apiBaseUrl: string;
  mapboxToken: string;
  mapboxStyle: string;
  /** False when no Mapbox token is configured, so the UI can explain itself. */
  isMapConfigured: boolean;
}

const DEFAULT_MAPBOX_STYLE = 'mapbox://styles/mapbox/satellite-streets-v12';

function readEnv(): AppEnv {
  const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000').replace(
    /\/+$/,
    '',
  );
  const mapboxToken = import.meta.env.VITE_MAPBOX_TOKEN ?? '';
  const mapboxStyle = import.meta.env.VITE_MAPBOX_STYLE ?? DEFAULT_MAPBOX_STYLE;

  return {
    apiBaseUrl,
    mapboxToken,
    mapboxStyle,
    // Mapbox public tokens always start with `pk.`; an `sk.` secret token here
    // would be a credential leak, so it is treated as "not configured".
    isMapConfigured: mapboxToken.startsWith('pk.'),
  };
}

export const env = readEnv();
