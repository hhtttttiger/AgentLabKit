import type { TFunction } from 'i18next';
import type { CardCapability, LlmProvider } from '@/modules/model-management/lib/contracts';

export const providerOptions: Array<{ label: string; value: LlmProvider }> = [
  { label: 'OpenAI', value: 'openai' },
  { label: 'Azure OpenAI', value: 'azure_openai' },
];

export const capabilityOptions: Array<{ label: string; value: CardCapability }> = [
  { label: 'Text', value: 'Text' },
  { label: 'Multimodal', value: 'Multimodal' },
  { label: 'Embedding', value: 'Embedding' },
  { label: 'Speech Batch', value: 'SpeechBatch' },
  { label: 'Speech Stream', value: 'SpeechStream' },
  { label: 'Realtime', value: 'Realtime' },
  { label: 'Image', value: 'Image' },
  { label: 'Tool', value: 'Tool' },
];

/** 判断是否文本类模型（后端 seed 用 "chat"，UI 用 'Text'，兼容两者）。 */
export function isTextModel(type: string | null | undefined): boolean {
  return type === 'Text' || type === 'chat';
}

/** 判断是否向量类模型（后端 seed 用 "embedding"，UI 用 'Embedding'，兼容两者）。 */
export function isEmbeddingModel(type: string | null | undefined): boolean {
  return type === 'Embedding' || type === 'embedding';
}

export function getEnabledFilterOptions(t: TFunction<'modelManagement'>) {
  return [
    { label: t('modelManagement:shared.enabledStatusOptions.all'), value: 'all' },
    { label: t('modelManagement:shared.enabledStatusOptions.enabledOnly'), value: 'true' },
    { label: t('modelManagement:shared.enabledStatusOptions.disabledOnly'), value: 'false' },
  ];
}

export function getHealthFilterOptions(t: TFunction<'modelManagement'>) {
  return [
    { label: t('modelManagement:shared.healthStatusOptions.all'), value: 'all' },
    { label: t('modelManagement:shared.healthStatusOptions.healthyOnly'), value: 'true' },
    { label: t('modelManagement:shared.healthStatusOptions.unhealthyOnly'), value: 'false' },
  ];
}

export const valueTypeOptions = [
  { label: 'String', value: 'string' },
  { label: 'Number', value: 'number' },
  { label: 'Integer', value: 'int' },
  { label: 'Boolean', value: 'boolean' },
  { label: 'Enum', value: 'enum' },
];

export function getFilterableFilterOptions(t: TFunction<'modelManagement'>) {
  return [
    { label: t('modelManagement:shared.filterableOptions.all'), value: 'all' },
    { label: t('modelManagement:shared.filterableOptions.filterableOnly'), value: 'true' },
    { label: t('modelManagement:shared.filterableOptions.notFilterableOnly'), value: 'false' },
  ];
}

export function getRoutableFilterOptions(t: TFunction<'modelManagement'>) {
  return [
    { label: t('modelManagement:shared.routableOptions.all'), value: 'all' },
    { label: t('modelManagement:shared.routableOptions.routableOnly'), value: 'true' },
    { label: t('modelManagement:shared.routableOptions.notRoutableOnly'), value: 'false' },
  ];
}

export function getProviderLabel(provider: string | null | undefined) {
  return providerOptions.find((item) => item.value === provider)?.label ?? provider ?? '-';
}

export function getValueTypeLabel(valueType: string | null | undefined) {
  return valueTypeOptions.find((item) => item.value === valueType)?.label ?? valueType ?? '-';
}

/** Map a capability value (e.g. 'SpeechBatch') to a localized, human-readable label. */
export function getCapabilityLabel(t: TFunction<'modelManagement'>, capability: string | null | undefined): string {
  if (!capability) return '-';
  const known = capabilityOptions.find((item) => item.value === capability);
  return t(`preferences.catalog.capabilities.${capability}`, { defaultValue: known?.label ?? capability });
}
