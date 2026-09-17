import { QueryClientProvider } from '@tanstack/react-query';
import { RouterProvider } from 'react-router-dom';

import { ErrorBoundary } from '@/components/common/ErrorBoundary';
import { PageFallback } from '@/components/common/PageFallback';
import { Toaster } from '@/components/ui/Toast';
import { useSessionBootstrap } from '@/features/auth/hooks/useAuth';
import { queryClient } from '@/app/queryClient';
import { router } from '@/app/router';
import { applyHighchartsTheme } from '@/lib/highcharts';

// Highcharts merges global options into charts at creation time, so the theme
// must be registered before any chart mounts.
applyHighchartsTheme();

function Routes() {
  const { isHydrating } = useSessionBootstrap();
  if (isHydrating) return <PageFallback />;
  return <RouterProvider router={router} />;
}

export function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <Routes />
        <Toaster />
      </QueryClientProvider>
    </ErrorBoundary>
  );
}
