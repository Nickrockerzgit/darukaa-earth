import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it } from 'vitest';

import { LoginPage } from '@/features/auth/pages/LoginPage';
import { useAuthStore } from '@/features/auth/store/authStore';
import { renderWithProviders } from '@/test/utils';

const API = 'http://localhost:8000/api/v1';

const AUTH_RESPONSE = {
  user: {
    id: 'u1',
    email: 'admin@darukaa.earth',
    full_name: 'Demo Admin',
    role: 'admin',
    is_active: true,
    created_at: '2025-01-01T00:00:00Z',
  },
  tokens: {
    access_token: 'access-1',
    refresh_token: 'refresh-1',
    token_type: 'bearer',
    expires_in: 900,
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

beforeEach(() => {
  useAuthStore.setState({
    user: null,
    accessToken: null,
    refreshToken: null,
    isAuthenticated: false,
    isHydrating: false,
  });
});

describe('LoginPage', () => {
  it('renders the credential fields', () => {
    renderWithProviders(<LoginPage />);

    expect(screen.getByLabelText('Email')).toBeInTheDocument();
    expect(screen.getByLabelText('Password')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Sign in' })).toBeInTheDocument();
  });

  it('offers a route to registration', () => {
    renderWithProviders(<LoginPage />);
    expect(screen.getByRole('link', { name: 'Create one' })).toHaveAttribute('href', '/register');
  });

  it('shows the demo credentials, so a reviewer can get in immediately', () => {
    renderWithProviders(<LoginPage />);
    expect(screen.getByText(/admin@darukaa\.earth/)).toBeInTheDocument();
  });

  it('validates the email client-side before calling the API', async () => {
    renderWithProviders(<LoginPage />);

    await userEvent.type(screen.getByLabelText('Email'), 'not-an-email');
    await userEvent.type(screen.getByLabelText('Password'), 'CorrectHorse123');
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }));

    expect(await screen.findByText('Enter a valid email address')).toBeInTheDocument();
  });

  it('requires a password', async () => {
    renderWithProviders(<LoginPage />);

    await userEvent.type(screen.getByLabelText('Email'), 'admin@darukaa.earth');
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }));

    expect(await screen.findByText('Password is required')).toBeInTheDocument();
  });

  it('signs the user in on success', async () => {
    server.use(http.post(`${API}/auth/login`, () => HttpResponse.json(AUTH_RESPONSE)));
    renderWithProviders(<LoginPage />);

    await userEvent.type(screen.getByLabelText('Email'), 'admin@darukaa.earth');
    await userEvent.type(screen.getByLabelText('Password'), 'DarukaaDemo123');
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }));

    await waitFor(() => {
      expect(useAuthStore.getState().isAuthenticated).toBe(true);
    });
    expect(useAuthStore.getState().user?.email).toBe('admin@darukaa.earth');
  });

  it('surfaces a rejected login as an alert', async () => {
    server.use(
      http.post(`${API}/auth/login`, () =>
        HttpResponse.json(
          { error: 'authentication_error', message: 'Incorrect email or password.' },
          { status: 401 },
        ),
      ),
    );
    renderWithProviders(<LoginPage />);

    await userEvent.type(screen.getByLabelText('Email'), 'admin@darukaa.earth');
    await userEvent.type(screen.getByLabelText('Password'), 'WrongHorse123');
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }));

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('Incorrect email or password.');
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
  });

  it('explains an unreachable API rather than showing a raw axios message', async () => {
    server.use(http.post(`${API}/auth/login`, () => HttpResponse.error()));
    renderWithProviders(<LoginPage />);

    await userEvent.type(screen.getByLabelText('Email'), 'admin@darukaa.earth');
    await userEvent.type(screen.getByLabelText('Password'), 'DarukaaDemo123');
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(/cannot reach the server/i);
  });
});
