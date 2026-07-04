import { useEffect, useMemo, useState } from 'react';
import type { LlmFeatureOptionView, LlmModelFeatureView } from '../lib/contracts';
import { toFeatureValueInput } from '../lib/features';
import { useFeatureOptions } from '../options/hooks';
import { useModelFeatureMutations } from '../resources/model-cards/hooks';

/** Shared draft type for both feature editor variants. */
export type FeatureEditorDraft = {
  isSupported: boolean;
  valueInput: string;
  source: string;
  remark: string;
  hasExisting: boolean;
};

/** A merged editable feature combining definition metadata with the current model-feature state. */
export type EditableFeature = {
  featureKey: string;
  displayName: string;
  valueType: string;
  isEnabled: boolean;
  isFilterable: boolean;
  isRoutable: boolean;
  allowedValuesJson: unknown[];
};

const EMPTY_FEATURE_DEFINITIONS: LlmFeatureOptionView[] = [];

/** Build a draft editor state from a feature definition and an optional current value. */
export function buildFeatureDraft(
  definition: Pick<LlmFeatureOptionView, 'featureKey' | 'valueType'> & { allowedValuesJson?: unknown[] },
  current?: LlmModelFeatureView,
): FeatureEditorDraft {
  return {
    isSupported: current?.isSupported ?? true,
    valueInput: toFeatureValueInput(
      definition.valueType,
      current?.valueJson ?? null,
      current?.allowedValuesJson ?? definition.allowedValuesJson ?? [],
    ),
    source: current?.source ?? 'manual',
    remark: current?.remark ?? '',
    hasExisting: Boolean(current),
  };
}

/** Derive the merged editable-feature list from definitions + current model features. */
export function deriveEditableFeatures(
  featureDefinitions: LlmFeatureOptionView[],
  features: LlmModelFeatureView[],
): EditableFeature[] {
  const currentFeatures = new Map(features.map((item) => [item.featureKey, item]));
  const keys = new Set<string>([
    ...featureDefinitions.map((item) => item.featureKey),
    ...currentFeatures.keys(),
  ]);

  return Array.from(keys)
    .map((featureKey) => {
      const definition = featureDefinitions.find((item) => item.featureKey === featureKey);
      const current = currentFeatures.get(featureKey);
      return {
        featureKey,
        displayName: definition?.displayName ?? current?.displayName ?? featureKey,
        valueType: definition?.valueType ?? current?.valueType ?? 'string',
        isEnabled: definition?.isEnabled ?? true,
        isFilterable: definition?.isFilterable ?? false,
        isRoutable: definition?.isRoutable ?? false,
        allowedValuesJson: current?.allowedValuesJson ?? definition?.allowedValuesJson ?? [],
      };
    })
    .sort((left, right) => left.displayName.localeCompare(right.displayName));
}

/**
 * Shared hook for managing feature editor drafts.
 *
 * Returns the core state and helpers that both ModelCardFeatureSection
 * (inline editing) and ModelCardFeatureSectionDnd (drag-and-drop) need.
 */
export function useFeatureEditorDrafts(
  _modelKey: string,
  features: LlmModelFeatureView[],
) {
  const featureDefinitionsQuery = useFeatureOptions(true);
  const featureMutations = useModelFeatureMutations();
  const [featureDrafts, setFeatureDrafts] = useState<Record<string, FeatureEditorDraft>>({});
  const [featureActionError, setFeatureActionError] = useState<string | null>(null);
  const [activeFeatureKey, setActiveFeatureKey] = useState<string | null>(null);

  const featureDefinitions: LlmFeatureOptionView[] = Array.isArray(featureDefinitionsQuery.data)
    ? featureDefinitionsQuery.data
    : EMPTY_FEATURE_DEFINITIONS;

  const editableFeatures = useMemo(
    () => deriveEditableFeatures(featureDefinitions, features),
    [featureDefinitions, features],
  );

  // Rebuild drafts whenever the editable feature list or current features change
  useEffect(() => {
    const currentFeatureMap = new Map(features.map((item) => [item.featureKey, item]));
    const nextDrafts: Record<string, FeatureEditorDraft> = {};

    for (const feature of editableFeatures) {
      nextDrafts[feature.featureKey] = buildFeatureDraft(feature, currentFeatureMap.get(feature.featureKey));
    }

    setFeatureDrafts(nextDrafts);
  }, [editableFeatures, features]);

  const updateFeatureDraft = (featureKey: string, updater: (current: FeatureEditorDraft) => FeatureEditorDraft) => {
    setFeatureDrafts((current) => ({
      ...current,
      [featureKey]: updater(current[featureKey]),
    }));
  };

  const getFeature = (featureKey: string) =>
    editableFeatures.find((item) => item.featureKey === featureKey);

  return {
    featureDefinitionsQuery,
    featureDefinitions,
    featureMutations,
    editableFeatures,
    featureDrafts,
    updateFeatureDraft,
    getFeature,
    featureActionError,
    setFeatureActionError,
    activeFeatureKey,
    setActiveFeatureKey,
  };
}
