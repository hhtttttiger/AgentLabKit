import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { renderWithQueryClient } from '@/shared/test/render';
import type { AgentVersionSummaryView, VersionDetailView } from '../../lib/contracts';
import { VersionList } from './VersionList';

const { useVersionListMock, useVersionDetailMock } = vi.hoisted(() => ({
  useVersionListMock: vi.fn(),
  useVersionDetailMock: vi.fn(),
}));

vi.mock('./hooks', () => ({
  useVersionList: useVersionListMock,
  useVersionDetail: useVersionDetailMock,
}));

vi.mock('./VersionDrawer', () => ({
  VersionDrawer: ({
    open,
    editVersion,
  }: {
    open: boolean;
    editVersion?: VersionDetailView | null;
  }) => (open ? <div>{editVersion ? `编辑版本 v${editVersion.versionNumber}` : '创建版本'}</div> : null),
}));

const rows: AgentVersionSummaryView[] = [
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
  {
    versionNumber: 2,
    versionStatus: 'draft',
    versionLabel: 'draft',
    changeSummary: 'draft version',
    modelKey: 'binding.primary',
    checksum: null,
    rowVersion: 20,
    publishedAtUtc: null,
    createdAtUtc: '2026-04-06T00:00:00Z',
  },
  {
    versionNumber: 1,
    versionStatus: 'archived',
    versionLabel: 'old',
    changeSummary: 'archived version',
    modelKey: 'binding.primary',
    checksum: 'sha256:archived',
    rowVersion: 10,
    publishedAtUtc: '2026-04-05T00:00:00Z',
    createdAtUtc: '2026-04-04T00:00:00Z',
  },
];

describe('VersionList', () => {
  beforeEach(() => {
    useVersionListMock.mockReturnValue({
      data: { items: rows, totalCount: rows.length },
      isLoading: false,
      isError: false,
    });
    useVersionDetailMock.mockImplementation((_: string, versionNumber: number | null) => ({
      isSuccess: versionNumber === 3,
      data: versionNumber === 3
        ? {
            ...rows[0],
            systemPromptTemplate: 'Published prompt',
            defaultLocale: 'zh-CN',
            runtimeOptions: {},
            handoffPolicy: {},
            responsePolicy: {},
            guardrailsPolicy: {},
            toolBindings: [],
          }
        : undefined,
    }));
  });

  it('shows state-specific actions for draft and published versions only', async () => {
    const user = userEvent.setup();

    renderWithQueryClient(<VersionList agentKey="agent.docs" onPublish={vi.fn()} />);

    const menuButtons = screen.getAllByRole('button', { name: '更多操作' });
    expect(menuButtons).toHaveLength(2); // published + draft; archived has none

    // Published row: 查看 + 创建草稿
    await user.click(menuButtons[0]);
    expect(screen.getByRole('menuitem', { name: '查看' })).toBeInTheDocument();
    expect(screen.getByRole('menuitem', { name: '创建草稿' })).toBeInTheDocument();

    await user.click(screen.getByRole('menuitem', { name: '查看' }));
    expect(screen.getByText('编辑版本 v3')).toBeInTheDocument();

    // Draft row: 编辑草稿 + 发布
    await user.click(menuButtons[1]);
    expect(screen.getByRole('menuitem', { name: '编辑草稿' })).toBeInTheDocument();
    expect(screen.getByRole('menuitem', { name: '发布' })).toBeInTheDocument();
  });

  it('keeps published rows view-only while still allowing draft creation', async () => {
    const user = userEvent.setup();

    renderWithQueryClient(<VersionList agentKey="agent.docs" onPublish={vi.fn()} />);

    await user.click(screen.getAllByRole('button', { name: '更多操作' })[0]);
    expect(screen.getByRole('menuitem', { name: '查看' })).toBeInTheDocument();
    expect(screen.getByRole('menuitem', { name: '创建草稿' })).toBeInTheDocument();
    expect(screen.queryByRole('menuitem', { name: '编辑草稿' })).not.toBeInTheDocument();
  });

  it('renders versions inside the panel with info message', () => {
    renderWithQueryClient(<VersionList agentKey="agent.docs" onPublish={vi.fn()} />);

    expect(screen.getByText('已发布版本只读。若要修改 Prompt、模型或运行策略，请基于某个版本创建草稿后再发布。')).toBeInTheDocument();
  });
});
