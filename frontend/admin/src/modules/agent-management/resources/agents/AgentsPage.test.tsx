import { MemoryRouter } from 'react-router-dom';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { renderWithQueryClient } from '@/shared/test/render';
import type { AgentSummaryView } from '../../lib/contracts';
import { AgentsPage } from './AgentsPage';

const navigateMock = vi.fn();

const { useAgentMock, useAgentListMock, useAgentMutationsMock } = vi.hoisted(() => ({
  useAgentMock: vi.fn(),
  useAgentListMock: vi.fn(),
  useAgentMutationsMock: vi.fn(),
}));

vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>();
  return {
    ...actual,
    useNavigate: () => navigateMock,
  };
});

vi.mock('./hooks', () => ({
  useAgent: useAgentMock,
  useAgentList: useAgentListMock,
  useAgentMutations: useAgentMutationsMock,
}));

vi.mock('./AgentDrawer', () => ({
  AgentDrawer: ({
    open,
    mode,
  }: {
    open: boolean;
    mode: 'create' | 'edit';
  }) => (open ? <div>{mode === 'edit' ? '编辑定义' : '新建 Agent'}</div> : null),
}));

const rows: AgentSummaryView[] = [
  {
    agentKey: 'agent.docs',
    displayName: '文档助理',
    description: '处理知识文档',
    status: 'published',
    publishedVersionNumber: 3,
    rowVersion: 12,
    createdAtUtc: '2026-04-01T00:00:00Z',
    updatedAtUtc: '2026-04-02T00:00:00Z',
  },
];

describe('AgentsPage', () => {
  beforeEach(() => {
    navigateMock.mockReset();
    useAgentListMock.mockReturnValue({
      data: {
        items: rows,
        totalCount: rows.length,
        page: 1,
        pageSize: 20,
      },
      isLoading: false,
      isError: false,
      isFetching: false,
      refetch: vi.fn(),
    });
    useAgentMock.mockReturnValue({
      data: {
        ...rows[0],
        tags: ['docs'],
        metadata: {},
        publishedVersion: null,
      },
      isLoading: false,
      isError: false,
    });
    useAgentMutationsMock.mockReturnValue({
      create: { isPending: false, error: null, reset: vi.fn() },
      update: { isPending: false, error: null, reset: vi.fn() },
      publish: { error: null, reset: vi.fn() },
      disable: { error: null, reset: vi.fn() },
      getMutationMessage: (error: unknown) => String(error),
    });
  });

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
});
