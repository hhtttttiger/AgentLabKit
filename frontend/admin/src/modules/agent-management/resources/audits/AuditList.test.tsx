import { screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { renderWithQueryClient } from '@/shared/test/render';
import type { ExecutionAuditView } from '../../lib/contracts';
import { AuditList } from './AuditList';

const { useAuditListMock } = vi.hoisted(() => ({
  useAuditListMock: vi.fn(),
}));

vi.mock('./hooks', () => ({
  useAuditList: useAuditListMock,
  useAuditDetail: vi.fn(() => ({
    isLoading: false,
    isError: false,
    data: null,
  })),
}));

vi.mock('./AuditDetailDrawer', () => ({
  AuditDetailDrawer: () => null,
}));

const rows: ExecutionAuditView[] = [
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

describe('AuditList', () => {
  beforeEach(() => {
    useAuditListMock.mockReturnValue({
      data: {
        items: rows,
        totalCount: rows.length,
        page: 1,
        pageSize: 10,
      },
      isLoading: false,
      isError: false,
    });
  });

  it('renders audits inside the panel with table and pagination', () => {
    renderWithQueryClient(<AuditList agentKey="agent.docs" />);

    expect(screen.getByText('执行审计')).toBeInTheDocument();
    expect(screen.getByRole('table')).toBeInTheDocument();
  });
});
