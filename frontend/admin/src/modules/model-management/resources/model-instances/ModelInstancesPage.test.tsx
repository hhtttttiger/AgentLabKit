import { screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { renderWithQueryClient } from '@/shared/test/render';
import { switchTestLanguage } from '@/shared/test/setup';
import { ModelInstancesPage } from './ModelInstancesPage';

const { useModelInstancesPageStateMock } = vi.hoisted(() => ({
  useModelInstancesPageStateMock: vi.fn(),
}));

vi.mock('./useModelInstancesPageState', () => ({
  useModelInstancesPageState: useModelInstancesPageStateMock,
}));

describe('ModelInstancesPage', () => {
  it('renders translated filters and actions', async () => {
    await switchTestLanguage('en-US');

    useModelInstancesPageStateMock.mockReturnValue({
      filters: {
        modelKey: '',
        featureKey: '',
        featureIsSupported: 'all',
        featureValueJson: '',
        type: '',
        isEnabled: 'all',
        isHealthy: 'all',
        page: 1,
        pageSize: 10,
      },
      featureOptionsQuery: { isLoading: false, data: [] },
      listQuery: {
        data: { items: [], page: 1, pageSize: 10, totalCount: 0 },
        isFetching: false,
        isError: false,
        isLoading: false,
        refetch: vi.fn(),
      },
      rows: [],
      metrics: {
        enabledCount: 0,
        healthyCount: 0,
        typeCount: 0,
      },
      drawer: {
        open: false,
        mode: 'create',
        initialValue: null,
        loading: false,
        error: null,
        onClose: vi.fn(),
        onSubmit: vi.fn(),
      },
      deleteDialog: {
        open: false,
        loading: false,
        description: '',
        onClose: vi.fn(),
        onConfirm: vi.fn(),
      },
      patchFilters: vi.fn(),
      resetFilters: vi.fn(),
      setPage: vi.fn(),
      openCreate: vi.fn(),
      openEdit: vi.fn(),
      requestDelete: vi.fn(),
    });

    renderWithQueryClient(<ModelInstancesPage />);

    expect(screen.getByRole('button', { name: 'New instance' })).toBeInTheDocument();
    expect(screen.getByLabelText('Model')).toBeInTheDocument();
    expect(screen.getByLabelText('Health')).toBeInTheDocument();
    expect(screen.getByText('No instances')).toBeInTheDocument();
  });

  it('renders localized enabled-status options', async () => {
    await switchTestLanguage('en-US');

    useModelInstancesPageStateMock.mockReturnValue({
      filters: {
        modelKey: '',
        featureKey: '',
        featureIsSupported: 'all',
        featureValueJson: '',
        type: '',
        isEnabled: 'all',
        isHealthy: 'all',
        page: 1,
        pageSize: 10,
      },
      featureOptionsQuery: { isLoading: false, data: [] },
      listQuery: {
        data: { items: [], page: 1, pageSize: 10, totalCount: 0 },
        isFetching: false,
        isError: false,
        isLoading: false,
        refetch: vi.fn(),
      },
      rows: [],
      metrics: {
        enabledCount: 0,
        healthyCount: 0,
        typeCount: 0,
      },
      drawer: {
        open: false,
        mode: 'create',
        initialValue: null,
        loading: false,
        error: null,
        onClose: vi.fn(),
        onSubmit: vi.fn(),
      },
      deleteDialog: {
        open: false,
        loading: false,
        description: '',
        onClose: vi.fn(),
        onConfirm: vi.fn(),
      },
      patchFilters: vi.fn(),
      resetFilters: vi.fn(),
      setPage: vi.fn(),
      openCreate: vi.fn(),
      openEdit: vi.fn(),
      requestDelete: vi.fn(),
    });

    renderWithQueryClient(<ModelInstancesPage />);

    expect(screen.getByRole('option', { name: 'All statuses' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Enabled only' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Disabled only' })).toBeInTheDocument();
  });
});
