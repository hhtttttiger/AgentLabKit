import { Navigate, Outlet, RouterProvider, createBrowserRouter, createMemoryRouter, type RouteObject } from 'react-router-dom';
import { moduleRoutes } from './modules';
import { LoginPage } from './pages/LoginPage';
import { AppShell } from './shell/AppShell';
import { AuthGuard, AuthProvider } from '@/shared/auth';

function AuthLayout() {
  return (
    <AuthProvider>
      <Outlet />
    </AuthProvider>
  );
}

export const appRouteTree: RouteObject[] = [
  {
    element: <AuthLayout />,
    children: [
      {
        path: '/login',
        element: <LoginPage />,
      },
      {
        path: '/',
        element: (
          <AuthGuard>
            <AppShell />
          </AuthGuard>
        ),
        children: [
          { index: true, element: <Navigate replace to="/model-management" /> },
          ...moduleRoutes,
        ],
      },
    ],
  },
];

const basename = import.meta.env.BASE_URL.replace(/\/+$/, '') || undefined;
const router = createBrowserRouter(appRouteTree, { basename });

export function createTestRouter(initialEntries: string[]) {
  return createMemoryRouter(appRouteTree, {
    initialEntries,
  });
}

export function AppRouter() {
  return <RouterProvider router={router} />;
}
