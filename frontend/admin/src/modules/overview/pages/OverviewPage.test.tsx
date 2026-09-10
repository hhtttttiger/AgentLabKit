import { MemoryRouter } from 'react-router-dom';
import { fireEvent, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { renderWithQueryClient } from '@/shared/test/render';
import { OverviewPage } from './OverviewPage';

const navigateMock = vi.fn();
const { useRunListMock, useAgentListMock } = vi.hoisted(() => ({
  useRunListMock: vi.fn(),
  useAgentListMock: vi.fn(),
}));

vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>();
  return {
    ...actual,
    useNavigate: () => navigateMock,
  };
});

vi.mock('@/modules/runs/hooks', () => ({
  useRunList: useRunListMock,
}));

vi.mock('@/modules/agent-management/resources/agents/hooks', () => ({
  useAgentList: useAgentListMock,
}));

describe('OverviewPage', () => {
  beforeEach(() => {
    navigateMock.mockReset();
    useRunListMock.mockReturnValue({
      data: { items: [], total: 0 },
      isLoading: false,
    });
  });

  it('leads a fresh workspace with a Create Agent first action', () => {
    useAgentListMock.mockReturnValue({
      data: { items: [], totalCount: 0 },
      isLoading: false,
    });

    renderWithQueryClient(
      <MemoryRouter>
        <OverviewPage />
      </MemoryRouter>,
    );

    expect(screen.getByText('创建你的第一个 Agent')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '创建 Agent' }));
    expect(navigateMock).toHaveBeenCalledWith('/agents?create=1');
    // The playground quick action is a dead end without agents; it must not
    // compete with the first action on a fresh workspace.
    expect(screen.queryByRole('button', { name: '测试 Agent' })).not.toBeInTheDocument();
  });

  it('shows quick actions once agents exist', () => {
    useAgentListMock.mockReturnValue({
      data: { items: [{ agentKey: 'agent.docs' }], totalCount: 1 },
      isLoading: false,
    });

    renderWithQueryClient(
      <MemoryRouter>
        <OverviewPage />
      </MemoryRouter>,
    );

    expect(screen.queryByText('创建你的第一个 Agent')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: '测试 Agent' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '创建 Agent' })).toBeInTheDocument();
  });
});
