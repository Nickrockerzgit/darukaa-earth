import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import { afterAll, afterEach, beforeAll, describe, expect, it } from 'vitest';

import { DashboardPage } from '@/features/projects/pages/DashboardPage';
import { renderWithProviders } from '@/test/utils';
import type { Page, ProjectWithStats } from '@/types/api';

const API = 'http://localhost:8000/api/v1';

function project(overrides: Partial<ProjectWithStats> = {}): ProjectWithStats {
  return {
    id: 'p1',
    owner_id: 'u1',
    name: 'Sundarbans Mangrove Restoration',
    description: 'Blue carbon restoration in the delta.',
    project_type: 'mixed',
    status: 'active',
    start_date: '2022-04-01',
    created_at: '2022-04-01T00:00:00Z',
    updated_at: '2022-04-01T00:00:00Z',
    site_count: 3,
    total_area_hectares: 1450.25,
    ...overrides,
  };
}

function page(items: ProjectWithStats[], total = items.length): Page<ProjectWithStats> {
  return { items, total, page: 1, size: 12, pages: Math.max(1, Math.ceil(total / 12)) };
}

const server = setupServer(http.get(`${API}/projects`, () => HttpResponse.json(page([project()]))));

beforeAll(() => {
  server.listen({ onUnhandledRequest: 'error' });
});
afterEach(() => {
  server.resetHandlers();
});
afterAll(() => {
  server.close();
});

describe('DashboardPage', () => {
  it('shows a loading skeleton before the data arrives', () => {
    renderWithProviders(<DashboardPage />);
    expect(screen.getAllByRole('status', { name: 'Loading' }).length).toBeGreaterThan(0);
  });

  it('renders the returned projects', async () => {
    renderWithProviders(<DashboardPage />);

    expect(await screen.findByText('Sundarbans Mangrove Restoration')).toBeInTheDocument();
  });

  it('shows each project with its site count and total area', async () => {
    renderWithProviders(<DashboardPage />);

    await screen.findByText('Sundarbans Mangrove Restoration');
    expect(screen.getByText('3')).toBeInTheDocument();
    expect(screen.getByText('1,450.3 ha')).toBeInTheDocument();
  });

  it('reports the total in the subheading', async () => {
    server.use(
      http.get(`${API}/projects`, () =>
        HttpResponse.json(page([project(), project({ id: 'p2', name: 'Second' })], 2)),
      ),
    );
    renderWithProviders(<DashboardPage />);

    expect(await screen.findByText('2 projects')).toBeInTheDocument();
  });

  it('uses the singular when there is exactly one project', async () => {
    renderWithProviders(<DashboardPage />);
    expect(await screen.findByText('1 project')).toBeInTheDocument();
  });

  it('invites the user to create one when the list is empty', async () => {
    server.use(http.get(`${API}/projects`, () => HttpResponse.json(page([], 0))));
    renderWithProviders(<DashboardPage />);

    expect(await screen.findByText('No projects yet')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /create a project/i })).toBeInTheDocument();
  });

  it('distinguishes "no matches" from "no projects" when filtering', async () => {
    server.use(http.get(`${API}/projects`, () => HttpResponse.json(page([], 0))));
    renderWithProviders(<DashboardPage />);

    await screen.findByText('No projects yet');
    await userEvent.type(screen.getByLabelText('Search projects'), 'zzz');

    expect(await screen.findByText('No matching projects')).toBeInTheDocument();
  });

  it('sends the search term to the API, debounced', async () => {
    const requestedUrls: string[] = [];
    server.use(
      http.get(`${API}/projects`, ({ request }) => {
        requestedUrls.push(request.url);
        return HttpResponse.json(page([project()]));
      }),
    );
    renderWithProviders(<DashboardPage />);
    await screen.findByText('Sundarbans Mangrove Restoration');

    await userEvent.type(screen.getByLabelText('Search projects'), 'mangrove');

    await waitFor(() => {
      expect(requestedUrls.some((url) => url.includes('search=mangrove'))).toBe(true);
    });
    // Eight keystrokes must not produce eight requests.
    expect(requestedUrls.filter((url) => url.includes('search=')).length).toBeLessThan(4);
  });

  it('sends the status filter to the API', async () => {
    const requestedUrls: string[] = [];
    server.use(
      http.get(`${API}/projects`, ({ request }) => {
        requestedUrls.push(request.url);
        return HttpResponse.json(page([project()]));
      }),
    );
    renderWithProviders(<DashboardPage />);
    await screen.findByText('Sundarbans Mangrove Restoration');

    await userEvent.selectOptions(screen.getByLabelText('Filter by status'), 'archived');

    await waitFor(() => {
      expect(requestedUrls.some((url) => url.includes('status=archived'))).toBe(true);
    });
  });

  it('surfaces a failure with a retry action', async () => {
    server.use(
      http.get(`${API}/projects`, () =>
        HttpResponse.json(
          { error: 'internal_error', message: 'Database unavailable.' },
          { status: 500 },
        ),
      ),
    );
    renderWithProviders(<DashboardPage />);

    expect(await screen.findByText('Could not load projects')).toBeInTheDocument();
    expect(screen.getByText('Database unavailable.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument();
  });

  it('opens the create-project dialog', async () => {
    renderWithProviders(<DashboardPage />);
    await screen.findByText('Sundarbans Mangrove Restoration');

    await userEvent.click(screen.getByRole('button', { name: 'New project' }));

    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).getByText('New project')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('Project name')).toBeInTheDocument();
  });
});
