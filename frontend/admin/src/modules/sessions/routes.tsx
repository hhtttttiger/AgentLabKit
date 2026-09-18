import { lazyRoute, routeElement } from '@/app/route-lazy';
import type { RouteObject } from 'react-router-dom';

const SessionsPage = lazyRoute(() => import('./pages/SessionsPage'), 'SessionsPage');

export const sessionsRoutes: RouteObject[] = [
  { path: 'sessions', element: routeElement(SessionsPage) },
];
