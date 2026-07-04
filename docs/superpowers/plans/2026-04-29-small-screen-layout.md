# Small-Screen Layout Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix crowded UI on 1080p + 150% DPI (≈1280px CSS) screens via auto-collapsing sidebar, ⋯ action dropdown, and compact table rows.

**Architecture:** Three independent layers — (A) `AppShell` reads viewport width via `useMediaQuery` and auto-collapses the sidebar unless the user has explicitly force-expanded; (B) a new `RowActions` shared component replaces per-page inline button stacks; (C) `DataTable` cell padding tightened globally.

**Tech Stack:** React 18, Tailwind CSS (via class names), Vitest + Testing Library, lucide-react icons.

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `src/shared/hooks/useMediaQuery.ts` | **Create** | Subscribe to `window.matchMedia`, return live boolean |
| `src/shared/hooks/useMediaQuery.test.ts` | **Create** | Verify hook reacts to media query changes |
| `src/app/shell/AppShell.tsx` | **Modify** | Add auto-collapse: derive `collapsed` from viewport + user prefs |
| `src/app/shell/AppShell.test.tsx` | **Create** | Verify auto-collapse and force-expand behaviour |
| `src/shared/ui/RowActions.tsx` | **Create** | `⋯` trigger + floating action menu, closes on outside-click/Escape |
| `src/shared/ui/RowActions.test.tsx` | **Create** | Verify open/close/action/keyboard behaviour |
| `src/modules/agent-management/resources/agents/AgentsPage.tsx` | **Modify** | Replace inline button pair with `<RowActions>` |
| `src/modules/agent-management/resources/agents/AgentsPage.test.tsx` | **Modify** | Update test to open menu before clicking action |
| `src/shared/ui/DataTable.tsx` | **Modify** | Tighten `td`/`th` padding |

---

## Task 1: `useMediaQuery` hook

**Files:**
- Create: `src/shared/hooks/useMediaQuery.ts`
- Create: `src/shared/hooks/useMediaQuery.test.ts`

- [ ] **Step 1.1 — Write the failing test**

```ts
// src/shared/hooks/useMediaQuery.test.ts
import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useMediaQuery } from './useMediaQuery';

function makeMql(matches: boolean) {
  const listeners: Array<(e: MediaQueryListEvent) => void> = [];
  return {
    matches,
    addEventListener: (_: string, fn: (e: MediaQueryListEvent) => void) => listeners.push(fn),
    removeEventListener: (_: string, fn: (e: MediaQueryListEvent) => void) => {
      const i = listeners.indexOf(fn);
      if (i !== -1) listeners.splice(i, 1);
    },
    _fire(nextMatches: boolean) {
      listeners.forEach((fn) => fn({ matches: nextMatches } as MediaQueryListEvent));
    },
  };
}

let mql: ReturnType<typeof makeMql>;

beforeEach(() => {
  mql = makeMql(false);
  vi.spyOn(window, 'matchMedia').mockReturnValue(mql as unknown as MediaQueryList);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('useMediaQuery', () => {
  it('returns the initial match state', () => {
    mql = makeMql(true);
    vi.spyOn(window, 'matchMedia').mockReturnValue(mql as unknown as MediaQueryList);
    const { result } = renderHook(() => useMediaQuery('(max-width: 1400px)'));
    expect(result.current).toBe(true);
  });

  it('updates when the media query fires a change event', () => {
    const { result } = renderHook(() => useMediaQuery('(max-width: 1400px)'));
    expect(result.current).toBe(false);
    act(() => { mql._fire(true); });
    expect(result.current).toBe(true);
  });

  it('removes the event listener on unmount', () => {
    const removespy = vi.spyOn(mql, 'removeEventListener');
    const { unmount } = renderHook(() => useMediaQuery('(max-width: 1400px)'));
    unmount();
    expect(removespy).toHaveBeenCalledOnce();
  });
});
```

- [ ] **Step 1.2 — Run to confirm FAIL**

```bash
cd templates/react-ts/ai-admin
npx vitest run src/shared/hooks/useMediaQuery.test.ts
```
Expected: `Cannot find module './useMediaQuery'`

- [ ] **Step 1.3 — Implement the hook**

