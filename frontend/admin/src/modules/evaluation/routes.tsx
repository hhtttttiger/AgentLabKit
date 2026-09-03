import { Navigate, type RouteObject } from 'react-router-dom';
import { lazyRoute, routeElement } from '@/app/route-lazy';

const EvaluationLayout = lazyRoute(() => import('./pages/EvaluationLayout'), 'EvaluationLayout');
const EvaluationOverviewPage = lazyRoute(() => import('./pages/EvaluationOverviewPage'), 'EvaluationOverviewPage');
const DatasetsPage = lazyRoute(() => import('./resources/datasets/DatasetsPage'), 'DatasetsPage');
const DatasetDetailPage = lazyRoute(() => import('./resources/datasets/DatasetDetailPage'), 'DatasetDetailPage');
const RunsPage = lazyRoute(() => import('./resources/runs/RunsPage'), 'RunsPage');
const RunDetailPage = lazyRoute(() => import('./resources/runs/RunDetailPage'), 'RunDetailPage');
const RunComparePage = lazyRoute(() => import('@/modules/runs/pages/RunComparePage'), 'RunComparePage');

export const evaluationRoutes: RouteObject[] = [
  {
    path: 'evaluation',
    element: routeElement(EvaluationLayout),
    children: [
      { index: true, element: <Navigate replace to="/evaluation/overview" /> },
      { path: 'overview', element: routeElement(EvaluationOverviewPage) },
      { path: 'datasets', element: routeElement(DatasetsPage) },
      { path: 'dataset/:datasetId', element: routeElement(DatasetDetailPage) },
      { path: 'runs', element: routeElement(RunsPage) },
      { path: 'runs/compare', element: routeElement(RunComparePage) },
      { path: 'runs/:runId', element: routeElement(RunDetailPage) },
    ],
  },
];
