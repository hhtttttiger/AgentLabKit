import { useState } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Badge } from '@/shared/ui/Badge';
import { Button } from '@/shared/ui/Button';
import { EmptyState } from '@/shared/ui/EmptyState';
import { InlineMessage } from '@/shared/ui/InlineMessage';
import type { LlmModelInstanceView } from '../../../lib/contracts';
import { DetailField, InstanceStat } from '../../../lib/DetailComponents';
import { useModelDetail } from '../hooks';
import { useModelInstanceMutations, useModelInstancesByModel } from '../../model-instances/hooks';
import { ModelInstanceDrawer } from '../../model-instances/ModelInstanceDrawer';

export function ModelInstancesTab() {
  const { modelKey } = useParams<{ modelKey: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const { t } = useTranslation();
  const detailQuery = useModelDetail(modelKey);
  const instanceMutations = useModelInstanceMutations();
  const instancesQuery = useModelInstancesByModel(modelKey ?? null);

  const [editingInstance, setEditingInstance] = useState<LlmModelInstanceView | null>(null);

  const isCreating = searchParams.get('action') === 'create';
  const drawerOpen = isCreating || editingInstance !== null;

  function openCreate() {
    setSearchParams({ action: 'create' });
  }

  function closeDrawer() {
    setSearchParams({});
    setEditingInstance(null);
    instanceMutations.create.reset();
    instanceMutations.update.reset();
  }

  if (!modelKey) return null;

  const card = detailQuery.data;

  if (detailQuery.isError) {
    return <InlineMessage tone="error">{t('modules.modelManagement.models.tabs.loadFailed')}</InlineMessage>;
  }

  if (!card && detailQuery.isLoading) {
    return <div className="text-sm text-text-secondary">{t('modules.modelManagement.models.tabs.loading')}</div>;
  }

  if (!card) return null;

  const instances = instancesQuery.data?.items ?? [];
  const healthyInstanceCount = instances.filter((i) => i.isHealthy).length;
  const enabledInstanceCount = instances.filter((i) => i.isEnabled).length;
  const regionCount = new Set(instances.map((i) => i.region ?? t('modules.modelManagement.models.tabs.instances.defaultRegion'))).size;

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <p className="text-sm text-text-secondary">{t('modules.modelManagement.models.tabs.instances.description')}</p>
        <Button onClick={openCreate}>{t('modules.modelManagement.models.tabs.instances.addButton')}</Button>
      </div>

      <div className="grid gap-3 md:grid-cols-4">
        <InstanceStat label={t('modules.modelManagement.models.tabs.instances.stats.total')} value={`${instances.length}`} />
        <InstanceStat label={t('modules.modelManagement.models.tabs.instances.stats.healthy')} value={instances.length ? `${Math.round((healthyInstanceCount / instances.length) * 100)}%` : '0%'} />
        <InstanceStat label={t('modules.modelManagement.models.tabs.instances.stats.enabled')} value={`${enabledInstanceCount}`} />
        <InstanceStat label={t('modules.modelManagement.models.tabs.instances.stats.regions')} value={`${regionCount}`} />
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
                    {instance.providerDeploymentName ?? t('modules.modelManagement.models.tabs.instances.defaultDeploy')} / {instance.region ?? t('modules.modelManagement.models.tabs.instances.defaultRegion')}
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Badge tone={instance.isEnabled ? 'success' : 'warning'}>{instance.isEnabled ? t('modules.modelManagement.models.tabs.instances.status.enabled') : t('modules.modelManagement.models.tabs.instances.status.disabled')}</Badge>
                  <Badge tone={instance.isHealthy ? 'success' : 'danger'}>{instance.isHealthy ? t('modules.modelManagement.models.tabs.instances.status.healthy') : t('modules.modelManagement.models.tabs.instances.status.unhealthy')}</Badge>
                </div>
              </div>

              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                <DetailField label={t('modules.modelManagement.models.tabs.instances.fields.deployName')} value={instance.providerDeploymentName ?? t('modules.modelManagement.models.tabs.instances.defaultDeploy')} />
                <DetailField label={t('modules.modelManagement.models.tabs.instances.fields.region')} value={instance.region ?? t('modules.modelManagement.models.tabs.instances.defaultRegion')} />
                <DetailField label={t('modules.modelManagement.models.tabs.instances.fields.priority')} value={`${instance.priority}`} />
                <DetailField label={t('modules.modelManagement.models.tabs.instances.fields.weight')} value={`${instance.weight}`} />
                <DetailField label={t('modules.modelManagement.models.tabs.instances.fields.timeout')} value={`${instance.defaultTimeoutMs} ms`} />
                <DetailField label={t('modules.modelManagement.models.tabs.instances.fields.type')} value={instance.type} />
              </div>

              <div className="mt-4 flex justify-end">
                <Button variant="secondary" onClick={() => setEditingInstance(instance)}>{t('modules.modelManagement.models.tabs.instances.editButton')}</Button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <EmptyState title={t('modules.modelManagement.models.tabs.instances.empty')} />
      )}

      <ModelInstanceDrawer
        key={editingInstance ? `edit:${editingInstance.instanceKey}` : `create:${modelKey}:${drawerOpen ? 'open' : 'closed'}`}
        open={drawerOpen}
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
        onClose={closeDrawer}
        onSubmit={async ({ modelKey: targetModelKey, model }) => {
          if (editingInstance) {
            await instanceMutations.update.mutateAsync({ instanceKey: editingInstance.instanceKey, model });
            setEditingInstance(null);
            return;
          }
          await instanceMutations.create.mutateAsync({ modelKey: targetModelKey, model });
          closeDrawer();
        }}
      />
    </div>
  );
}
