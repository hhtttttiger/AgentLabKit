import { useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Badge } from '@/shared/ui/Badge';
import { getCapabilityLabel } from '@/shared/config/catalogOptions';
import { InlineMessage } from '@/shared/ui/InlineMessage';
import { DetailField } from '../../../lib/DetailComponents';
import { useModelDetail } from '../hooks';
import { ModelFeatureSectionDnd } from '../ModelCardFeatureSectionDnd';

export function ModelOverviewTab() {
  const { modelKey } = useParams<{ modelKey: string }>();
  const { t } = useTranslation();
  const detailQuery = useModelDetail(modelKey);

  if (!modelKey) return null;

  if (detailQuery.isError) {
    return <InlineMessage tone="error">{t('modules.modelManagement.models.tabs.loadFailed')}</InlineMessage>;
  }

  if (!detailQuery.data && detailQuery.isLoading) {
    return <div className="text-sm text-text-secondary">{t('modules.modelManagement.models.tabs.loading')}</div>;
  }

  const card = detailQuery.data;
  if (!card) return null;

  const bindings = card.bindings ?? [];
  const instances = card.instances ?? [];
  const features = card.features ?? [];

  return (
    <div className="space-y-6">
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.15fr)_minmax(320px,0.85fr)]">
        {/* Basic info */}
        <div className="rounded-[2px] border border-border bg-surface/80 p-6">
          <h2 className="mb-4 text-sm font-semibold text-text-secondary">{t('modules.modelManagement.models.tabs.overview.basicInfo')}</h2>

          <div className="mb-5 flex flex-wrap items-start justify-between gap-3 rounded-[2px] border border-border-subtle bg-background-subtle/60 px-5 py-4">
            <div className="min-w-0">
              <div className="text-[11px] uppercase tracking-[0.18em] text-text-muted">{t('modules.modelManagement.models.tabs.overview.modelLabel')}</div>
              <div className="mt-2 text-2xl font-semibold tracking-tight text-text">{card.displayName}</div>
              <div className="mt-2 text-sm text-text-secondary">{card.modelName}</div>
            </div>
            <div className="flex flex-wrap gap-2">
              <Badge>{getCapabilityLabel(t, card.type)}</Badge>
              <Badge tone={card.isEnabled ? 'success' : 'warning'}>{card.isEnabled ? t('modules.modelManagement.models.tabs.overview.status.enabled') : t('modules.modelManagement.models.tabs.overview.status.disabled')}</Badge>
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            <DetailField label={t('modules.modelManagement.models.tabs.overview.modelKeyLabel')} value={<span className="font-mono text-[13px]">{card.modelKey}</span>} tone="strong" />
            <DetailField label={t('modules.modelManagement.models.tabs.overview.bindingsCount')} value={t('modules.modelManagement.models.tabs.overview.countUnit', { count: bindings.length })} />
            <DetailField label={t('modules.modelManagement.models.tabs.overview.instancesCount')} value={t('modules.modelManagement.models.tabs.overview.countUnit', { count: instances.length })} />
            <DetailField label={t('modules.modelManagement.models.tabs.overview.featureCount')} value={t('modules.modelManagement.models.tabs.overview.countUnit', { count: features.length })} />
            <DetailField label={t('modules.modelManagement.models.tabs.overview.statusLabel')} value={card.isEnabled ? t('modules.modelManagement.models.tabs.overview.enabled') : t('modules.modelManagement.models.tabs.overview.disabled')} />
            <div className="sm:col-span-2 xl:col-span-3 rounded-[2px] border border-border-subtle bg-background-subtle/70 px-4 py-3">
              <div className="text-[11px] uppercase tracking-[0.16em] text-text-muted">{t('modules.modelManagement.models.tabs.overview.descriptionLabel')}</div>
              <div className="mt-2 text-sm leading-6 text-text-secondary">{card.description ?? t('modules.modelManagement.models.tabs.overview.noDescription')}</div>
            </div>
          </div>
        </div>

        <ModelFeatureSectionDnd modelKey={card.modelKey} features={features} />
      </div>
    </div>
  );
}
