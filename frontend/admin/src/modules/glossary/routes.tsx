import type { RouteObject } from 'react-router-dom';
import { lazyRoute, routeElement } from '@/app/route-lazy';

const GlossaryListPage = lazyRoute(() => import('./pages/GlossaryListPage'), 'GlossaryListPage');
const GlossaryCategoryLayout = lazyRoute(() => import('./pages/GlossaryCategoryLayout'), 'GlossaryCategoryLayout');
const CategoryTermsTab = lazyRoute(() => import('./pages/tabs/CategoryTermsTab'), 'CategoryTermsTab');

export const glossaryRoutes: RouteObject[] = [
  {
    path: 'glossary',
    children: [
      { index: true, element: routeElement(GlossaryListPage) },
      {
        path: ':categoryId',
        element: routeElement(GlossaryCategoryLayout),
        children: [
          { index: true, element: routeElement(CategoryTermsTab) },
        ],
      },
    ],
  },
];