```ts
// src/shared/hooks/useMediaQuery.ts
import { useEffect, useState } from 'react';

export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(() => window.matchMedia(query).matches);

  useEffect(() => {
    const mql = window.matchMedia(query);
    const handler = (e: MediaQueryListEvent) => setMatches(e.matches);
    mql.addEventListener('change', handler);
    return () => mql.removeEventListener('change', handler);
  }, [query]);

  return matches;
}
```

- [ ] **Step 1.4 — Run to confirm PASS**

```bash
npx vitest run src/shared/hooks/useMediaQuery.test.ts
```
Expected: `3 tests passed`

- [ ] **Step 1.5 — Commit**

```bash
git add src/shared/hooks/useMediaQuery.ts src/shared/hooks/useMediaQuery.test.ts
git commit -m "feat: add useMediaQuery hook"
```

---

## Task 2: Auto-collapse sidebar in `AppShell`

**Files:**
- Modify: `src/app/shell/AppShell.tsx`
- Create: `src/app/shell/AppShell.test.tsx`

**Logic summary:**
- `userCollapsed` (bool, localStorage `ai-admin-sidebar-collapsed`) — user explicitly collapsed
- `forceExpanded` (bool, localStorage `ai-admin-sidebar-force-expanded`) — user explicitly expanded on a small screen
- `isSmallScreen` = `useMediaQuery('(max-width: 1400px)')`
- `collapsed = forceExpanded ? false : (userCollapsed || isSmallScreen)`
- Toggle: if expanding on a small screen → set `forceExpanded=true`; if collapsing → clear `forceExpanded`

- [ ] **Step 2.1 — Write the failing test**

```tsx
// src/app/shell/AppShell.test.tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const { useMediaQueryMock } = vi.hoisted(() => ({ useMediaQueryMock: vi.fn(() => false) }));

vi.mock('@/shared/hooks/useMediaQuery', () => ({ useMediaQuery: useMediaQueryMock }));
vi.mock('@/shared/auth', () => ({
  useAuth: () => ({ user: { userName: 'admin', userId: 1 }, logout: vi.fn() }),
}));
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>();
  return { ...actual, Outlet: () => <div>outlet</div>, useNavigate: () => vi.fn() };
});

// Import AppShell after mocks
const { AppShell } = await import('./AppShell');

function setup() {
  localStorage.clear();
  return render(<MemoryRouter><AppShell /></MemoryRouter>);
}

describe('AppShell sidebar auto-collapse', () => {
  beforeEach(() => {
    useMediaQueryMock.mockReturnValue(false);
    localStorage.clear();
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

  it('force-expand on small screen persists across remount', async () => {
    useMediaQueryMock.mockReturnValue(true);
    const user = userEvent.setup();
    setup();
    // sidebar starts collapsed — click toggle to expand
    await user.click(screen.getByRole('button', { name: '展开菜单' }));
    expect(document.querySelector('.admin-shell')).not.toHaveClass('admin-shell--collapsed');
    expect(localStorage.getItem('ai-admin-sidebar-force-expanded')).toBe('true');
  });

  it('collapsing clears force-expanded flag', async () => {
    useMediaQueryMock.mockReturnValue(true);
    localStorage.setItem('ai-admin-sidebar-force-expanded', 'true');
    const user = userEvent.setup();
    setup();
    // starts expanded (force-expanded)
    await user.click(screen.getByRole('button', { name: '收起菜单' }));
    expect(localStorage.getItem('ai-admin-sidebar-force-expanded')).toBeNull();
  });
});
```

- [ ] **Step 2.2 — Run to confirm FAIL**

```bash
npx vitest run src/app/shell/AppShell.test.tsx
```
Expected: `useMediaQuery is not mocked` or behaviour assertions fail

- [ ] **Step 2.3 — Update AppShell**

Replace `src/app/shell/AppShell.tsx` entirely with:

