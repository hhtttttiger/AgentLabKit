import type { RouteObject } from 'react-router-dom';
import { lazyRoute, routeElement } from '@/app/route-lazy';

const ProjectsPage = lazyRoute(() => import('./pages/ProjectsPage'), 'ProjectsPage');
export const projectRoutes: RouteObject[] = [{ path: 'projects', element: routeElement(ProjectsPage) }];
