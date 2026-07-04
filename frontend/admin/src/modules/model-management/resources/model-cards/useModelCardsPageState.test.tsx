import { act, renderHook } from '@testing-library/react';
import type { PropsWithChildren } from 'react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { LlmModelView } from '../../lib/contracts';
import type { useModelMutations } from './hooks';
import { useModelsPageState } from './useModelCardsPageState';

const {
  useFeatureOptionsMock,
  useModelListMock,
  useModelMutationsMock,
} = vi.hoisted(() => ({
  useFeatureOptionsMock: vi.fn(),
  useModelListMock: vi.fn(),
  useModelMutationsMock: vi.fn(),
}));

vi.mock('../../options/hooks', () => ({
  useFeatureOptions: useFeatureOptionsMock,
}));

vi.mock('./hooks', () => ({
  useModelList: useModelListMock,
  useModelMutations: useModelMutationsMock,
}));

describe('useModelsPageState', () => {
  type CardMutations = ReturnType<typeof useModelMutations>;

  const wrapper = ({ children }: PropsWithChildren) => <MemoryRouter>{children}</MemoryRouter>;

  const row: LlmModelView = {
    modelKey: 'card.text',
    type: 'Text',
    modelName: 'gpt-4.1-mini',
    displayName: 'Text Card',
    description: null,
    connectionProfileKey: 'default',
    tagsJson: [],
    routingPolicyJson: {},
    retryPolicyJson: {},
    isEnabled: true,
    instances: [],
    bindings: [],
    features: [],
    instanceCount: 0,
    healthyInstanceCount: 0,
  };

  let capturedQuery: unknown;
  let mutations: CardMutations;

  beforeEach(() => {
    capturedQuery = null;
    mutations = {
      create: {
        mutateAsync: vi.fn().mockResolvedValue(undefined),
        isPending: false,
        error: null,
        reset: vi.fn(),
      },
      update: {
        mutateAsync: vi.fn().mockResolvedValue(undefined),
        isPending: false,
        error: null,
        reset: vi.fn(),
      },
      remove: {
        mutateAsync: vi.fn().mockResolvedValue(undefined),
        isPending: false,
        error: null,
        reset: vi.fn(),
      },
      getMutationMessage: vi.fn((error: unknown) => `error:${String(error)}`),
    } as unknown as CardMutations;

    useFeatureOptionsMock.mockReturnValue({ isLoading: false, data: [] });
    useModelListMock.mockImplementation((query: unknown) => {
      capturedQuery = query;
      return {
        data: {
          items: [row],
          page: 1,
          pageSize: 10,
          totalCount: 1,
        },
        isError: false,
      };
    });
    useModelMutationsMock.mockReturnValue(mutations);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('computes list metrics and resets filters back to the first page', async () => {
    const { result } = renderHook(() => useModelsPageState(), { wrapper });

    expect(result.current.metrics.enabledCount).toBe(1);
    expect(result.current.metrics.withInstances).toBe(0);
    expect(result.current.metrics.withBindings).toBe(0);
    expect(capturedQuery).toMatchObject({ page: 1, pageSize: 10 });

    act(() => {
      result.current.patchFilters({ featureKey: 'function_call', page: 4 });
    });

    expect(capturedQuery).toMatchObject({
      featureKey: 'function_call',
      page: 4,
      pageSize: 10,
    });

    act(() => {
      result.current.resetFilters();
    });

    expect(result.current.filters.featureKey).toBe('');
    expect(result.current.filters.page).toBe(1);
    expect(capturedQuery).toMatchObject({ featureKey: undefined, page: 1, pageSize: 10 });
  });

  it('routes create, edit, and delete flows through dedicated state handlers', async () => {
    const { result } = renderHook(() => useModelsPageState(), { wrapper });

    act(() => {
      result.current.openCreate();
    });

    expect(result.current.drawer.open).toBe(true);
    expect(result.current.drawer.mode).toBe('create');

    await act(async () => {
      await result.current.drawer.onSubmit({
        ...row,
        modelKey: 'card.new',
      }, {});
    });

    expect(mutations.create.mutateAsync).toHaveBeenCalledWith({
      ...row,
      modelKey: 'card.new',
    });
    expect(result.current.drawer.open).toBe(false);

    act(() => {
      result.current.openEdit(row);
    });

    expect(result.current.drawer.mode).toBe('edit');
    expect(result.current.drawer.initialValue).toEqual(row);

    await act(async () => {
      await result.current.drawer.onSubmit(row, {});
    });

    expect(mutations.update.mutateAsync).toHaveBeenCalledWith({
      modelKey: 'card.text',
      model: row,
    });

    act(() => {
      result.current.requestDelete(row);
    });

    expect(result.current.deleteDialog.open).toBe(true);

    await act(async () => {
      await result.current.deleteDialog.onConfirm();
    });

    expect(mutations.remove.mutateAsync).toHaveBeenCalledWith('card.text');
    expect(result.current.deleteDialog.open).toBe(false);
  });
});
