import type { RouteObject } from 'react-router-dom';
import { lazyRoute, routeElement } from '@/app/route-lazy';

const OverviewPage = lazyRoute(() => import('./pages/OverviewPage'), 'OverviewPage');

export const overviewRoutes: RouteObject[] = [
  {
    path: 'overview',
    element: routeElement(OverviewPage),
  },
];
