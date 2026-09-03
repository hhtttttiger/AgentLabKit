/**
 * Runs Module - Routes
 */

import { Navigate, useLocation, type RouteObject } from 'react-router-dom';
import { lazyRoute, routeElement } from '@/app/route-lazy';

const RunsListPage = lazyRoute(() => import('./pages/RunsListPage'), 'RunsListPage');
const RunDetailPage = lazyRoute(() => import('./pages/RunDetailPage'), 'RunDetailPage');
const RunReplayPage = lazyRoute(() => import('./pages/RunReplayPage'), 'RunReplayPage');

function LegacyRunCompareRedirect() {
  const location = useLocation();
  return <Navigate replace to={{ pathname: '/evaluation/runs/compare', search: location.search }} />;
}

export const runsRoutes: RouteObject[] = [
  {
    path: 'runs',
    element: routeElement(RunsListPage),
  },
  {
    path: 'runs/compare',
    element: <LegacyRunCompareRedirect />,
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
