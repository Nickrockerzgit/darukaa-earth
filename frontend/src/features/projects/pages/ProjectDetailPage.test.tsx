import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from 'vitest';

import { renderWithProviders } from '@/test/utils';

// mapbox-gl needs WebGL, which jsdom does not provide. The map is replaced by
// a stub that exposes the same selection callback, so this file can test the
// page's own behaviour (selection, layout, deletion) without a GPU.
vi.mock('@/features/map/components/MapView', () => ({
  MapView: ({ onSelectSite }: { onSelectSite?: (id: string | null) => void }) => (
    <button
      type="button"
      data-testid="map-stub"
      onClick={() => {
        onSelectSite?.('site-1');
      }}
    >
      map
    </button>
  ),
}));

const { ProjectDetailPage } = await import('@/features/projects/pages/ProjectDetailPage');

const API = 'http://localhost:8000/api/v1';
const PROJECT_ID = 'project-1';

const PROJECT = {
  id: PROJECT_ID,
  owner_id: 'u1',
  name: 'Western Ghats Agroforestry',
  description: 'Shade-grown coffee.',
  project_type: 'carbon',
  status: 'active',
  start_date: '2021-06-01',
  created_at: '2021-06-01T00:00:00Z',
  updated_at: '2021-06-01T00:00:00Z',
};

const SITE = {
  id: 'site-1',
  project_id: PROJECT_ID,
  name: 'Kodagu Plateau',
  area_hectares: 1820.5,
  centroid: { type: 'Point', coordinates: [75.79, 12.36] },
  created_at: '2021-06-01T00:00:00Z',
};

const SUMMARY = {
  site_id: 'site-1',
  site_name: 'Kodagu Plateau',
  area_hectares: 1820.5,
  snapshots: [
    {
      metric_key: 'ndvi',
      label: 'NDVI',
      unit: 'index',
      category: 'vegetation',
      latest_value: 0.62,
      latest_date: '2025-09-01',
      previous_value: 0.6,
      change_pct: 3.33,
    },
  ],
};

const server = setupServer(
  http.get(`${API}/projects/${PROJECT_ID}`, () => HttpResponse.json(PROJECT)),
  http.get(`${API}/projects/${PROJECT_ID}/summary`, () =>
    HttpResponse.json({
      project_id: PROJECT_ID,
      site_count: 1,
      total_area_hectares: 1820.5,
      latest_metrics: { ndvi: 0.62 },
    }),
  ),
  http.get(`${API}/projects/${PROJECT_ID}/sites`, () =>
    HttpResponse.json({ items: [SITE], total: 1, page: 1, size: 100, pages: 1 }),
  ),
  http.get(`${API}/sites/geojson`, () =>
    HttpResponse.json({ type: 'FeatureCollection', features: [], bbox: null }),
  ),
  http.get(`${API}/sites/site-1/analytics/summary`, () => HttpResponse.json(SUMMARY)),
  http.get(`${API}/sites/site-1/analytics`, () =>
    HttpResponse.json({
      site_id: 'site-1',
      interval: 'month',
      date_from: '2022-09-01',
      date_to: '2025-09-01',
      series: [
        {
          metric_key: 'ndvi',
          label: 'NDVI',
          unit: 'index',
          category: 'vegetation',
          aggregation: 'avg',
          points: [{ t: '2025-09-01', v: 0.62 }],
        },
      ],
    }),
  ),
);

beforeAll(() => {
  server.listen({ onUnhandledRequest: 'error' });
});
afterEach(() => {
  server.resetHandlers();
});
afterAll(() => {
  server.close();
});

function renderPage() {
  return renderWithProviders(<ProjectDetailPage />, { route: `/projects/${PROJECT_ID}` });
}

// The component reads :projectId from the router; the test renders it outside
// a matching route, so useParams is pinned to the fixture id.
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return { ...actual, useParams: () => ({ projectId: PROJECT_ID }) };
});

describe('ProjectDetailPage', () => {
  it('shows the project name and badges', async () => {
    renderPage();

    expect(await screen.findByText('Western Ghats Agroforestry')).toBeInTheDocument();
    expect(screen.getByText('Carbon')).toBeInTheDocument();
    expect(screen.getByText('Active')).toBeInTheDocument();
  });

  it('summarises site count and total area in the header', async () => {
    renderPage();
    expect(await screen.findByText(/1 site · 1,820.5 ha/)).toBeInTheDocument();
  });

  it('lists the project sites', async () => {
    renderPage();
    expect(await screen.findByText('Kodagu Plateau')).toBeInTheDocument();
  });

  it('prompts the user to pick a site before showing analytics', async () => {
    renderPage();
    expect(await screen.findByText('Select a site')).toBeInTheDocument();
  });

  it('loads analytics when a site is selected from the list', async () => {
    renderPage();
    await userEvent.click(await screen.findByRole('button', { name: /Kodagu Plateau/ }));

    await waitFor(() => {
      expect(screen.getByText('Performance over time')).toBeInTheDocument();
    });
  });

  it('selects the same site when the map reports a click', async () => {
    renderPage();
    await screen.findByText('Kodagu Plateau');

    await userEvent.click(screen.getByTestId('map-stub'));

    await waitFor(() => {
      expect(screen.getByText('Performance over time')).toBeInTheDocument();
    });
  });

  it('toggles the selection off when the same row is clicked twice', async () => {
    renderPage();
    const row = await screen.findByRole('button', { name: /Kodagu Plateau/ });

    await userEvent.click(row);
    await waitFor(() => {
      expect(screen.getByText('Performance over time')).toBeInTheDocument();
    });

    await userEvent.click(row);
    expect(await screen.findByText('Select a site')).toBeInTheDocument();
  });

  it('reports a project that cannot be loaded', async () => {
    server.use(
      http.get(`${API}/projects/${PROJECT_ID}`, () =>
        HttpResponse.json({ error: 'not_found', message: 'Project not found.' }, { status: 404 }),
      ),
    );
    renderPage();

    expect(await screen.findByText('Project not found')).toBeInTheDocument();
  });
});
