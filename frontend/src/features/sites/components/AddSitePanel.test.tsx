import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { Feature, Polygon } from 'geojson';
import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from 'vitest';

import { AddSitePanel } from '@/features/sites/components/AddSitePanel';
import { renderWithProviders } from '@/test/utils';

const API = 'http://localhost:8000/api/v1';
const PROJECT_ID = 'project-1';

const DRAWN: Feature<Polygon> = {
  type: 'Feature',
  properties: {},
  geometry: {
    type: 'Polygon',
    coordinates: [
      [
        [77, 12],
        [77.01, 12],
        [77.01, 12.01],
        [77, 12.01],
        [77, 12],
      ],
    ],
  },
};

const server = setupServer();

beforeAll(() => {
  server.listen({ onUnhandledRequest: 'error' });
});
afterEach(() => {
  server.resetHandlers();
});
afterAll(() => {
  server.close();
});

function renderPanel(overrides: Partial<React.ComponentProps<typeof AddSitePanel>> = {}): {
  onStartDrawing: ReturnType<typeof vi.fn>;
  onCancel: ReturnType<typeof vi.fn>;
  onCreated: ReturnType<typeof vi.fn>;
} {
  const handlers = {
    onStartDrawing: vi.fn(),
    onCancel: vi.fn(),
    onCreated: vi.fn(),
  };
  renderWithProviders(
    <AddSitePanel
      projectId={PROJECT_ID}
      isDrawing={false}
      drawnFeature={null}
      {...handlers}
      {...overrides}
    />,
  );
  return handlers;
}

describe('AddSitePanel', () => {
  it('starts in the idle state with a call to action', () => {
    renderPanel();
    expect(screen.getByRole('button', { name: /draw a new site/i })).toBeInTheDocument();
  });

  it('arms drawing when the action is pressed', async () => {
    const { onStartDrawing } = renderPanel();

    await userEvent.click(screen.getByRole('button', { name: /draw a new site/i }));
    expect(onStartDrawing).toHaveBeenCalledTimes(1);
  });

  it('explains how to draw while the tool is armed', () => {
    // The map control is small; the instruction is what makes the flow usable.
    renderPanel({ isDrawing: true });

    expect(screen.getByText('Drawing mode')).toBeInTheDocument();
    expect(screen.getByText(/click on the map to place each corner/i)).toBeInTheDocument();
  });

  it('can cancel out of drawing mode', async () => {
    const { onCancel } = renderPanel({ isDrawing: true });

    await userEvent.click(screen.getByRole('button', { name: /cancel/i }));
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it('asks for a name once a polygon exists', () => {
    renderPanel({ drawnFeature: DRAWN });
    expect(screen.getByLabelText('Site name')).toBeInTheDocument();
  });

  it('keeps save disabled until the name is long enough', async () => {
    renderPanel({ drawnFeature: DRAWN });

    const save = screen.getByRole('button', { name: /save site/i });
    expect(save).toBeDisabled();

    await userEvent.type(screen.getByLabelText('Site name'), 'Gosaba Block');
    expect(save).toBeEnabled();
  });

  it('posts the drawn geometry and reports success', async () => {
    let received: unknown = null;
    server.use(
      http.post(`${API}/projects/${PROJECT_ID}/sites`, async ({ request }) => {
        received = await request.json();
        return HttpResponse.json(
          {
            id: 'site-1',
            project_id: PROJECT_ID,
            name: 'Gosaba Block',
            description: null,
            geometry: DRAWN.geometry,
            centroid: { type: 'Point', coordinates: [77.005, 12.005] },
            area_hectares: 122.4,
            created_at: '2025-09-01T00:00:00Z',
            updated_at: '2025-09-01T00:00:00Z',
          },
          { status: 201 },
        );
      }),
    );

    const { onCreated } = renderPanel({ drawnFeature: DRAWN });
    await userEvent.type(screen.getByLabelText('Site name'), 'Gosaba Block');
    await userEvent.click(screen.getByRole('button', { name: /save site/i }));

    await waitFor(() => {
      expect(onCreated).toHaveBeenCalledTimes(1);
    });
    expect(received).toMatchObject({
      name: 'Gosaba Block',
      geometry: { type: 'Polygon' },
    });
  });

  it('keeps the form open when the server rejects the geometry', async () => {
    server.use(
      http.post(`${API}/projects/${PROJECT_ID}/sites`, () =>
        HttpResponse.json(
          { error: 'invalid_geometry', message: 'Site area must be at least 100 m2.' },
          { status: 422 },
        ),
      ),
    );

    const { onCreated } = renderPanel({ drawnFeature: DRAWN });
    await userEvent.type(screen.getByLabelText('Site name'), 'Too Small');
    await userEvent.click(screen.getByRole('button', { name: /save site/i }));

    await waitFor(() => {
      expect(screen.getByLabelText('Site name')).toHaveValue('Too Small');
    });
    expect(onCreated).not.toHaveBeenCalled();
  });
});
