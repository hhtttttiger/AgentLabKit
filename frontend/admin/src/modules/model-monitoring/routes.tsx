import type { RouteObject } from 'react-router-dom';
import { lazyRoute, routeElement } from '@/app/route-lazy';

const ModelMonitoringLayout = lazyRoute(() => import('./pages/ModelMonitoringLayout'), 'ModelMonitoringLayout');
const UsagePage = lazyRoute(() => import('./resources/usage/UsagePage'), 'UsagePage');
const ErrorsPage = lazyRoute(() => import('./resources/errors/ErrorsPage'), 'ErrorsPage');

export const modelMonitoringRoutes: RouteObject[] = [
  {
    path: 'model-monitoring',
    element: routeElement(ModelMonitoringLayout),
    children: [
      { index: true, element: routeElement(UsagePage) },
      { path: 'errors', element: routeElement(ErrorsPage) },
    ],
  },
];