```tsx
import { useState } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { AppSidebar } from './AppSidebar';
import { appModules } from '../modules';
import { useAuth } from '@/shared/auth';
import { UserMenu } from '@/shared/ui/UserMenu';
import { useMediaQuery } from '@/shared/hooks/useMediaQuery';

const SIDEBAR_COLLAPSED_KEY = 'ai-admin-sidebar-collapsed';
const SIDEBAR_FORCE_EXPANDED_KEY = 'ai-admin-sidebar-force-expanded';

function loadUserCollapsed(): boolean {
  return window.localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === 'true';
}

function loadForceExpanded(): boolean {
  return window.localStorage.getItem(SIDEBAR_FORCE_EXPANDED_KEY) === 'true';
}

export function AppShell() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [userCollapsed, setUserCollapsed] = useState(loadUserCollapsed);
  const [forceExpanded, setForceExpanded] = useState(loadForceExpanded);
  const isSmallScreen = useMediaQuery('(max-width: 1400px)');

  const collapsed = forceExpanded ? false : (userCollapsed || isSmallScreen);

  const currentModule = appModules.find((item) => location.pathname.startsWith(item.basePath));

  function handleLogout() {
    logout();
    navigate('/login', { replace: true });
  }

  function toggleCollapsed() {
    if (collapsed) {
      // Expanding
      setUserCollapsed(false);
      window.localStorage.setItem(SIDEBAR_COLLAPSED_KEY, 'false');
      if (isSmallScreen) {
        setForceExpanded(true);
        window.localStorage.setItem(SIDEBAR_FORCE_EXPANDED_KEY, 'true');
      }
    } else {
      // Collapsing
      setUserCollapsed(true);
      window.localStorage.setItem(SIDEBAR_COLLAPSED_KEY, 'true');
      setForceExpanded(false);
      window.localStorage.removeItem(SIDEBAR_FORCE_EXPANDED_KEY);
    }
  }

  const displayName = user?.userName ?? `User #${user?.userId ?? ''}`;

  return (
    <div className={`admin-shell${collapsed ? ' admin-shell--collapsed' : ''}`}>
      <div className="admin-shell__glow" />
      <div className="admin-shell__toolbar">
        <UserMenu displayName={displayName} onLogout={handleLogout} />
      </div>
      <AppSidebar
        currentModuleKey={currentModule?.key}
        currentPath={location.pathname}
        collapsed={collapsed}
        onToggleCollapse={toggleCollapsed}
      />
      <main className="admin-shell__content">
        <div className="admin-shell__panel">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
```

- [ ] **Step 2.4 — Run to confirm PASS**

```bash
npx vitest run src/app/shell/AppShell.test.tsx
```
Expected: `4 tests passed`

- [ ] **Step 2.5 — Run full test suite to confirm no regressions**

```bash
npx vitest run
```
Expected: all tests pass

- [ ] **Step 2.6 — Commit**

```bash
git add src/app/shell/AppShell.tsx src/app/shell/AppShell.test.tsx src/shared/hooks/useMediaQuery.ts src/shared/hooks/useMediaQuery.test.ts
git commit -m "feat: auto-collapse sidebar on screens ≤1400px with force-expand override"
```

---

## Task 3: `RowActions` shared component

**Files:**
- Create: `src/shared/ui/RowActions.tsx`
- Create: `src/shared/ui/RowActions.test.tsx`

- [ ] **Step 3.1 — Write the failing test**

```tsx
// src/shared/ui/RowActions.test.tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { RowActions } from './RowActions';

const actions = [
  { label: '管理 Prompt 与版本', onClick: vi.fn() },
  { label: '编辑定义', onClick: vi.fn() },
];

describe('RowActions', () => {
  it('renders a trigger button and no menu items initially', () => {
    render(<RowActions actions={actions} />);
    expect(screen.getByRole('button', { name: '更多操作' })).toBeInTheDocument();
    expect(screen.queryByRole('menuitem')).toBeNull();
  });

  it('opens the menu on trigger click', async () => {
    const user = userEvent.setup();
    render(<RowActions actions={actions} />);
    await user.click(screen.getByRole('button', { name: '更多操作' }));
    expect(screen.getByRole('menuitem', { name: '管理 Prompt 与版本' })).toBeInTheDocument();
    expect(screen.getByRole('menuitem', { name: '编辑定义' })).toBeInTheDocument();
  });

  it('calls the action onClick and closes the menu', async () => {
    const user = userEvent.setup();
    render(<RowActions actions={actions} />);
    await user.click(screen.getByRole('button', { name: '更多操作' }));
    await user.click(screen.getByRole('menuitem', { name: '管理 Prompt 与版本' }));
    expect(actions[0].onClick).toHaveBeenCalledOnce();
    expect(screen.queryByRole('menuitem')).toBeNull();
  });

  it('closes the menu when Escape is pressed', async () => {
    const user = userEvent.setup();
    render(<RowActions actions={actions} />);
    await user.click(screen.getByRole('button', { name: '更多操作' }));
    await user.keyboard('{Escape}');
    expect(screen.queryByRole('menuitem')).toBeNull();
  });

  it('closes the menu when clicking outside', async () => {
    const user = userEvent.setup();
    render(
      <div>
        <RowActions actions={actions} />
        <button type="button">outside</button>
      </div>,
    );
    await user.click(screen.getByRole('button', { name: '更多操作' }));
    await user.click(screen.getByRole('button', { name: 'outside' }));
    expect(screen.queryByRole('menuitem')).toBeNull();
  });
});
```

- [ ] **Step 3.2 — Run to confirm FAIL**

```bash
npx vitest run src/shared/ui/RowActions.test.tsx
```
Expected: `Cannot find module './RowActions'`

- [ ] **Step 3.3 — Implement `RowActions`**

```tsx
// src/shared/ui/RowActions.tsx
import { useEffect, useRef, useState } from 'react';
import { MoreHorizontal } from 'lucide-react';

export type RowAction = {
  label: string;
  onClick: () => void;
  variant?: 'default' | 'danger';
};

export function RowActions({ actions }: { actions: RowAction[] }) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function handleOutsideClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    function handleEscape(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false);
    }
    document.addEventListener('mousedown', handleOutsideClick);
    document.addEventListener('keydown', handleEscape);
    return () => {
      document.removeEventListener('mousedown', handleOutsideClick);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [open]);

  return (
    <div ref={containerRef} className="relative inline-block">
      <button
        type="button"
        aria-label="更多操作"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className="flex h-8 w-8 items-center justify-center rounded-lg border border-transparent text-text-secondary transition hover:border-border hover:bg-state-hover hover:text-text"
      >
        <MoreHorizontal size={16} />
      </button>

      {open && (
        <div
          role="menu"
          className="absolute right-0 z-50 mt-1 min-w-[140px] overflow-hidden rounded-xl border border-border bg-surface py-1 shadow-lg"
        >
          {actions.map((action) => (
            <button
              key={action.label}
              role="menuitem"
              type="button"
              onClick={() => {
                setOpen(false);
                action.onClick();
              }}
              className={`w-full px-4 py-2 text-left text-sm transition hover:bg-state-hover ${
                action.variant === 'danger' ? 'text-red-600' : 'text-text'
              }`}
            >
              {action.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3.4 — Run to confirm PASS**

```bash
npx vitest run src/shared/ui/RowActions.test.tsx
```
Expected: `5 tests passed`

- [ ] **Step 3.5 — Commit**

```bash
git add src/shared/ui/RowActions.tsx src/shared/ui/RowActions.test.tsx
git commit -m "feat: add RowActions shared component for table row menus"
```

---

## Task 4: Wire `RowActions` into `AgentsPage`

**Files:**
- Modify: `src/modules/agent-management/resources/agents/AgentsPage.tsx`
- Modify: `src/modules/agent-management/resources/agents/AgentsPage.test.tsx`

- [ ] **Step 4.1 — Update the test first**

Replace the test body of `it('splits row actions ...')` in `AgentsPage.test.tsx`:

```tsx
it('splits row actions between version management and definition editing', async () => {
  const user = userEvent.setup();

  renderWithQueryClient(
    <MemoryRouter>
      <AgentsPage />
    </MemoryRouter>,
  );

  // Open the ⋯ menu for the row
  await user.click(screen.getByRole('button', { name: '更多操作' }));

  // Click "管理 Prompt 与版本" inside the menu
  await user.click(screen.getByRole('menuitem', { name: '管理 Prompt 与版本' }));
  expect(navigateMock).toHaveBeenCalledWith('agent.docs?tab=versions');

  // Open the menu again for "编辑定义"
  await user.click(screen.getByRole('button', { name: '更多操作' }));
  await user.click(screen.getByRole('menuitem', { name: '编辑定义' }));

  // AgentDrawer mock renders "编辑定义" text when open in edit mode
  expect(screen.getByText('编辑定义')).toBeInTheDocument();
});
```

- [ ] **Step 4.2 — Run test to confirm it now FAILS** (buttons still inline)

```bash
npx vitest run src/modules/agent-management/resources/agents/AgentsPage.test.tsx
```
Expected: `Unable to find role="button" name="更多操作"`

- [ ] **Step 4.3 — Update `AgentsPage.tsx` actions column**

Replace the `actions` column definition (the entire `key: 'actions'` object) in `AgentsPage.tsx`:

```tsx
// add to imports at top of file:
// import { RowActions } from '@/shared/ui/RowActions';

{
  key: 'actions',
  header: '操作',
  render: (row) => (
    <RowActions
      actions={[
        {
          label: '管理 Prompt 与版本',
          onClick: () => navigate(`${row.agentKey}?tab=versions`),
        },
        {
          label: '编辑定义',
          onClick: () => setEditingAgentKey(row.agentKey),
        },
      ]}
    />
  ),
},
```

Also add the import at the top of `AgentsPage.tsx`:

```tsx
import { RowActions } from '@/shared/ui/RowActions';
```

And remove the now-unused `Button` import if it's only used in the actions column (keep it if used elsewhere — check `立即创建` empty state button still uses it).

- [ ] **Step 4.4 — Run to confirm PASS**

```bash
npx vitest run src/modules/agent-management/resources/agents/AgentsPage.test.tsx
```
Expected: `1 test passed`

- [ ] **Step 4.5 — Run full test suite**

```bash
npx vitest run
```
Expected: all tests pass

- [ ] **Step 4.6 — Commit**

```bash
git add src/modules/agent-management/resources/agents/AgentsPage.tsx \
        src/modules/agent-management/resources/agents/AgentsPage.test.tsx
git commit -m "feat: replace inline action buttons with RowActions dropdown in AgentsPage"
```

---

## Task 5: Compact `DataTable` row height

**Files:**
- Modify: `src/shared/ui/DataTable.tsx`

No test needed — this is a padding-only visual change. Rely on existing rendering tests and visual inspection.

- [ ] **Step 5.1 — Update padding in `DataTable.tsx`**

In `src/shared/ui/DataTable.tsx`, make two changes:

**`th` className** — change `px-4 py-3` → `px-4 py-2`:
```tsx
// before
className={`px-4 py-3 text-xs font-semibold uppercase tracking-[0.12em] text-text-muted ${column.headerClassName ?? ''}`}

// after
className={`px-4 py-2 text-xs font-semibold uppercase tracking-[0.12em] text-text-muted ${column.headerClassName ?? ''}`}
```

**`td` className** — change `px-4 py-4` → `px-4 py-2.5`:
```tsx
// before
className={`px-4 py-4 text-sm leading-6 text-text-secondary ${column.className ?? ''}`}

// after
className={`px-4 py-2.5 text-sm leading-6 text-text-secondary ${column.className ?? ''}`}
```

- [ ] **Step 5.2 — Run full test suite to confirm no regressions**

```bash
npx vitest run
```
Expected: all tests pass

- [ ] **Step 5.3 — Visual check in browser**

Open `http://127.0.0.1:5173/agent-management` in DevTools, set viewport to **1280 × 720**. Verify:
- No horizontal scrollbar
- ≥ 8 rows visible without scrolling
- `⋯` button appears and opens menu correctly
- Sidebar auto-collapses at 1280px; clicking expand persists across page reload

- [ ] **Step 5.4 — Commit**

```bash
git add src/shared/ui/DataTable.tsx
git commit -m "fix: compact DataTable row height for small-screen density (py-4→py-2.5)"
```

---

## Acceptance Checklist

- [ ] Viewport 1280×720: no horizontal scrollbar on Agent 管理 page
- [ ] Viewport 1280×720: ≥ 8 table rows visible without vertical scroll
- [ ] Sidebar auto-collapses at ≤1400px; force-expand persists on reload
- [ ] Viewport 1920×1080: sidebar defaults to expanded, behaviour unchanged
- [ ] `⋯` opens menu with both actions; each action works correctly
- [ ] All `npx vitest run` tests pass
