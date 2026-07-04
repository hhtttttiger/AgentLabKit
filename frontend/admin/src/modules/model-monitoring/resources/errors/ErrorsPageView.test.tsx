import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { switchTestLanguage } from '@/shared/test/setup';
import { ErrorsPageView } from './ErrorsPageView';
import type { ErrorsPageState } from './useErrorsPageState';

// Stub out the error-codes API hook so it falls back to local known labels
vi.mock('./hooks', async () => {
  const actual = await vi.importActual('./hooks');
  return {
    ...actual,
    useDistinctErrorCodes: () => ({ data: undefined, isLoading: false }),
  };
});

function buildState(): ErrorsPageState {
  return {
    filters: {
      modelKey: '',
      errorCode: '',
      fromDate: '',
      toDate: '',
      page: 1,
      pageSize: 10,
    },
    modelOptionsQuery: { data: [], isLoading: false } as unknown as ErrorsPageState['modelOptionsQuery'],
    listQuery: { isFetching: false, isLoading: false, refetch: vi.fn(), data: { totalCount: 1 } } as unknown as ErrorsPageState['listQuery'],
    rows: [
      {
        requestId: 'req-1',
        modelKey: 'gpt-4o',
        displayName: 'GPT-4o',
        instanceKey: 'inst-1',
        capability: 'Text',
        errorCode: 'RateLimited',
        errorMessage: 'Rate limited',
        durationMs: 1234,
        startedAtUtc: '2024-01-02T03:04:05Z',
        completedAtUtc: '2024-01-02T03:04:06Z',
      },
    ],
    expandedRowId: null,
    patchFilters: vi.fn(),
    resetFilters: vi.fn(),
    setPage: vi.fn(),
    toggleExpand: vi.fn(),
  };
}

describe('ErrorsPageView locale subscription', () => {
  it('rerenders locale-sensitive formatter content on language change', async () => {
    const state = buildState();
    const date = new Date('2024-01-02T03:04:05Z');
    const enValue = new Intl.DateTimeFormat('en-US', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    }).format(date);
    const zhValue = new Intl.DateTimeFormat('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    }).format(date);

    await switchTestLanguage('en-US');
    render(<ErrorsPageView state={state} />);

    expect(screen.getByText(enValue)).toBeInTheDocument();

    await act(async () => {
      await switchTestLanguage('zh-CN');
    });

    await waitFor(() => {
      expect(screen.getByText(zhValue)).toBeInTheDocument();
    });
    expect(screen.queryByText(enValue)).not.toBeInTheDocument();
  });

  it('renders translated error code filter options', async () => {
    await switchTestLanguage('en-US');
    render(<ErrorsPageView state={buildState()} />);

    expect(screen.getByRole('option', { name: 'upstream_error — Upstream error' })).toBeInTheDocument();
  });

  it('opens a localized calendar for date filters', async () => {
    const state = buildState();
    state.filters.fromDate = '2024-01-15';
    const user = userEvent.setup();

    await switchTestLanguage('en-US');
    render(<ErrorsPageView state={state} />);

    await user.click(screen.getByLabelText('Start time'));
    expect(screen.getByText('January 2024')).toBeInTheDocument();

    await act(async () => {
      await switchTestLanguage('zh-CN');
    });

    await waitFor(() => {
      expect(screen.getByText('2024年1月')).toBeInTheDocument();
    });
  });
});
