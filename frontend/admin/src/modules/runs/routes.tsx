/**
 * Runs Module - Routes
 */

import { Navigate, type RouteObject } from 'react-router-dom';
import { lazyRoute, routeElement } from '@/app/route-lazy';

const RunsListPage = lazyRoute(() => import('./pages/RunsListPage'), 'RunsListPage');
const RunDetailPage = lazyRoute(() => import('./pages/RunDetailPage'), 'RunDetailPage');
const RunReplayPage = lazyRoute(() => import('./pages/RunReplayPage'), 'RunReplayPage');

export const runsRoutes: RouteObject[] = [
  {
    path: 'runs',
    element: routeElement(RunsListPage),
  },
  {
    path: 'runs/compare',
    element: <Navigate replace to="/evaluation/runs/compare" />,
  },
  {
    path: 'runs/:runId',
    element: routeElement(RunDetailPage),
  },
  {
    path: 'runs/:runId/replay',
    element: routeElement(RunReplayPage),
  },
];
