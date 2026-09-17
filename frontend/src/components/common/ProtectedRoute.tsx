import { Loader2 } from 'lucide-react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';

import { useAuthStore } from '@/features/auth/store/authStore';

/**
 * Route guard for authenticated pages.
 *
 * While the persisted session is being read back, it renders a spinner rather
 * than redirecting: redirecting first would bounce a signed-in user to the
 * login screen on every hard refresh.
 */
export function ProtectedRoute() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const isHydrating = useAuthStore((state) => state.isHydrating);
  const location = useLocation();

  if (isHydrating) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-brand-500" aria-label="Loading session" />
      </div>
    );
  }

  if (!isAuthenticated) {
    // `state.from` lets the login page send the user back where they meant to go.
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return <Outlet />;
}

/** Keeps a signed-in user away from the login and register screens. */
export function PublicOnlyRoute() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const isHydrating = useAuthStore((state) => state.isHydrating);

  if (isHydrating) return null;
  if (isAuthenticated) return <Navigate to="/dashboard" replace />;
  return <Outlet />;
}
