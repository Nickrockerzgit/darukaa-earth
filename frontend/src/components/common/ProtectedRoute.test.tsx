import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it } from 'vitest';

import { ProtectedRoute, PublicOnlyRoute } from '@/components/common/ProtectedRoute';
import { useAuthStore } from '@/features/auth/store/authStore';

function setAuth(isAuthenticated: boolean, isHydrating = false) {
  useAuthStore.setState({ isAuthenticated, isHydrating });
}

function renderRoutes(initial: string) {
  return render(
    <MemoryRouter
      initialEntries={[initial]}
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      <Routes>
        <Route element={<ProtectedRoute />}>
          <Route path="/dashboard" element={<p>Dashboard</p>} />
        </Route>
        <Route element={<PublicOnlyRoute />}>
          <Route path="/login" element={<p>Login</p>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  setAuth(false);
});

describe('ProtectedRoute', () => {
  it('renders the page for a signed-in user', () => {
    setAuth(true);
    renderRoutes('/dashboard');
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
  });

  it('redirects a signed-out user to login', () => {
    renderRoutes('/dashboard');
    expect(screen.getByText('Login')).toBeInTheDocument();
  });

  it('waits rather than redirecting while the session is being restored', () => {
    // Redirecting first would bounce a signed-in user to login on every
    // hard refresh, before localStorage has been read back.
    setAuth(false, true);
    renderRoutes('/dashboard');

    expect(screen.queryByText('Login')).not.toBeInTheDocument();
    expect(screen.getByLabelText('Loading session')).toBeInTheDocument();
  });
});

describe('PublicOnlyRoute', () => {
  it('renders login for a signed-out user', () => {
    renderRoutes('/login');
    expect(screen.getByText('Login')).toBeInTheDocument();
  });

  it('sends a signed-in user to the dashboard', () => {
    setAuth(true);
    renderRoutes('/login');
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
  });

  it('renders nothing while hydrating', () => {
    setAuth(false, true);
    const { container } = renderRoutes('/login');
    expect(container).toBeEmptyDOMElement();
  });
});
