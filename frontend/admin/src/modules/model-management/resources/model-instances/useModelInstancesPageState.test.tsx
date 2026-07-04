import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { LlmModelInstanceView } from '../../lib/contracts';
import type { useModelInstanceMutations } from './hooks';
import { useModelInstancesPageState } from './useModelInstancesPageState';

const {
  useFeatureOptionsMock,
  useModelInstanceListMock,
  useModelInstanceMutationsMock,
} = vi.hoisted(() => ({
  useFeatureOptionsMock: vi.fn(),
  useModelInstanceListMock: vi.fn(),
  useModelInstanceMutationsMock: vi.fn(),
}));

vi.mock('../../options/hooks', () => ({
  useFeatureOptions: useFeatureOptionsMock,
}));

vi.mock('./hooks', () => ({
  useModelInstanceList: useModelInstanceListMock,
  useModelInstanceMutations: useModelInstanceMutationsMock,
}));

describe('useModelInstancesPageState', () => {
  type InstanceMutations = ReturnType<typeof useModelInstanceMutations>;

  const row: LlmModelInstanceView = {
    instanceKey: 'inst-a',
    modelKey: 'card.text',
    type: 'Text',
    modelName: 'gpt-4.1-mini',
    providerDeploymentName: null,
    region: null,
    priority: 1,
    weight: 100,
    defaultTimeoutMs: 30000,
    extraJson: {},
    isEnabled: true,
    isHealthy: true,
  };

  const rowWithApiKey = {
    ...row,
    apiKey: null,
  };

  let capturedQuery: unknown;
  let mutations: InstanceMutations;

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
    } as unknown as InstanceMutations;

    useFeatureOptionsMock.mockReturnValue({ isLoading: false, data: [] });
    useModelInstanceListMock.mockImplementation((query: unknown) => {
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
    useModelInstanceMutationsMock.mockReturnValue(mutations);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('computes list metrics and keeps instance filters in query state', () => {
    const { result } = renderHook(() => useModelInstancesPageState());

    expect(result.current.metrics.enabledCount).toBe(1);
    expect(result.current.metrics.healthyCount).toBe(1);
    expect(result.current.metrics.typeCount).toBe(1);
    expect(capturedQuery).toMatchObject({ page: 1, pageSize: 10 });

    act(() => {
      result.current.patchFilters({
        type: 'Text',
        page: 2,
      });
    });

    expect(capturedQuery).toMatchObject({
      type: 'Text',
      page: 2,
      pageSize: 10,
    });
  });

  it('keeps create and edit submission flows separate', async () => {
    const { result } = renderHook(() => useModelInstancesPageState());

    act(() => {
      result.current.openCreate();
    });

    expect(result.current.drawer.mode).toBe('create');

    await act(async () => {
      await result.current.drawer.onSubmit({ modelKey: 'card.text', model: rowWithApiKey });
    });

    expect(mutations.create.mutateAsync).toHaveBeenCalledWith({
      modelKey: 'card.text',
      model: rowWithApiKey,
    });
    expect(result.current.drawer.open).toBe(false);

    act(() => {
      result.current.openEdit(row);
    });

    expect(result.current.drawer.mode).toBe('edit');
    expect(result.current.drawer.initialValue).toEqual(row);

    await act(async () => {
      await result.current.drawer.onSubmit({ modelKey: 'card.text', model: rowWithApiKey });
    });

    expect(mutations.update.mutateAsync).toHaveBeenCalledWith({
      instanceKey: 'inst-a',
      model: rowWithApiKey,
    });
  });
});
