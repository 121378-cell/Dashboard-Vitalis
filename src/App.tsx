import React, { Suspense, lazy } from 'react';
import { createBrowserRouter, RouterProvider, Outlet } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { WebDashboardLayout } from './layout/WebDashboardLayout';

const OverviewPage = lazy(() => import('./pages/OverviewPage').then(m => ({ default: m.OverviewPage })));
const BiometricsPage = lazy(() => import('./pages/BiometricsPage').then(m => ({ default: m.BiometricsPage })));
const TrainingPage = lazy(() => import('./pages/TrainingPage').then(m => ({ default: m.TrainingPage })));
const ReadinessPage = lazy(() => import('./pages/ReadinessPage').then(m => ({ default: m.ReadinessPage })));
const MemoryPage = lazy(() => import('./pages/MemoryPage').then(m => ({ default: m.MemoryPage })));
const PlanPage = lazy(() => import('./pages/PlanPage').then(m => ({ default: m.PlanPage })));
const CoachPage = lazy(() => import('./pages/CoachPage').then(m => ({ default: m.CoachPage })));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      refetchOnReconnect: true,
      staleTime: 5 * 60 * 1000,
      gcTime: 30 * 60 * 1000,
      retry: 2,
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
    },
  },
});

const DashboardLayout = () => (
  <WebDashboardLayout>
    <Outlet />
  </WebDashboardLayout>
);

const PageFallback = () => (
  <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '50vh' }}>
    <span style={{ color: 'var(--muted-foreground, #888)' }}>Cargando...</span>
  </div>
);

const router = createBrowserRouter([
  {
    path: '/',
    element: <DashboardLayout />,
    children: [
      { index: true, element: <Suspense fallback={<PageFallback />}><OverviewPage /></Suspense> },
      { path: 'overview', element: <Suspense fallback={<PageFallback />}><OverviewPage /></Suspense> },
      { path: 'biometrics', element: <Suspense fallback={<PageFallback />}><BiometricsPage /></Suspense> },
      { path: 'training', element: <Suspense fallback={<PageFallback />}><TrainingPage /></Suspense> },
      { path: 'readiness', element: <Suspense fallback={<PageFallback />}><ReadinessPage /></Suspense> },
      { path: 'memory', element: <Suspense fallback={<PageFallback />}><MemoryPage /></Suspense> },
      { path: 'plan', element: <Suspense fallback={<PageFallback />}><PlanPage /></Suspense> },
      { path: 'coach', element: <Suspense fallback={<PageFallback />}><CoachPage /></Suspense> },
    ],
  },
]);

const App = () => (
  <QueryClientProvider client={queryClient}>
    <RouterProvider router={router} />
    <ReactQueryDevtools initialIsOpen={false} />
  </QueryClientProvider>
);

export default App;
