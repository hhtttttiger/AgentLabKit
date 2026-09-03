import { Navigate, type RouteObject } from 'react-router-dom';
import { lazyRoute, routeElement } from '@/app/route-lazy';

const ModelMonitoringLayout = lazyRoute(() => import('./pages/ModelMonitoringLayout'), 'ModelMonitoringLayout');
const UsagePage = lazyRoute(() => import('./resources/usage/UsagePage'), 'UsagePage');
const ErrorsPage = lazyRoute(() => import('./resources/errors/ErrorsPage'), 'ErrorsPage');

export const modelMonitoringRoutes: RouteObject[] = [
  // New primary route
  {
    path: 'monitoring',
    element: routeElement(ModelMonitoringLayout),
    children: [
      { index: true, element: routeElement(UsagePage) },
      { path: 'errors', element: routeElement(ErrorsPage) },
    ],
  },
  // Legacy route alias
  {
    path: 'model-monitoring',
    element: <Navigate replace to="/monitoring" />,
  },
  {
    path: 'model-monitoring/*',
    element: <Navigate replace to="/monitoring" />,
  },
];
