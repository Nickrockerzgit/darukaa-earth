import { lazy, Suspense } from 'react';
import { createBrowserRouter, Navigate } from 'react-router-dom';

import { AppShell } from '@/components/layout/AppShell';
import { ErrorBoundary } from '@/components/common/ErrorBoundary';
import { ProtectedRoute, PublicOnlyRoute } from '@/components/common/ProtectedRoute';
import { LoginPage } from '@/features/auth/pages/LoginPage';
import { RegisterPage } from '@/features/auth/pages/RegisterPage';
import { DashboardPage } from '@/features/projects/pages/DashboardPage';
import { PageFallback } from '@/components/common/PageFallback';

// Mapbox GL and Highcharts together are most of the bundle. Splitting the
// routes that need them keeps the login screen's first paint small.
const ProjectDetailPage = lazy(() =>
  import('@/features/projects/pages/ProjectDetailPage').then((module) => ({
    default: module.ProjectDetailPage,
  })),
);
const MapPage = lazy(() =>
  import('@/features/map/pages/MapPage').then((module) => ({ default: module.MapPage })),
);

export const router = createBrowserRouter(
  [
    {
      element: <PublicOnlyRoute />,
      children: [
        { path: '/login', element: <LoginPage /> },
        { path: '/register', element: <RegisterPage /> },
      ],
    },
    {
      element: <ProtectedRoute />,
      children: [
        {
          element: <AppShell />,
          children: [
            { path: '/dashboard', element: <DashboardPage /> },
            {
              path: '/projects/:projectId',
              element: (
                <ErrorBoundary area="the project workspace">
                  <Suspense fallback={<PageFallback />}>
                    <ProjectDetailPage />
                  </Suspense>
                </ErrorBoundary>
              ),
            },
            {
              path: '/map',
              element: (
                <ErrorBoundary area="the map">
                  <Suspense fallback={<PageFallback />}>
                    <MapPage />
                  </Suspense>
                </ErrorBoundary>
              ),
            },
          ],
        },
      ],
    },
    { path: '/', element: <Navigate to="/dashboard" replace /> },
    { path: '*', element: <Navigate to="/dashboard" replace /> },
  ],
  {
    // Opt in to the v7 behaviours now, so the upgrade is a version bump
    // rather than a behavioural surprise.
    future: {
      v7_relativeSplatPath: true,
      v7_fetcherPersist: true,
      v7_normalizeFormMethod: true,
      v7_partialHydration: true,
      v7_skipActionErrorRevalidation: true,
    },
  },
);
