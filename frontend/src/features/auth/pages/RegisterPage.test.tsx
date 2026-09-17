import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it } from 'vitest';

import { RegisterPage } from '@/features/auth/pages/RegisterPage';
import { useAuthStore } from '@/features/auth/store/authStore';
import { renderWithProviders } from '@/test/utils';

const API = 'http://localhost:8000/api/v1';

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

async function fillValidForm(password = 'CorrectHorse123') {
  await userEvent.type(screen.getByLabelText('Full name'), 'Ada Lovelace');
  await userEvent.type(screen.getByLabelText('Email'), 'ada@darukaa.earth');
  await userEvent.type(screen.getByLabelText('Password'), password);
}

describe('RegisterPage', () => {
  it('renders the sign-up fields', () => {
    renderWithProviders(<RegisterPage />);

    expect(screen.getByLabelText('Full name')).toBeInTheDocument();
    expect(screen.getByLabelText('Email')).toBeInTheDocument();
    expect(screen.getByLabelText('Password')).toBeInTheDocument();
  });

  it('states the password rules up front', () => {
    renderWithProviders(<RegisterPage />);
    expect(screen.getByText(/at least 10 characters, with an uppercase/i)).toBeInTheDocument();
  });

  it('links back to sign in', () => {
    renderWithProviders(<RegisterPage />);
    expect(screen.getByRole('link', { name: 'Sign in' })).toHaveAttribute('href', '/login');
  });

  it('rejects a short password before hitting the API', async () => {
    renderWithProviders(<RegisterPage />);
    await fillValidForm('Short1A');
    await userEvent.click(screen.getByRole('button', { name: 'Create account' }));

    expect(await screen.findByText('Use at least 10 characters')).toBeInTheDocument();
  });

  it('requires an uppercase letter', async () => {
    renderWithProviders(<RegisterPage />);
    await fillValidForm('alllowercase123');
    await userEvent.click(screen.getByRole('button', { name: 'Create account' }));

    expect(await screen.findByText('Include an uppercase letter')).toBeInTheDocument();
  });

  it('requires a digit', async () => {
    renderWithProviders(<RegisterPage />);
    await fillValidForm('NoDigitsHereAtAll');
    await userEvent.click(screen.getByRole('button', { name: 'Create account' }));

    expect(await screen.findByText('Include a digit')).toBeInTheDocument();
  });

  it('creates the account and signs the user in', async () => {
    let received: unknown = null;
    server.use(
      http.post(`${API}/auth/register`, async ({ request }) => {
        received = await request.json();
        return HttpResponse.json(
          {
            user: {
              id: 'u2',
              email: 'ada@darukaa.earth',
              full_name: 'Ada Lovelace',
              role: 'admin',
              is_active: true,
              created_at: '2025-01-01T00:00:00Z',
            },
            tokens: {
              access_token: 'a',
              refresh_token: 'r',
              token_type: 'bearer',
              expires_in: 900,
            },
          },
          { status: 201 },
        );
      }),
    );

    renderWithProviders(<RegisterPage />);
    await fillValidForm();
    await userEvent.click(screen.getByRole('button', { name: 'Create account' }));

    await waitFor(() => {
      expect(useAuthStore.getState().isAuthenticated).toBe(true);
    });
    expect(received).toMatchObject({ email: 'ada@darukaa.earth', full_name: 'Ada Lovelace' });
  });

  it('reports a duplicate email from the server', async () => {
    server.use(
      http.post(`${API}/auth/register`, () =>
        HttpResponse.json(
          { error: 'conflict', message: 'An account with this email already exists.' },
          { status: 409 },
        ),
      ),
    );

    renderWithProviders(<RegisterPage />);
    await fillValidForm();
    await userEvent.click(screen.getByRole('button', { name: 'Create account' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(/already exists/i);
  });
});
