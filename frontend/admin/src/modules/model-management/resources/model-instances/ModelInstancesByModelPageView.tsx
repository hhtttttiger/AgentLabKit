import { useMemo } from 'react';
import { Plus, Server } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Badge } from '@/shared/ui/Badge';
import { Button } from '@/shared/ui/Button';
import { ConfirmDialog } from '@/shared/ui/ConfirmDialog';
import { DataTable, type TableColumn } from '@/shared/ui/DataTable';
import { EmptyState } from '@/shared/ui/EmptyState';
import { MetricStrip } from '@/shared/ui/MetricStrip';
import { getCapabilityLabel } from '@/shared/config/catalogOptions';
import type { LlmModelInstanceView } from '../../lib/contracts';
import { ModelInstanceDrawer } from './ModelInstanceDrawer';
import type { ModelInstancesByModelPageState } from './useModelInstancesByModelPageState';

function ModelSidebarItem({
  model,
  isSelected,
  onSelect,
}: {
  model: { modelKey: string; displayName: string; isEnabled: boolean; instanceCount: number };
  isSelected: boolean;
  onSelect: () => void;
}) {
  const { t } = useTranslation();
  return (
    <button
      type="button"
      onClick={onSelect}
      className={`w-full text-left rounded-[2px] border px-4 py-3 transition ${
        isSelected
          ? 'border-primary/40 bg-primary/5'
          : 'border-border bg-surface/60 hover:border-border-strong hover:bg-surface'
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className={`text-sm font-medium truncate ${isSelected ? 'text-primary' : 'text-text'}`}>
            {model.displayName}
          </div>
          <div className="mt-0.5 text-xs text-text-muted truncate">{model.modelKey}</div>
        </div>
        <Badge tone={model.isEnabled ? 'success' : 'warning'}>
          {model.isEnabled ? t('modules.modelManagement.modelInstances.page.status.enabled') : t('modules.modelManagement.modelInstances.page.status.disabled')}
        </Badge>
      </div>
      <div className="mt-2 flex items-center gap-1.5 text-xs text-text-muted">
        <Server size={12} />
        <span>{t('modules.modelManagement.instancesByModel.instanceCount', { count: model.instanceCount })}</span>
      </div>
    </button>
  );
}

export function ModelInstancesByModelPageView({ state }: { state: ModelInstancesByModelPageState }) {
  const { t } = useTranslation();

  const columns = useMemo<TableColumn<LlmModelInstanceView>[]>(
    () => [
      {
        key: 'instanceKey',
        header: t('modules.modelManagement.modelInstances.page.columns.instanceKey'),
        render: (row) => (
          <div>
            <div className="font-medium text-[var(--color-ink)]">{row.instanceKey}</div>
            <div className="mt-1 text-xs text-[var(--color-ink-muted)]">{getCapabilityLabel(t, row.type)}</div>
          </div>
        ),
      },
      {
        key: 'priority',
        header: t('modules.modelManagement.modelInstances.page.columns.priority'),
        render: (row) => `${row.priority} / ${row.weight} / ${row.defaultTimeoutMs} ms`,
      },
      {
        key: 'status',
        header: t('modules.modelManagement.modelInstances.page.columns.status'),
        render: (row) => (
          <div className="flex gap-2">
            <Badge tone={row.isEnabled ? 'success' : 'warning'}>
              {row.isEnabled ? t('modules.modelManagement.modelInstances.page.status.enabled') : t('modules.modelManagement.modelInstances.page.status.disabled')}
            </Badge>
            <Badge tone={row.isHealthy ? 'success' : 'danger'}>
              {row.isHealthy ? t('modules.modelManagement.modelInstances.page.status.healthy') : t('modules.modelManagement.modelInstances.page.status.unhealthy')}
            </Badge>
          </div>
        ),
      },
      {
        key: 'actions',
        header: t('modules.modelManagement.modelInstances.page.columns.actions'),
        render: (row) => (
          <div className="flex gap-1">
            <button
              type="button"
              onClick={() => state.openEdit(row)}
              className="text-xs text-primary hover:underline"
            >
              {t('modules.modelManagement.modelInstances.page.rowActions.edit')}
            </button>
            <span className="text-border">|</span>
            <button
              type="button"
              onClick={() => state.requestDelete(row)}
              className="text-xs text-error hover:underline"
            >
              {t('modules.modelManagement.modelInstances.page.rowActions.delete')}
            </button>
          </div>
        ),
      },
    ],
    [state, t],
  );

  const healthyCount = state.instances.items.filter((i) => i.isHealthy).length;
  const enabledCount = state.instances.items.filter((i) => i.isEnabled).length;

  return (
    <div className="flex h-full gap-4">
      {/* Left: Model sidebar */}
      <div className="flex w-64 shrink-0 flex-col gap-2 overflow-y-auto">
        <div className="text-xs font-medium text-text-muted uppercase tracking-wider px-1">
          {t('modules.modelManagement.instancesByModel.modelList')}
        </div>
        {state.models.isLoading ? (
          <div className="space-y-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-20 rounded-[2px] border border-border bg-surface/60 animate-pulse" />
            ))}
          </div>
        ) : state.models.items.length === 0 ? (
          <div className="text-sm text-text-muted py-4 text-center">
            {t('modules.modelManagement.instancesByModel.noModels')}
          </div>
        ) : (
          <div className="space-y-1.5">
            {state.models.items.map((model) => (
              <ModelSidebarItem
                key={model.modelKey}
                model={model}
                isSelected={model.modelKey === state.models.selectedModelKey}
                onSelect={() => state.models.onSelect(model.modelKey)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Right: Instances panel */}
      <div className="flex min-w-0 flex-1 flex-col gap-3">
        {state.models.selectedModelKey ? (
          <>
            <div className="grid grid-cols-[1fr_auto] items-end gap-3">
              <MetricStrip
                showHints={false}
                columns={3}
                items={[
                  { label: t('modules.modelManagement.modelInstances.page.metrics.total'), value: state.instances.totalCount, hint: '' },
                  { label: t('modules.modelManagement.modelInstances.page.metrics.enabled'), value: enabledCount, hint: '' },
                  { label: t('modules.modelManagement.modelInstances.page.metrics.healthy'), value: healthyCount, hint: '' },
                ]}
              />
              <Button onClick={state.openCreate} className="shrink-0">
                <Plus size={14} />
                {t('modules.modelManagement.modelInstances.page.newInstance')}
              </Button>
            </div>

            <div className="min-h-0 flex-1 overflow-y-auto">
              <DataTable
                columns={columns}
                rows={state.instances.items}
                getRowKey={(row) => row.instanceKey}
                loading={state.instances.isLoading}
                emptyState={
                  <EmptyState
                    title={t('modules.modelManagement.instancesByModel.emptyTitle')}
                    description={t('modules.modelManagement.instancesByModel.emptyDescription')}
                    action={
                      <Button onClick={state.openCreate}>
                        <Plus size={14} />
                        {t('modules.modelManagement.modelInstances.page.newInstance')}
                      </Button>
                    }
                  />
                }
              />
            </div>
          </>
        ) : (
          <div className="flex flex-1 items-center justify-center">
            <EmptyState
              title={t('modules.modelManagement.instancesByModel.selectModel')}
              description={t('modules.modelManagement.instancesByModel.selectModelHint')}
            />
          </div>
        )}
      </div>

      <ModelInstanceDrawer
        key={state.drawer.mode === 'edit' ? `edit:${state.drawer.initialValue?.instanceKey ?? 'none'}` : `create:${state.drawer.open ? 'open' : 'closed'}`}
        open={state.drawer.open}
        mode={state.drawer.mode}
        initialValue={state.drawer.initialValue}
        modelKeyPreset={state.drawer.modelKeyPreset ?? undefined}
        loading={state.drawer.loading}
        error={state.drawer.error}
        onClose={state.drawer.onClose}
        onSubmit={state.drawer.onSubmit}
      />

      <ConfirmDialog
        open={state.deleteDialog.open}
        title={t('modules.modelManagement.modelInstances.page.deleteTitle')}
        description={state.deleteDialog.description}
        confirmLabel={t('modules.modelManagement.modelInstances.page.confirmDelete')}
        loading={state.deleteDialog.loading}
        onClose={state.deleteDialog.onClose}
        onConfirm={state.deleteDialog.onConfirm}
      />
    </div>
  );
}
