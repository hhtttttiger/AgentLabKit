import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { screen, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { renderWithQueryClient } from '@/shared/test/render';
import type { AgentDetailView, ExecutionAuditView, AgentVersionSummaryView } from '../../lib/contracts';
import { AgentDetailPage } from './AgentDetailPage';

const navigateMock = vi.fn();

const {
  useAgentMock,
  useAgentMutationsMock,
  useVersionListMock,
  useVersionDetailMock,
  useAuditListMock,
} = vi.hoisted(() => ({
  useAgentMock: vi.fn(),
  useAgentMutationsMock: vi.fn(),
  useVersionListMock: vi.fn(),
  useVersionDetailMock: vi.fn(),
  useAuditListMock: vi.fn(),
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
  useAgentMutations: useAgentMutationsMock,
}));

vi.mock('../versions/hooks', () => ({
  useVersionList: useVersionListMock,
  useVersionDetail: useVersionDetailMock,
}));

vi.mock('../audits/hooks', () => ({
  useAuditList: useAuditListMock,
  useAuditDetail: vi.fn(() => ({
    isLoading: false,
    isError: false,
    data: null,
  })),
}));

vi.mock('../versions/VersionDrawer', () => ({
  VersionDrawer: () => null,
}));

vi.mock('../audits/AuditDetailDrawer', () => ({
  AuditDetailDrawer: () => null,
}));

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

const auditRows: ExecutionAuditView[] = [
  {
    id: '1',
    runId: 'run-12345678',
    agentKey: 'agent.docs',
    agentVersion: 3,
    inputSummary: 'Test input',
    outputSummary: 'Done.',
    toolCallsJson: [],
    status: 'success',
    durationMs: 1000,
    tokenUsageJson: {},
    errorMessage: null,
    createdAtUtc: '2026-04-08T00:00:00Z',
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

describe('AgentDetailPage', () => {
  beforeEach(() => {
    navigateMock.mockReset();
    useAgentMock.mockReturnValue({
      data: agent,
      isLoading: false,
      isError: false,
      error: null,
    });
    useAgentMutationsMock.mockReturnValue({
      publish: { error: null, isPending: false, reset: vi.fn(), mutateAsync: vi.fn() },
      disable: { error: null, isPending: false, reset: vi.fn(), mutateAsync: vi.fn() },
      getMutationMessage: (error: unknown) => String(error),
    });
    useVersionListMock.mockReturnValue({
      data: versionRows,
      isLoading: false,
      isError: false,
    });
    useVersionDetailMock.mockReturnValue({
      isSuccess: false,
      data: undefined,
    });
    useAuditListMock.mockReturnValue({
      data: {
        items: auditRows,
        totalCount: auditRows.length,
        page: 1,
        pageSize: 10,
      },
      isLoading: false,
      isError: false,
    });
  });

  it('renders a plain title row with boxed metadata and shared tab work area', () => {
    renderWithQueryClient(
      <MemoryRouter initialEntries={['/agent-management/agents/agent.docs?tab=versions']}>
        <Routes>
          <Route path="/agent-management/agents/:agentKey" element={<AgentDetailPage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getAllByText('文档助理').length).toBeGreaterThan(0);
    expect(screen.getByText('处理知识文档')).toBeInTheDocument();
    expect(screen.getByTestId('agent-detail-top')).toHaveClass('shrink-0');
    expect(screen.getByTestId('agent-detail-title-row')).toHaveClass('flex');
    expect(screen.getByTestId('agent-detail-title-row')).not.toHaveClass('bg-surface');
    // Status badge is now inline with the title, not in the info row
    expect(within(screen.getByTestId('agent-detail-title-row')).getByText('已发布')).toBeInTheDocument();
    // Info row is a unified metadata strip
    expect(screen.getByTestId('agent-detail-info-row')).toHaveClass('mt-5', 'overflow-hidden', 'rounded-[2px]', 'border', 'border-border-subtle', 'bg-background-subtle/40');
    expect(screen.getByRole('button', { name: '返回列表' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '禁用' })).toBeInTheDocument();
    // 创建版本 button is in the top nav when on the versions tab
    expect(screen.getByRole('button', { name: '创建版本' })).toBeInTheDocument();
    expect(within(screen.getByTestId('agent-detail-info-row')).getByText('Agent Key')).toBeInTheDocument();
    expect(within(screen.getByTestId('agent-detail-info-row')).getByText('当前发布版本')).toBeInTheDocument();
    expect(within(screen.getByTestId('agent-detail-info-row')).getByText('创建时间')).toBeInTheDocument();
    expect(screen.queryByTestId('agent-detail-summary-card')).not.toBeInTheDocument();
    expect(screen.getByRole('tab', { name: '版本管理' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: '执行审计' })).toBeInTheDocument();
    expect(screen.getByTestId('agent-detail-workspace')).toBeInTheDocument();
  });
});
