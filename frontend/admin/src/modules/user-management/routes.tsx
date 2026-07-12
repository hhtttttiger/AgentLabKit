import type { RouteObject } from 'react-router-dom';
import { lazyRoute, routeElement } from '@/app/route-lazy';

const UsersPage = lazyRoute(() => import('./pages/UsersPage'), 'UsersPage');

export const userManagementRoutes: RouteObject[] = [
  {
    path: 'user-management',
    children: [
      { index: true, element: routeElement(UsersPage) },
    ],
  },
];
