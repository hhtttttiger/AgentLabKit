import { lazyRoute, routeElement } from '@/app/route-lazy';
import type { RouteObject } from 'react-router-dom';

const SessionsPage = lazyRoute(() => import('./pages/SessionsPage'), 'SessionsPage');
const NewSessionPage = lazyRoute(() => import('./pages/NewSessionPage'), 'NewSessionPage');

export const sessionsRoutes: RouteObject[] = [
  { path: 'sessions/new', element: routeElement(NewSessionPage) },
  { path: 'sessions', element: routeElement(SessionsPage) },
];
