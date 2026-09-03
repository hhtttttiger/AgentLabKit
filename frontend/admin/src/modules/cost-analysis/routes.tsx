import { Navigate, type RouteObject } from 'react-router-dom';
import { lazyRoute, routeElement } from '@/app/route-lazy';

const CostAnalysisLayout = lazyRoute(() => import('./pages/CostAnalysisLayout'), 'CostAnalysisLayout');
const CostOverviewPage = lazyRoute(() => import('./resources/overview/CostOverviewPage'), 'CostOverviewPage');
const BudgetsPage = lazyRoute(() => import('./resources/budgets/BudgetsPage'), 'BudgetsPage');
const AlertsPage = lazyRoute(() => import('./resources/alerts/AlertsPage'), 'AlertsPage');

export const costAnalysisRoutes: RouteObject[] = [
  // New primary route
  {
    path: 'cost',
    element: routeElement(CostAnalysisLayout),
    children: [
      { index: true, element: routeElement(CostOverviewPage) },
      { path: 'budgets', element: routeElement(BudgetsPage) },
      { path: 'alerts', element: routeElement(AlertsPage) },
    ],
  },
  // Legacy route alias
  {
    path: 'cost-analysis',
    element: <Navigate replace to="/cost" />,
  },
  {
    path: 'cost-analysis/*',
    element: <Navigate replace to="/cost" />,
  },
];
