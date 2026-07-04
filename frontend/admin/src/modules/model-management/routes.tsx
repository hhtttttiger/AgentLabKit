import { Navigate, type RouteObject } from 'react-router-dom';
import { lazyRoute, routeElement } from '@/app/route-lazy';

const ModelManagementLayout = lazyRoute(() => import('./pages/ModelManagementLayout'), 'ModelManagementLayout');
const ModelDetailLayout = lazyRoute(() => import('./pages/ModelCardDetailLayout'), 'ModelDetailLayout');
const ConnectionProfilesPage = lazyRoute(() => import('./resources/connection-profiles/ConnectionProfilesPage'), 'ConnectionProfilesPage');
const ModelBindingsPage = lazyRoute(() => import('./resources/model-bindings/ModelBindingsPage'), 'ModelBindingsPage');
const ModelsPage = lazyRoute(() => import('./resources/model-cards/ModelCardsPage'), 'ModelsPage');
const ModelInstancesByModelPage = lazyRoute(() => import('./resources/model-instances/ModelInstancesByModelPage'), 'ModelInstancesByModelPage');
const FeatureDefinitionsPage = lazyRoute(() => import('./resources/feature-definitions/FeatureDefinitionsPage'), 'FeatureDefinitionsPage');
const ModelOverviewTab = lazyRoute(() => import('./resources/model-cards/tabs/ModelCardOverviewTab'), 'ModelOverviewTab');
const ModelInstancesTab = lazyRoute(() => import('./resources/model-cards/tabs/ModelCardInstancesTab'), 'ModelInstancesTab');
const ModelBindingsTab = lazyRoute(() => import('./resources/model-cards/tabs/ModelCardBindingsTab'), 'ModelBindingsTab');

export const modelManagementRoutes: RouteObject[] = [
  {
    path: 'model-management',
    children: [
      { index: true, element: <Navigate replace to="/model-management/models" /> },
      // List pages — wrapped in the tab navigation layout
      {
        element: routeElement(ModelManagementLayout),
        children: [
          { path: 'connection-profiles', element: routeElement(ConnectionProfilesPage) },
          { path: 'models', element: routeElement(ModelsPage) },
          { path: 'model-instances', element: routeElement(ModelInstancesByModelPage) },
          { path: 'model-bindings', element: routeElement(ModelBindingsPage) },
          { path: 'features', element: routeElement(FeatureDefinitionsPage) },
        ],
      },
      // Detail page — has its own ModuleLayoutShell with breadcrumb + tabs
      {
        path: 'models/:modelKey',
        element: routeElement(ModelDetailLayout),
        children: [
          { index: true, element: routeElement(ModelOverviewTab) },
          { path: 'instances', element: routeElement(ModelInstancesTab) },
          { path: 'bindings', element: routeElement(ModelBindingsTab) },
        ],
      },
    ],
  },
];
