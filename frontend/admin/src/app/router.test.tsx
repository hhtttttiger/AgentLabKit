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

  it('redirects root index route to model management', () => {
    const rootRoute = authChildren.find((r) => r.path === '/');
    const indexRoute = rootRoute?.children?.[0];
    const element = indexRoute?.element as ReactElement<{ to: string }>;

    expect(rootRoute?.path).toBe('/');
    expect(indexRoute?.index).toBe(true);
    expect(element.type).toBe(Navigate);
    expect(element.props.to).toBe('/model-management');
  });

  it('registers model monitoring routes under the protected shell', () => {
    const rootRoute = authChildren.find((r) => r.path === '/');
    const monitoringRoute = rootRoute?.children?.find((r) => r.path === 'model-monitoring');

    expect(monitoringRoute).toBeDefined();
    expect(monitoringRoute?.children?.some((child) => child.index === true)).toBe(true);
    expect(monitoringRoute?.children?.some((child) => child.path === 'errors')).toBe(true);
  });

  it('registers ai chat route under the protected shell', () => {
    const rootRoute = authChildren.find((r) => r.path === '/');
    const aiChatRoute = rootRoute?.children?.find((r) => r.path === 'ai-chat');

    expect(aiChatRoute).toBeDefined();
  });

  it('redirects agent management index route to the agents list', () => {
    const rootRoute = authChildren.find((r) => r.path === '/');
    const moduleRoute = rootRoute?.children?.find((r) => r.path === 'agent-management');
    const indexRoute = moduleRoute?.children?.find((child) => child.index);
    const element = indexRoute?.element as ReactElement<{ to: string }>;

    expect(moduleRoute).toBeDefined();
    expect(indexRoute?.index).toBe(true);
    expect(element.type).toBe(Navigate);
    expect(element.props.to).toBe('/agent-management/agents');
  });

  it('redirects model management index route to the models list', () => {
    const rootRoute = authChildren.find((r) => r.path === '/');
    const moduleRoute = rootRoute?.children?.find((r) => r.path === 'model-management');
    const indexRoute = moduleRoute?.children?.find((child) => child.index);
    const element = indexRoute?.element as ReactElement<{ to: string }>;

    expect(moduleRoute).toBeDefined();
    expect(indexRoute?.index).toBe(true);
    expect(element.type).toBe(Navigate);
    expect(element.props.to).toBe('/model-management/models');
  });

});
