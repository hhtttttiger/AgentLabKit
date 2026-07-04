import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { switchTestLanguage } from '@/shared/test/setup';
import { UsagePageView } from './UsagePageView';
import type { UsagePageState } from './useUsagePageState';

function buildState(): UsagePageState {
  return {
    filters: {
      modelKey: '',
      fromDate: '',
      toDate: '',
      page: 1,
      pageSize: 10,
    },
    modelOptionsQuery: { data: [], isLoading: false } as unknown as UsagePageState['modelOptionsQuery'],
    rows: [
      {
        modelKey: 'gpt-4o',
        displayName: 'GPT-4o',
        totalRequests: 34,
        totalInputTokens: 20,
        totalOutputTokens: 30,
        averageLatencyMs: 1234,
        errorCount: 3,
        errorRate: 0.03,
      },
    ],
    overviewQuery: { isLoading: false, isFetching: false, refetch: vi.fn(), data: null } as unknown as UsagePageState['overviewQuery'],
    overview: {
      totalRequests: 12,
      totalTokens: 1_234_000,
      averageLatencyMs: 1234,
      totalErrors: 3,
      modelSummaries: [],
    },
    detail: {
      open: false,
      modelKey: '',
      filters: { fromDate: '', toDate: '', page: 1, pageSize: 10 },
      query: { isLoading: false, isFetching: false, data: { totalCount: 0 } } as unknown as UsagePageState['detail']['query'],
      rows: [],
      patchFilters: vi.fn(),
      setPage: vi.fn(),
      onClose: vi.fn(),
    },
    patchFilters: vi.fn(),
    resetFilters: vi.fn(),
    setPage: vi.fn(),
    openDetail: vi.fn(),
  };
}

describe('UsagePageView locale subscription', () => {
  it('does not render the error rate column in the usage table', async () => {
    const state = buildState();

    await switchTestLanguage('zh-CN');
    render(<UsagePageView state={state} />);

    expect(screen.getByRole('columnheader', { name: '模型名称' })).toBeInTheDocument();
    expect(screen.queryByRole('columnheader', { name: '错误率' })).not.toBeInTheDocument();
  });

  it('rerenders locale-sensitive formatter content on language change', async () => {
    const state = buildState();
    const enValue = new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 }).format(1_234_000);
    const zhValue = new Intl.NumberFormat('zh-CN', { notation: 'compact', maximumFractionDigits: 1 }).format(1_234_000);

    await switchTestLanguage('en-US');
    render(<UsagePageView state={state} />);

    expect(screen.getByText(enValue)).toBeInTheDocument();

    await act(async () => {
      await switchTestLanguage('zh-CN');
    });

    await waitFor(() => {
      expect(screen.getByText(zhValue)).toBeInTheDocument();
    });
    expect(screen.queryByText(enValue)).not.toBeInTheDocument();
  });

  it('opens a localized calendar for date filters', async () => {
    const state = buildState();
    state.filters.fromDate = '2024-01-15';
    state.detail.filters.fromDate = '2024-01-15';
    const user = userEvent.setup();

    await switchTestLanguage('en-US');
    render(<UsagePageView state={state} />);

    await user.click(screen.getByLabelText('Start time'));
    expect(screen.getByText('January 2024')).toBeInTheDocument();

    await act(async () => {
      await switchTestLanguage('zh-CN');
    });

    await waitFor(() => {
      expect(screen.getByText('2024年1月')).toBeInTheDocument();
    });
  });

  it('keeps emitting ISO dates when a calendar day is selected', async () => {
    const state = buildState();
    state.filters.fromDate = '2024-01-15';
    const user = userEvent.setup();
    const targetDateLabel = new Intl.DateTimeFormat('en-US', {
      dateStyle: 'full',
      timeZone: 'UTC',
    }).format(new Date(Date.UTC(2024, 0, 20)));

    await switchTestLanguage('en-US');
    render(<UsagePageView state={state} />);

    await user.click(screen.getByLabelText('Start time'));
    await user.click(screen.getByRole('button', { name: targetDateLabel }));

    expect(state.patchFilters).toHaveBeenCalledWith({ fromDate: '2024-01-20', page: 1 });
  });
});
