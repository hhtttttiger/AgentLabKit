import type { ReactElement } from 'react';
import { Navigate } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { appRouteTree } from './router';

// The route tree is nested: [ { element: AuthLayout, children: [ { path: '/login' }, { path: '/', children: [...] } ] } ]
const authLayoutRoute = appRouteTree[0];
const authChildren = authLayoutRoute?.children ?? [];

describe('app route tree', () => {
  it('has a public login route', () => {
    const loginRoute = authChildren.find((r) => r.path === '/login');
    expect(loginRoute).toBeDefined();
  });

  it('redirects root index route to overview', () => {
    const rootRoute = authChildren.find((r) => r.path === '/');
    const indexRoute = rootRoute?.children?.[0];
    const element = indexRoute?.element as ReactElement<{ to: string }>;

    expect(rootRoute?.path).toBe('/');
    expect(indexRoute?.index).toBe(true);
    expect(element.type).toBe(Navigate);
    expect(element.props.to).toBe('/overview');
  });

  it('registers monitoring routes under the protected shell', () => {
    const rootRoute = authChildren.find((r) => r.path === '/');
    const monitoringRoute = rootRoute?.children?.find((r) => r.path === 'monitoring');

    expect(monitoringRoute).toBeDefined();
    expect(monitoringRoute?.children?.some((child) => child.index === true)).toBe(true);
    expect(monitoringRoute?.children?.some((child) => child.path === 'errors')).toBe(true);
  });

  it('registers playground route under the protected shell', () => {
    const rootRoute = authChildren.find((r) => r.path === '/');
    const playgroundRoute = rootRoute?.children?.find((r) => r.path === 'playground');

    expect(playgroundRoute).toBeDefined();
  });

  it('registers agents route under the protected shell', () => {
    const rootRoute = authChildren.find((r) => r.path === '/');
    const agentsRoute = rootRoute?.children?.find((r) => r.path === 'agents');

    expect(agentsRoute).toBeDefined();
  });

  it('registers models route under the protected shell', () => {
    const rootRoute = authChildren.find((r) => r.path === '/');
    const modelsRoute = rootRoute?.children?.find((r) => r.path === 'models');

    expect(modelsRoute).toBeDefined();
  });

});
