import { fireEvent, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { renderWithQueryClient } from '@/shared/test/render';
import { switchTestLanguage } from '@/shared/test/setup';
import type { useModelFeatureMutations } from './hooks';
import { ModelFeatureSectionDnd } from './ModelCardFeatureSectionDnd';

const {
  useFeatureOptionsMock,
  useModelFeatureMutationsMock,
} = vi.hoisted(() => ({
  useFeatureOptionsMock: vi.fn(),
  useModelFeatureMutationsMock: vi.fn(),
}));

vi.mock('../../options/hooks', () => ({
  useFeatureOptions: useFeatureOptionsMock,
}));

vi.mock('./hooks', () => ({
  useModelFeatureMutations: useModelFeatureMutationsMock,
}));

describe('ModelFeatureSectionDnd', () => {
  type FeatureMutations = ReturnType<typeof useModelFeatureMutations>;

  let mutations: FeatureMutations;

  beforeEach(() => {
    mutations = {
      upsert: {
        mutateAsync: vi.fn().mockResolvedValue(undefined),
        isPending: false,
      },
      remove: {
        mutateAsync: vi.fn().mockResolvedValue(undefined),
        isPending: false,
      },
      getMutationMessage: vi.fn((error: unknown) => `error:${String(error)}`),
    } as unknown as FeatureMutations;

    useFeatureOptionsMock.mockReturnValue({
      isLoading: false,
      data: [
        {
          featureKey: 'function_call',
          displayName: 'Function Call',
          valueType: 'boolean',
          allowedValuesJson: '[]',
          isEnabled: true,
          isFilterable: true,
          isRoutable: false,
        },
        {
          featureKey: 'reasoning_level',
          displayName: 'Reasoning Level',
          valueType: 'string',
          allowedValuesJson: '[]',
          isEnabled: true,
          isFilterable: true,
          isRoutable: true,
        },
      ],
    });
    useModelFeatureMutationsMock.mockReturnValue(mutations);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('allows adding and removing features through explicit action buttons', async () => {
    await switchTestLanguage('en-US');

    renderWithQueryClient(
      <ModelFeatureSectionDnd
        modelKey="card.text"
        features={[
          {
            modelKey: 'card.text',
            featureKey: 'function_call',
            displayName: 'Function Call',
            valueType: 'boolean',
            allowedValuesJson: [],
            isSupported: true,
            valueJson: 'true',
            source: 'manual',
            remark: null,
          },
        ]}
      />,
    );

    fireEvent.click(await screen.findByRole('button', { name: 'Add Reasoning Level' }));

    await waitFor(() => {
      expect(mutations.upsert.mutateAsync).toHaveBeenCalledWith({
        modelKey: 'card.text',
        featureKey: 'reasoning_level',
        model: {
          featureKey: 'reasoning_level',
          isSupported: true,
          valueJson: '',
          source: 'manual',
          remark: null,
        },
      });
    });

    fireEvent.click(screen.getByRole('button', { name: 'Remove Function Call' }));

    await waitFor(() => {
      expect(mutations.remove.mutateAsync).toHaveBeenCalledWith({
        modelKey: 'card.text',
        featureKey: 'function_call',
      });
    });
  });
});
