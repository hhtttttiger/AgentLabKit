import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { renderWithQueryClient } from '@/shared/test/render';
import type { AgentDetailView, ExecutionAuditView, AgentVersionSummaryView, VersionDetailView } from '../../lib/contracts';
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

const draftRow: AgentVersionSummaryView = {
  ...versionRows[0],
  versionNumber: 4,
  versionStatus: 'draft',
  versionLabel: 'next',
  publishedAtUtc: null,
  createdAtUtc: '2026-04-09T00:00:00Z',
};

const publishedDetail: VersionDetailView = {
  ...versionRows[0],
  systemPromptTemplate: 'You are a documentation assistant.',
  defaultLocale: 'en-US',
  runtimeOptions: {},
  handoffPolicy: {},
  responsePolicy: {},
  guardrailsPolicy: {},
  toolBindings: [],
  knowledgeBaseBindings: [],
  mcpBindings: [],
  skillBindings: [],
};

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
      data: { items: versionRows, totalCount: versionRows.length, page: 1, pageSize: 100 },
      isLoading: false,
      isError: false,
    });
    useVersionDetailMock.mockReturnValue({
      isSuccess: true,
      data: publishedDetail,
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

  const renderBuild = () => {
    renderWithQueryClient(
      <MemoryRouter initialEntries={['/agent-management/agents/agent.docs?tab=build']}>
        <Routes>
          <Route path="/agent-management/agents/:agentKey" element={<AgentDetailPage />} />
        </Routes>
      </MemoryRouter>,
    );
  };

  it('hides Test when the agent only has a draft', () => {
    useAgentMock.mockReturnValue({
      data: { ...agent, status: 'draft', publishedVersionNumber: null, publishedVersion: null },
      isLoading: false,
      isError: false,
      error: null,
    });
    useVersionListMock.mockReturnValue({
      data: { items: [draftRow], totalCount: 1, page: 1, pageSize: 100 },
      isLoading: false,
      isError: false,
    });

    renderBuild();

    expect(screen.getByRole('button', { name: '发布草稿' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /^测试$/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /^测试已发布版本$/ })).not.toBeInTheDocument();
  });

  it('shows Test and navigates with the agent context for a published-only agent', () => {
    renderBuild();

    const testButton = screen.getAllByRole('button', { name: /^测试$/ })[0];
    fireEvent.click(testButton);

    expect(navigateMock).toHaveBeenCalledWith('/playground?agent=agent.docs');
    expect(screen.queryByRole('button', { name: /^测试已发布版本$/ })).not.toBeInTheDocument();
  });

  it('labels the CTA Test Published when a draft is shown over a published version', () => {
    useVersionListMock.mockReturnValue({
      data: { items: [versionRows[0], draftRow], totalCount: 2, page: 1, pageSize: 100 },
      isLoading: false,
      isError: false,
    });

    renderBuild();

    const testButtons = screen.getAllByRole('button', { name: /^测试已发布版本$/ });
    expect(testButtons).toHaveLength(2);
    expect(screen.getByText('草稿变更尚未发布。测试将使用已发布版本。')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /^测试$/ })).not.toBeInTheDocument();

    fireEvent.click(testButtons[0]);
    expect(navigateMock).toHaveBeenCalledWith('/playground?agent=agent.docs');
  });

  it('keeps the publish success CTA and clears it when leaving Build', async () => {
    useVersionListMock.mockReturnValue({
      data: { items: [versionRows[0], draftRow], totalCount: 2, page: 1, pageSize: 100 },
      isLoading: false,
      isError: false,
    });

    renderBuild();
    fireEvent.click(screen.getByRole('button', { name: '发布草稿' }));
    fireEvent.click(screen.getByRole('button', { name: '确认发布' }));

    await waitFor(() => expect(screen.getByText('发布成功。')).toBeInTheDocument());
    expect(screen.getByRole('button', { name: '在 Playground 中测试' })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('tab', { name: '版本管理' }));
    fireEvent.click(screen.getByRole('tab', { name: '构建' }));
    expect(screen.queryByText('发布成功。')).not.toBeInTheDocument();
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
