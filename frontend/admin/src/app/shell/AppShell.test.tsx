import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useEffect, useState } from 'react';
import { RouterProvider, createMemoryRouter, type RouteObject } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { switchTestLanguage } from '@/shared/test/setup';
import { createStorageMock } from '@/shared/test/storage';

const { useMediaQueryMock } = vi.hoisted(() => ({ useMediaQueryMock: vi.fn(() => false) }));

vi.mock('@/shared/hooks/useMediaQuery', () => ({ useMediaQuery: useMediaQueryMock }));
vi.mock('@/shared/auth', () => ({
  useAuth: () => ({ user: { userName: 'admin', userId: 1 }, logout: vi.fn() }),
}));
vi.mock('@/shared/ui/UserMenu', () => ({
  UserMenu: ({ displayName }: { displayName: string }) => <div>{displayName}</div>,
}));

import { AppShell } from './AppShell';

const storage = createStorageMock();

function StableRouteProbePage() {
  const [value, setValue] = useState('persist me');
  const [mountCount, setMountCount] = useState(0);

  useEffect(() => {
    setMountCount((count) => count + 1);
  }, []);

  return (
    <div>
      <label htmlFor="route-probe-input">Probe</label>
      <input
        id="route-probe-input"
        value={value}
        onChange={(event) => setValue(event.target.value)}
      />
      <div data-testid="mount-count">{mountCount}</div>
      <div data-testid="route-value">{value}</div>
    </div>
  );
}

function setup() {
  const routes: RouteObject[] = [
    {
      path: '/',
      element: <AppShell />,
      children: [
        {
          path: 'model-management',
          element: <StableRouteProbePage />,
        },
      ],
    },
  ];
  const router = createMemoryRouter(routes, {
    initialEntries: ['/model-management'],
  });

  return render(<RouterProvider router={router} />);
}

describe('AppShell sidebar auto-collapse', () => {
  beforeEach(() => {
    vi.stubGlobal('localStorage', storage);
    useMediaQueryMock.mockReturnValue(false);
    localStorage.clear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('sidebar is expanded on wide screens by default', () => {
    setup();
    expect(document.querySelector('.admin-shell')).not.toHaveClass('admin-shell--collapsed');
  });

  it('sidebar is collapsed on small screens by default', () => {
    useMediaQueryMock.mockReturnValue(true);
    setup();
    expect(document.querySelector('.admin-shell')).toHaveClass('admin-shell--collapsed');
  });

  it('force-expand on small screen persists the flag in localStorage', async () => {
    useMediaQueryMock.mockReturnValue(true);
    const user = userEvent.setup();
    setup();
    await user.click(screen.getByRole('button', { name: '展开菜单' }));
    expect(document.querySelector('.admin-shell')).not.toHaveClass('admin-shell--collapsed');
    expect(localStorage.getItem('agentlabkit-sidebar-force-expanded')).toBe('true');
  });

  it('collapsing clears force-expanded flag', async () => {
    useMediaQueryMock.mockReturnValue(true);
    localStorage.setItem('agentlabkit-sidebar-force-expanded', 'true');
    const user = userEvent.setup();
    setup();
    await user.click(screen.getByRole('button', { name: '收起菜单' }));
    expect(localStorage.getItem('agentlabkit-sidebar-force-expanded')).toBeNull();
  });

  it('does not remount the routed child when the admin locale changes', async () => {
    await switchTestLanguage('zh-CN');
    const user = userEvent.setup();
    setup();

    const input = screen.getByLabelText('Probe');
    await user.clear(input);
    await user.type(input, 'keep this state');

    expect(screen.getByTestId('mount-count')).toHaveTextContent('1');
    expect(screen.getByTestId('route-value')).toHaveTextContent('keep this state');

    await act(async () => {
      await switchTestLanguage('en-US');
    });

    await waitFor(() => {
      expect(screen.getByTestId('mount-count')).toHaveTextContent('1');
    });
    expect(screen.getByTestId('route-value')).toHaveTextContent('keep this state');
    expect(screen.getByLabelText('Probe')).toHaveValue('keep this state');
  });
});
