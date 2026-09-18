import { Navigate, type RouteObject } from 'react-router-dom';
import { lazyRoute, routeElement } from '@/app/route-lazy';

const ModelSettingsPage = lazyRoute(() => import('./pages/ModelSettingsPage'), 'ModelSettingsPage');

export const settingsRoutes: RouteObject[] = [
  { path: 'settings', element: <Navigate replace to="/settings/models" /> },
  { path: 'settings/models', element: routeElement(ModelSettingsPage) },
];
