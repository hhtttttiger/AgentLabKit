/**
 * DF-08 regression: Agent Build page survives the cold-mount loading->loaded
 * transition.
 *
 * The page used to call useVersionList only after the loading/error early
 * returns. On a cold mount (direct URL, create-success navigation,
 * Use-Knowledge entry) the loading branch rendered with fewer hooks; the
 * resolved render then added useVersionList's React hooks and crashed with
 * "Rendered more hooks than during the previous render". The route-level
 * ErrorBoundary's Retry button masked it as a transient error.
 *
 * This file keeps '../versions/hooks' REAL (its useQuery adds real React
 * hooks, which is what makes the invariant observable — a bare vi.fn() mock
 * adds none) and stubs only fetch.
 */
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { act, render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { AgentDetailView, AgentVersionSummaryView } from '../../lib/contracts';

const { useAgentMock, useAgentMutationsMock, useAuditListMock } = vi.hoisted(() => ({
  useAgentMock: vi.fn(),
  useAgentMutationsMock: vi.fn(),
  useAuditListMock: vi.fn(),
}));

vi.mock('./hooks', () => ({
  useAgent: useAgentMock,
  useAgentMutations: useAgentMutationsMock,
}));

vi.mock('../audits/hooks', () => ({
  useAuditList: useAuditListMock,
  useAuditDetail: vi.fn(() => ({ isLoading: false, isError: false, data: null })),
}));

vi.mock('../versions/VersionDrawer', () => ({ VersionDrawer: () => null }));
vi.mock('../audits/AuditDetailDrawer', () => ({ AuditDetailDrawer: () => null }));

import { AgentDetailPage } from './AgentDetailPage';

const versionRows: AgentVersionSummaryView[] = [
  {
    versionNumber: 3,
    versionStatus: 'published',
    versionLabel: 'stable',
    changeSummary: 'published version',
    modelKey: 'binding.primary',
    checksum: 'sha256:published',
    rowVersion: 30,
    publishedAtUtc: '2026-04-08T00:00:00Z',
    createdAtUtc: '2026-04-07T00:00:00Z',
  },
];

const agent: AgentDetailView = {
  agentKey: 'agent.docs',
  displayName: '文档助理',
  description: '处理知识文档',
  status: 'published',
  publishedVersionNumber: 3,
  rowVersion: 12,
  createdAtUtc: '2026-04-01T00:00:00Z',
  updatedAtUtc: '2026-04-02T00:00:00Z',
  tags: ['docs'],
  metadata: {},
  publishedVersion: versionRows[0],
};

describe('AgentDetailPage hook ordering (DF-08)', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            success: true,
            msg: 'ok',
            data: { items: versionRows, totalCount: versionRows.length, page: 1, pageSize: 100 },
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        ),
      ),
    );
    useAgentMock.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      error: null,
    });
    useAgentMutationsMock.mockReturnValue({
      publish: { error: null, isPending: false, reset: vi.fn(), mutateAsync: vi.fn() },
      disable: { error: null, isPending: false, reset: vi.fn(), mutateAsync: vi.fn() },
      getMutationMessage: (error: unknown) => String(error),
    });
    useAuditListMock.mockReturnValue({
      data: { items: [], totalCount: 0, page: 1, pageSize: 10 },
      isLoading: false,
      isError: false,
    });
  });

  it('renders after the agent query resolves without a hook-count change', async () => {
    // Fresh element objects of the same shape keep the page component
    // instance alive across renders; an identical element reference would
    // let React bail out and hide the transition.
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const makeUi = () => (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/agents/agent.docs?tab=build']}>
          <Routes>
            <Route path="/agents/:agentKey" element={<AgentDetailPage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    );
    const view = render(makeUi());

    // Resolve the agent query: the next render must not add hooks.
    useAgentMock.mockReturnValue({
      data: agent,
      isLoading: false,
      isError: false,
      error: null,
    });

    await act(async () => {
      view.rerender(makeUi());
    });

    expect(await screen.findAllByText('文档助理')).not.toHaveLength(0);
  });
});
