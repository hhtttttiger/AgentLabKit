import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, PlusCircle } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Badge } from '@/shared/ui/Badge';
import { Button } from '@/shared/ui/Button';
import { Card } from '@/shared/ui/Card';
import { EmptyState } from '@/shared/ui/EmptyState';
import { InlineMessage } from '@/shared/ui/InlineMessage';
import { PageFrame } from '@/shared/ui/PageFrame';
import { getCapabilityLabel } from '@/shared/config/catalogOptions';
import type { LlmModelInstanceView } from '../../lib/contracts';
import { DetailField, InstanceStat } from '../../lib/DetailComponents';
import { useModelDetail } from './hooks';
import { ModelFeatureSectionDnd } from './ModelCardFeatureSectionDnd';
import { ModelInstanceDrawer } from '../model-instances/ModelInstanceDrawer';
import { ModelBindingDrawer } from '../model-bindings/ModelBindingDrawer';
import { useModelInstanceMutations } from '../model-instances/hooks';
import { useModelBindingMutations } from '../model-bindings/hooks';

export function ModelDetailPage() {
  const { modelKey } = useParams();
  const navigate = useNavigate();
  const { t } = useTranslation(['common', 'modelManagement']);
  const detailQuery = useModelDetail(modelKey);
  const instanceMutations = useModelInstanceMutations();
  const bindingMutations = useModelBindingMutations();
  const [instanceOpen, setInstanceOpen] = useState(false);
  const [editingInstance, setEditingInstance] = useState<LlmModelInstanceView | null>(null);
  const [bindingOpen, setBindingOpen] = useState(false);

  if (!modelKey) {
    return null;
  }

  const model = detailQuery.data;
  const instances = model?.instances ?? [];
  const bindings = model?.bindings ?? [];
  const features = model?.features ?? [];
  const healthyInstanceCount = instances.filter((instance) => instance.isHealthy).length;
  const enabledInstanceCount = instances.filter((instance) => instance.isEnabled).length;
  const regionCount = model
    ? new Set(instances.map((instance) => instance.region ?? t('modelManagement:models.detail.instances.defaultRegion'))).size
    : 0;

  return (
    <PageFrame
      title={model?.displayName ?? t('modelManagement:models.detail.loading')}
      actions={
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => navigate('/model-management/models')}>
            <ArrowLeft size={16} />
            {t('modelManagement:models.detail.actions.backToList')}
          </Button>
          <Button onClick={() => setInstanceOpen(true)}>
            <PlusCircle size={16} />
            {t('modelManagement:models.detail.actions.addInstance')}
          </Button>
          <Button variant="secondary" onClick={() => setBindingOpen(true)}>
            <PlusCircle size={16} />
            {t('modelManagement:models.detail.actions.addBinding')}
          </Button>
        </div>
      }
    >
      {!model && detailQuery.isLoading ? <div className="text-sm text-text-secondary">{t('modelManagement:models.detail.loading')}</div> : null}
      {detailQuery.isError ? <InlineMessage tone="error">{t('modelManagement:models.detail.loadFailed')}</InlineMessage> : null}

      {model ? (
        <div className="space-y-6">
          <div className="grid gap-6 xl:grid-cols-[minmax(0,1.15fr)_minmax(320px,0.85fr)]">
            <Card title={t('modelManagement:models.detail.basicInfo.cardTitle')} description={t('modelManagement:models.detail.basicInfo.cardDescription')}>
              <div className="space-y-5">
                <div className="flex flex-wrap items-start justify-between gap-3 rounded-[2px] border border-border-subtle bg-background-subtle/60 px-5 py-4">
                  <div className="min-w-0">
                    <div className="text-[11px] uppercase tracking-[0.18em] text-text-muted">{t('modelManagement:models.detail.basicInfo.modelLabel')}</div>
                    <div className="mt-2 text-2xl font-semibold tracking-tight text-text">{model.displayName}</div>
                    <div className="mt-2 text-sm text-text-secondary">{model.modelName}</div>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Badge>{getCapabilityLabel(t, model.type)}</Badge>
                    <Badge tone={model.isEnabled ? 'success' : 'warning'}>{model.isEnabled ? t('modelManagement:models.detail.instances.status.enabled') : t('modelManagement:models.detail.instances.status.disabled')}</Badge>
                  </div>
                </div>

                <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                  <DetailField label={t('modelManagement:models.detail.basicInfo.modelKeyLabel')} value={<span className="font-mono text-[13px]">{model.modelKey}</span>} tone="strong" />
                  <DetailField label={t('modelManagement:models.detail.basicInfo.connectionProfileLabel')} value={model.connectionProfileKey} />
                  <DetailField label={t('modelManagement:models.detail.basicInfo.bindingsCount')} value={t('modelManagement:models.detail.basicInfo.countUnit', { count: bindings.length })} />
                  <DetailField label={t('modelManagement:models.detail.basicInfo.instancesCount')} value={t('modelManagement:models.detail.basicInfo.countUnit', { count: instances.length })} />
                  <DetailField label={t('modelManagement:models.detail.basicInfo.featureCount')} value={t('modelManagement:models.detail.basicInfo.countUnit', { count: features.length })} />
                  <DetailField label={t('modelManagement:models.detail.basicInfo.statusLabel')} value={model.isEnabled ? t('modelManagement:models.detail.basicInfo.enabled') : t('modelManagement:models.detail.basicInfo.disabled')} />
                  <div className="sm:col-span-2 xl:col-span-3 rounded-[2px] border border-border-subtle bg-background-subtle/70 px-4 py-3">
                    <div className="text-[11px] uppercase tracking-[0.16em] text-text-muted">{t('modelManagement:models.detail.basicInfo.descriptionLabel')}</div>
                    <div className="mt-2 text-sm leading-6 text-text-secondary">{model.description ?? t('modelManagement:models.detail.basicInfo.noDescription')}</div>
                  </div>
                </div>
              </div>
            </Card>

            <ModelFeatureSectionDnd modelKey={model.modelKey} features={features} />
          </div>

          <Card
            title={t('modelManagement:models.detail.instances.cardTitle')}
            description={t('modelManagement:models.detail.instances.cardDescription')}
            actions={<Button onClick={() => setInstanceOpen(true)}>{t('modelManagement:models.detail.instances.addButton')}</Button>}
            className="border-primary/20"
          >
            <div className="space-y-4">
              <div className="grid gap-3 md:grid-cols-4">
                <InstanceStat label={t('modelManagement:models.detail.instances.stats.total')} value={`${instances.length}`} />
                <InstanceStat label={t('modelManagement:models.detail.instances.stats.healthy')} value={instances.length ? `${Math.round((healthyInstanceCount / instances.length) * 100)}%` : '0%'} />
                <InstanceStat label={t('modelManagement:models.detail.instances.stats.enabled')} value={`${enabledInstanceCount}`} />
                <InstanceStat label={t('modelManagement:models.detail.instances.stats.regions')} value={`${regionCount}`} />
              </div>

              {instances.length ? (
                <div className="grid gap-4 xl:grid-cols-2">
                  {instances.map((instance) => (
                    <div
                      key={instance.instanceKey}
                      className="rounded-[2px] border border-border bg-surface/80 p-5"
                    >
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div className="min-w-0">
                          <div className="font-semibold text-text">{instance.instanceKey}</div>
                          <div className="mt-1 text-sm text-text-secondary">{instance.modelName}</div>
                          <div className="mt-2 text-xs text-text-muted">
                            {instance.providerDeploymentName ?? t('modelManagement:models.detail.instances.defaultDeploy')} / {instance.region ?? t('modelManagement:models.detail.instances.defaultRegion')}
                          </div>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          <Badge tone={instance.isEnabled ? 'success' : 'warning'}>{instance.isEnabled ? t('modelManagement:models.detail.instances.status.enabled') : t('modelManagement:models.detail.instances.status.disabled')}</Badge>
                          <Badge tone={instance.isHealthy ? 'success' : 'danger'}>{instance.isHealthy ? t('modelManagement:models.detail.instances.status.healthy') : t('modelManagement:models.detail.instances.status.unhealthy')}</Badge>
                        </div>
                      </div>

                      <div className="mt-4 grid gap-3 sm:grid-cols-2">
                        <DetailField label={t('modelManagement:models.detail.instances.fields.deployName')} value={instance.providerDeploymentName ?? t('modelManagement:models.detail.instances.defaultDeploy')} />
                        <DetailField label={t('modelManagement:models.detail.instances.fields.region')} value={instance.region ?? t('modelManagement:models.detail.instances.defaultRegion')} />
                        <DetailField label={t('modelManagement:models.detail.instances.fields.priority')} value={`${instance.priority}`} />
                        <DetailField label={t('modelManagement:models.detail.instances.fields.weight')} value={`${instance.weight}`} />
                        <DetailField label={t('modelManagement:models.detail.instances.fields.timeout')} value={`${instance.defaultTimeoutMs} ms`} />
                        <DetailField label={t('modelManagement:models.detail.instances.fields.type')} value={instance.type} />
                      </div>

                      <div className="mt-4 flex justify-end">
                        <Button variant="secondary" onClick={() => setEditingInstance(instance)}>
                          {t('modelManagement:models.detail.instances.editButton')}
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <EmptyState title={t('modelManagement:models.detail.instances.empty')} />
              )}
            </div>
          </Card>

          <Card
            title={t('modelManagement:models.detail.bindings.cardTitle')}
            description={t('modelManagement:models.detail.bindings.cardDescription')}
            actions={<Button variant="secondary" onClick={() => setBindingOpen(true)}>{t('modelManagement:models.detail.bindings.addButton')}</Button>}
          >
            {bindings.length ? (
              <div className="space-y-3">
                {bindings.map((binding) => (
                  <div key={binding.bindingKey} className="rounded-[2px] border border-border bg-surface/70 p-4">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <div className="font-medium text-text">{binding.displayName}</div>
                        <div className="mt-1 text-xs text-text-muted">
                          {binding.bindingKey} / {getCapabilityLabel(t, binding.capability)}
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <Badge tone={binding.isEnabled ? 'success' : 'warning'}>{binding.isEnabled ? t('modelManagement:models.detail.bindings.status.enabled') : t('modelManagement:models.detail.bindings.status.disabled')}</Badge>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState title={t('modelManagement:models.detail.bindings.empty')} />
            )}
          </Card>
        </div>
      ) : null}

      <ModelInstanceDrawer
        key={editingInstance ? `edit:${editingInstance.instanceKey}` : `create:${modelKey}:${instanceOpen ? 'open' : 'closed'}`}
        open={instanceOpen || editingInstance !== null}
        mode={editingInstance ? 'edit' : 'create'}
        initialValue={editingInstance}
        modelKeyPreset={editingInstance ? undefined : modelKey}
        loading={instanceMutations.create.isPending || instanceMutations.update.isPending}
        error={
          instanceMutations.create.error
            ? instanceMutations.getMutationMessage(instanceMutations.create.error)
            : instanceMutations.update.error
              ? instanceMutations.getMutationMessage(instanceMutations.update.error)
              : null
        }
        onClose={() => {
          setInstanceOpen(false);
          setEditingInstance(null);
          instanceMutations.create.reset();
          instanceMutations.update.reset();
        }}
        onSubmit={async ({ modelKey: targetModelKey, model }) => {
          if (editingInstance) {
            await instanceMutations.update.mutateAsync({ instanceKey: editingInstance.instanceKey, model });
            setEditingInstance(null);
            return;
          }

          await instanceMutations.create.mutateAsync({ modelKey: targetModelKey, model });
          setInstanceOpen(false);
        }}
      />

      <ModelBindingDrawer
        open={bindingOpen}
        mode="create"
        initialValue={null}
        modelKeyPreset={modelKey}
        loading={bindingMutations.create.isPending}
        error={bindingMutations.create.error ? bindingMutations.getMutationMessage(bindingMutations.create.error) : null}
        onClose={() => {
          setBindingOpen(false);
          bindingMutations.create.reset();
        }}
        onSubmit={async (model) => {
          await bindingMutations.create.mutateAsync(model);
          setBindingOpen(false);
        }}
      />
    </PageFrame>
  );
}
