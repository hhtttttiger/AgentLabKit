import { Navigate, type RouteObject } from 'react-router-dom';
import { lazyRoute, routeElement } from '@/app/route-lazy';

const ObservabilityLayout = lazyRoute(() => import('./pages/ObservabilityLayout'), 'ObservabilityLayout');
const TraceListPage = lazyRoute(() => import('./resources/traces/TraceListPage'), 'TraceListPage');
const TraceDetailPage = lazyRoute(() => import('./resources/traces/TraceDetailPage'), 'TraceDetailPage');

export const observabilityRoutes: RouteObject[] = [
  // New primary route
  {
    path: 'traces',
    element: routeElement(ObservabilityLayout),
    children: [
      { index: true, element: routeElement(TraceListPage) },
      { path: ':traceId', element: routeElement(TraceDetailPage) },
    ],
  },
  // Legacy route alias
  {
    path: 'observability',
    element: <Navigate replace to="/traces" />,
  },
  {
    path: 'observability/*',
    element: <Navigate replace to="/traces" />,
  },
];
