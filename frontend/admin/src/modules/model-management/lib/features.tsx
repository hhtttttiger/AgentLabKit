import { useTranslation } from 'react-i18next';
import { Badge } from '@/shared/ui/Badge';
import type {
  LlmFeatureOptionView,
  LlmModelFeatureView,
} from './contracts';

type FeatureValueType = LlmFeatureOptionView['valueType'];

export function parseAllowedValues(allowedValuesJson: unknown[]): string[] {
  return Array.isArray(allowedValuesJson)
    ? allowedValuesJson.filter((item): item is string => typeof item === 'string')
    : [];
}

export function getDefaultFeatureInput(definition: Pick<LlmFeatureOptionView, 'valueType' | 'featureKey'> & { allowedValuesJson?: unknown[] }) {
  if (definition.valueType === 'boolean') {
    return 'true';
  }

  if (definition.valueType === 'enum') {
    return parseAllowedValues(definition.allowedValuesJson ?? [])[0] ?? '';
  }

  if (definition.valueType === 'int' || definition.valueType === 'number') {
    return '0';
  }

  return definition.featureKey;
}

export function toFeatureValueInput(valueType: FeatureValueType, valueJson: unknown, allowedValuesJson: unknown[] = []) {
  if (valueJson === null || valueJson === undefined) {
    return getDefaultFeatureInput({ featureKey: '', valueType, allowedValuesJson });
  }

  if (valueType === 'string' || valueType === 'enum') {
    return typeof valueJson === 'string' ? valueJson : '';
  }

  if (valueType === 'boolean') {
    return valueJson === false ? 'false' : 'true';
  }

  if (valueType === 'int' || valueType === 'number') {
    return typeof valueJson === 'number' ? String(valueJson) : '0';
  }

  return getDefaultFeatureInput({ featureKey: '', valueType, allowedValuesJson });
}

export function validateFeatureValueInput(
  definition: Pick<LlmFeatureOptionView, 'valueType'> & { allowedValuesJson?: unknown[] },
  valueInput: string,
) {
  if (definition.valueType === 'boolean') {
    return valueInput === 'true' || valueInput === 'false' ? null : 'modules.modelManagement.featureValidation.booleanRequired';
  }

  if (definition.valueType === 'int') {
    return /^-?\d+$/.test(valueInput.trim()) ? null : 'modules.modelManagement.featureValidation.integerRequired';
  }

  if (definition.valueType === 'number') {
    return Number.isFinite(Number(valueInput.trim())) ? null : 'modules.modelManagement.featureValidation.numberRequired';
  }

  if (definition.valueType === 'enum') {
    const allowed = parseAllowedValues(definition.allowedValuesJson ?? []);
    return allowed.length === 0 || allowed.includes(valueInput) ? null : 'modules.modelManagement.featureValidation.enumRequired';
  }

  return null;
}

export function toFeatureValueJson(
  definition: Pick<LlmFeatureOptionView, 'valueType'> & { allowedValuesJson?: unknown[] },
  valueInput: string,
) {
  const validationError = validateFeatureValueInput(definition, valueInput);
  if (validationError) {
    throw new Error(validationError);
  }

  if (definition.valueType === 'boolean') {
    return valueInput === 'false' ? false : true;
  }

  if (definition.valueType === 'int' || definition.valueType === 'number') {
    return Number(valueInput.trim());
  }

  return valueInput;
}

export function formatFeatureValue(valueJson: unknown) {
  if (valueJson === null || valueJson === undefined) {
    return null;
  }

  if (typeof valueJson === 'string' || typeof valueJson === 'number' || typeof valueJson === 'boolean') {
    return String(valueJson);
  }

  return JSON.stringify(valueJson);
}

export function CardFeatureBadges({
  features,
  emptyLabel,
  limit = 3,
}: {
  features: LlmModelFeatureView[];
  emptyLabel?: string;
  limit?: number;
}) {
  const { t } = useTranslation();
  const resolvedEmptyLabel = emptyLabel ?? t('modules.modelManagement.models.featureSection.noFeatures');
  if (features.length === 0) {
    return <span className="text-xs text-text-muted">{resolvedEmptyLabel}</span>;
  }

  const visibleItems = features.slice(0, limit);
  const remaining = features.length - visibleItems.length;

  return (
    <div className="flex flex-wrap gap-2">
      {visibleItems.map((feature) => {
        const valueLabel = formatFeatureValue(feature.valueJson);
        return (
          <Badge key={feature.featureKey} tone={feature.isSupported ? 'success' : 'warning'}>
            {feature.displayName}
            {valueLabel ? ` · ${valueLabel}` : ''}
          </Badge>
        );
      })}
      {remaining > 0 ? <Badge tone="neutral">+{remaining}</Badge> : null}
    </div>
  );
}
