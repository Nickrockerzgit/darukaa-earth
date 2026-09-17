/**
 * API contract types.
 *
 * These mirror the Pydantic schemas in `backend/app/schemas`. They are written
 * by hand rather than generated so the file stays readable in review; the
 * generator alternative (`openapi-typescript` against `/openapi.json`) is
 * documented in ADR-0005 as the upgrade path once the contract stabilises.
 */

import type { BBox, Feature, FeatureCollection, MultiPolygon, Point, Polygon } from 'geojson';

// ---------------------------------------------------------------------------
// Shared
// ---------------------------------------------------------------------------

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface ApiError {
  error: string;
  message: string;
  details?: Record<string, unknown> | null;
  request_id?: string | null;
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export type UserRole = 'admin' | 'viewer';

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface AuthResponse {
  user: User;
  tokens: TokenPair;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface RegisterPayload extends LoginPayload {
  full_name?: string;
}

// ---------------------------------------------------------------------------
// Projects
// ---------------------------------------------------------------------------

export type ProjectType = 'carbon' | 'biodiversity' | 'mixed';
export type ProjectStatus = 'draft' | 'active' | 'archived';

export interface Project {
  id: string;
  owner_id: string;
  name: string;
  description: string | null;
  project_type: ProjectType;
  status: ProjectStatus;
  start_date: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectWithStats extends Project {
  site_count: number;
  total_area_hectares: number;
}

export interface ProjectSummary {
  project_id: string;
  site_count: number;
  total_area_hectares: number;
  latest_metrics: Record<string, number>;
}

export interface ProjectCreatePayload {
  name: string;
  description?: string | null;
  project_type: ProjectType;
  status: ProjectStatus;
  start_date?: string | null;
}

export type ProjectUpdatePayload = Partial<ProjectCreatePayload>;

export interface ProjectListParams {
  page?: number;
  size?: number;
  status?: ProjectStatus;
  project_type?: ProjectType;
  search?: string;
}

// ---------------------------------------------------------------------------
// Sites
// ---------------------------------------------------------------------------

/** What the API accepts and returns for a site's footprint. */
export type AreaGeometry = Polygon | MultiPolygon;

export interface Site {
  id: string;
  project_id: string;
  name: string;
  description: string | null;
  geometry: AreaGeometry;
  centroid: Point;
  area_hectares: number;
  created_at: string;
  updated_at: string;
}

export interface SiteListItem {
  id: string;
  project_id: string;
  name: string;
  area_hectares: number;
  centroid: Point;
  created_at: string;
}

export interface SiteCreatePayload {
  name: string;
  description?: string | null;
  geometry: AreaGeometry;
}

export type SiteUpdatePayload = Partial<SiteCreatePayload>;

/** Properties the API attaches to each map feature, used for styling and popups. */
export interface SiteFeatureProperties {
  site_id: string;
  project_id: string;
  name: string;
  project_name: string;
  project_type: ProjectType;
  status: ProjectStatus;
  area_hectares: number;
}

export type SiteFeature = Feature<AreaGeometry, SiteFeatureProperties>;
export type SiteFeatureCollection = FeatureCollection<AreaGeometry, SiteFeatureProperties>;

/** The API sends `[minLon, minLat, maxLon, maxLat]`, or null when there are no sites. */
export type SiteBBox = BBox | null | undefined;

// ---------------------------------------------------------------------------
// Analytics
// ---------------------------------------------------------------------------

export type MetricCategory = 'carbon' | 'biodiversity' | 'vegetation';
export type AggregationType = 'sum' | 'avg' | 'last';
export type Interval = 'day' | 'month' | 'quarter' | 'year';

export interface MetricDefinition {
  id: number;
  key: string;
  label: string;
  unit: string;
  description: string | null;
  category: MetricCategory;
  aggregation: AggregationType;
  display_order: number;
}

export interface SeriesPoint {
  /** Bucket start date, ISO `YYYY-MM-DD`. */
  t: string;
  v: number;
}

export interface MetricSeries {
  metric_key: string;
  label: string;
  unit: string;
  category: MetricCategory;
  aggregation: AggregationType;
  points: SeriesPoint[];
}

export interface SiteAnalytics {
  site_id: string;
  interval: Interval;
  date_from: string;
  date_to: string;
  series: MetricSeries[];
}

export interface MetricSnapshot {
  metric_key: string;
  label: string;
  unit: string;
  category: MetricCategory;
  latest_value: number;
  latest_date: string;
  previous_value: number | null;
  change_pct: number | null;
}

export interface SiteAnalyticsSummary {
  site_id: string;
  site_name: string;
  area_hectares: number;
  snapshots: MetricSnapshot[];
}

export interface AnalyticsParams {
  metrics?: string[];
  date_from?: string;
  date_to?: string;
  interval?: Interval;
}
