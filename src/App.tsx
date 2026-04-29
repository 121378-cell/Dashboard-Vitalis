import React from 'react';
import { createBrowserRouter, RouterProvider, Outlet } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { WebDashboardLayout } from './layout/WebDashboardLayout';
import { OverviewPage } from './pages/OverviewPage';
import { BiometricsPage } from './pages/BiometricsPage';
import { TrainingPage } from './pages/TrainingPage';
import { ReadinessPage } from './pages/ReadinessPage';
import { MemoryPage } from './pages/MemoryPage';

// Initialize React Query Client
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

// Dashboard Layout Wrapper
const DashboardLayout = () => (
  <WebDashboardLayout>
    <Outlet />
  </WebDashboardLayout>
);

// Router Configuration
const router = createBrowserRouter([
  {
    path: '/',
    element: <DashboardLayout />,
    children: [
      {
        index: true,
        element: <OverviewPage />,
      },
      {
        path: 'overview',
        element: <OverviewPage />,
      },
      {
        path: 'biometrics',
        element: <BiometricsPage />,
      },
      {
        path: 'training',
        element: <TrainingPage />,
      },
      {
        path: 'readiness',
        element: <ReadinessPage />,
      },
      {
        path: 'memory',
        element: <MemoryPage />,
      },
    ],
  },
]);

// Root App Component
const App = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  );
};

export default App;
