import { useRouteError } from 'react-router-dom';
import type { RouteObject } from 'react-router-dom';
import { lazyRoute, routeElement } from '@/app/route-lazy';
import { ErrorFallback } from '@/shared/error/ErrorFallback';

const MemoryLayout = lazyRoute(() => import('./pages/MemoryLayout'), 'MemoryLayout');
const MemoryListPage = lazyRoute(() => import('./resources/memories/MemoryListPage'), 'MemoryListPage');

function RouteErrorBoundary() {
  const error = useRouteError() as Error;
  return <ErrorFallback error={error} onReset={() => window.location.reload()} />;
}

export const memoryRoutes: RouteObject[] = [
  {
    path: 'memory',
    element: routeElement(MemoryLayout),
    errorElement: <RouteErrorBoundary />,
    children: [
      { index: true, element: routeElement(MemoryListPage) },
    ],
  },
];
