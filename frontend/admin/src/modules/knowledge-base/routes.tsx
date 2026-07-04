import type { RouteObject } from 'react-router-dom';
import { lazyRoute, routeElement } from '@/app/route-lazy';

const KnowledgeBaseLayout = lazyRoute(() => import('./pages/KnowledgeBaseLayout'), 'KnowledgeBaseLayout');
const KnowledgeBaseListPage = lazyRoute(() => import('./pages/KnowledgeBaseListPage'), 'KnowledgeBaseListPage');
const KbOverviewTab = lazyRoute(() => import('./pages/tabs/KbOverviewTab'), 'KbOverviewTab');
const KbDocumentsTab = lazyRoute(() => import('./pages/tabs/KbDocumentsTab'), 'KbDocumentsTab');
const KbSearchTab = lazyRoute(() => import('./pages/tabs/KbSearchTab'), 'KbSearchTab');
const KbGlossaryTab = lazyRoute(() => import('./pages/tabs/KbGlossaryTab'), 'KbGlossaryTab');

export const knowledgeBaseRoutes: RouteObject[] = [
  {
    path: 'knowledge-base',
    children: [
      { index: true, element: routeElement(KnowledgeBaseListPage) },
      {
        path: ':kbId',
        element: routeElement(KnowledgeBaseLayout),
        children: [
          { index: true, element: routeElement(KbOverviewTab) },
          { path: 'documents', element: routeElement(KbDocumentsTab) },
          { path: 'glossary', element: routeElement(KbGlossaryTab) },
          { path: 'search', element: routeElement(KbSearchTab) },
        ],
      },
    ],
  },
];
