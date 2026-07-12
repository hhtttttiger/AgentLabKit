import { useMemo } from 'react';
import { Plus } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { capabilityOptions, getEnabledFilterOptions, getHealthFilterOptions, getCapabilityLabel } from '@/shared/config/catalogOptions';
import { Badge } from '@/shared/ui/Badge';
import { Button } from '@/shared/ui/Button';
import { RowActions } from '@/shared/ui/RowActions';
import { ToolbarButton } from '@/shared/ui/ToolbarButton';
import { ConfirmDialog } from '@/shared/ui/ConfirmDialog';
import { DataTable, type TableColumn } from '@/shared/ui/DataTable';
import { EmptyState } from '@/shared/ui/EmptyState';
import { FilterToolbar } from '@/shared/ui/FilterToolbar';
import { FilterToolbarActions } from '@/shared/ui/FilterToolbarActions';
import { InlineMessage } from '@/shared/ui/InlineMessage';
import { ManagementListFrame } from '@/shared/ui/ManagementListFrame';
import { MetricStrip } from '@/shared/ui/MetricStrip';
import { Pagination } from '@/shared/ui/Pagination';
import { SelectField, TextField } from '@/shared/ui/FormFields';
import type { LlmModelInstanceView } from '../../lib/contracts';
import { ModelInstanceDrawer } from './ModelInstanceDrawer';
import type { ModelInstancesPageState } from './useModelInstancesPageState';
import { defaultModelInstanceFilters } from './types';

export function ModelInstancesPageView({ state }: { state: ModelInstancesPageState }) {
  const { t } = useTranslation(['common', 'modelManagement']);
  const enabledFilterOptions = getEnabledFilterOptions(t);
  const healthFilterOptions = getHealthFilterOptions(t);
  const columns = useMemo<TableColumn<LlmModelInstanceView>[]>(
    () => [
      {
        key: 'instanceKey',
        header: t('modelManagement:modelInstances.page.columns.instanceKey'),
        render: (row) => (
          <div>
            <div className="font-medium text-[var(--color-ink)]">{row.instanceKey}</div>
            <div className="mt-1 text-xs text-[var(--color-ink-muted)]">
              {row.modelKey} / {getCapabilityLabel(t, row.type)}
            </div>
          </div>
        ),
      },
      {
        key: 'modelName',
        header: t('modelManagement:modelInstances.page.columns.modelName'),
        render: (row) => row.modelName,
      },
      {
        key: 'priority',
        header: t('modelManagement:modelInstances.page.columns.priority'),
        render: (row) => `${row.priority} / ${row.weight} / ${row.defaultTimeoutMs} ms`,
      },
      {
        key: 'status',
        header: t('modelManagement:modelInstances.page.columns.status'),
        render: (row) => (
          <div className="flex gap-2">
            <Badge tone={row.isEnabled ? 'success' : 'warning'}>{row.isEnabled ? t('modelManagement:modelInstances.page.status.enabled') : t('modelManagement:modelInstances.page.status.disabled')}</Badge>
            <Badge tone={row.isHealthy ? 'success' : 'danger'}>{row.isHealthy ? t('modelManagement:modelInstances.page.status.healthy') : t('modelManagement:modelInstances.page.status.unhealthy')}</Badge>
          </div>
        ),
      },
      {
        key: 'actions',
        header: t('modelManagement:modelInstances.page.columns.actions'),
        render: (row) => (
          <RowActions actions={[
            { label: t('modelManagement:modelInstances.page.rowActions.edit'), onClick: () => state.openEdit(row) },
            { label: t('modelManagement:modelInstances.page.rowActions.delete'), onClick: () => state.requestDelete(row), variant: 'danger' },
          ]} />
        ),
      },
    ],
    [state, t],
  );

  return (
    <>
      <div className="px-8 pt-6">
        <MetricStrip
          compact
          showHints={false}
          items={[
          { label: t('modelManagement:modelInstances.page.metrics.total'), value: state.listQuery.data?.totalCount ?? 0, hint: t('modelManagement:modelInstances.page.metrics.totalHint') },
          { label: t('modelManagement:modelInstances.page.metrics.enabled'), value: state.metrics.enabledCount, hint: t('modelManagement:modelInstances.page.metrics.enabledHint') },
          { label: t('modelManagement:modelInstances.page.metrics.healthy'), value: state.metrics.healthyCount, hint: t('modelManagement:modelInstances.page.metrics.healthyHint') },
          { label: t('modelManagement:modelInstances.page.metrics.typeCount'), value: state.metrics.typeCount, hint: t('modelManagement:modelInstances.page.metrics.typeCountHint') },
        ]}
      />
      </div>

      <ManagementListFrame
        refreshing={state.listQuery.isFetching}
        toolbar={
          <FilterToolbar
            compact
            actions={
              <FilterToolbarActions
                onRefresh={() => state.listQuery.refetch()}
                refreshing={state.listQuery.isFetching}
                onReset={state.resetFilters}
              >
                <ToolbarButton variant="primary" onClick={state.openCreate}>
                  <Plus size={14} />
                  {t('modelManagement:modelInstances.page.newInstance')}
                </ToolbarButton>
              </FilterToolbarActions>
            }
          >
          <TextField fieldSize="compact" label={t('modelManagement:modelInstances.page.filters.modelKey')} value={state.filters.modelKey} onChange={(event) => state.patchFilters({ modelKey: event.target.value, page: 1 })} />
          <SelectField fieldSize="compact" label={t('modelManagement:modelInstances.page.filters.feature')} value={state.filters.featureKey} onChange={(event) => state.patchFilters({ featureKey: event.target.value, page: 1 })}>
            <option value="">{state.featureOptionsQuery.isLoading ? t('modelManagement:modelInstances.page.filters.loading') : t('modelManagement:modelInstances.page.filters.featureAll')}</option>
            {(state.featureOptionsQuery.data ?? []).map((item) => (
              <option key={item.featureKey} value={item.featureKey}>
                {item.displayName}
              </option>
            ))}
          </SelectField>
          <SelectField fieldSize="compact" label={t('modelManagement:modelInstances.page.filters.featureSupport')} value={state.filters.featureIsSupported} onChange={(event) => state.patchFilters({ featureIsSupported: event.target.value as typeof defaultModelInstanceFilters.featureIsSupported, page: 1 })}>
            <option value="all">{t('modelManagement:modelInstances.page.filters.featureSupportAll')}</option>
            <option value="true">{t('modelManagement:modelInstances.page.filters.featureSupportTrue')}</option>
            <option value="false">{t('modelManagement:modelInstances.page.filters.featureSupportFalse')}</option>
          </SelectField>
          <TextField fieldSize="compact" label={t('modelManagement:modelInstances.page.filters.featureValue')} value={state.filters.featureValueJson} onChange={(event) => state.patchFilters({ featureValueJson: event.target.value, page: 1 })} />
          <SelectField fieldSize="compact" label={t('modelManagement:modelInstances.page.filters.type')} value={state.filters.type} onChange={(event) => state.patchFilters({ type: event.target.value as typeof defaultModelInstanceFilters.type, page: 1 })}>
            <option value="">{t('modelManagement:modelInstances.page.filters.typeAll')}</option>
            {capabilityOptions.map((item) => (
              <option key={item.value} value={item.value}>
                {getCapabilityLabel(t, item.value)}
              </option>
            ))}
          </SelectField>
          <div className="filter-narrow">
            <SelectField fieldSize="compact" label={t('modelManagement:modelInstances.page.filters.enableStatus')} value={state.filters.isEnabled} onChange={(event) => state.patchFilters({ isEnabled: event.target.value as typeof defaultModelInstanceFilters.isEnabled, page: 1 })}>
              {enabledFilterOptions.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </SelectField>
          </div>
          <div className="filter-narrow">
            <SelectField fieldSize="compact" label={t('modelManagement:modelInstances.page.filters.healthStatus')} value={state.filters.isHealthy} onChange={(event) => state.patchFilters({ isHealthy: event.target.value as typeof defaultModelInstanceFilters.isHealthy, page: 1 })}>
              {healthFilterOptions.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </SelectField>
          </div>
        </FilterToolbar>
        }
        error={state.listQuery.isError ? <InlineMessage tone="error">{state.drawer.error}</InlineMessage> : undefined}
        pagination={
          <Pagination
            page={state.filters.page}
            pageSize={state.filters.pageSize}
            totalCount={state.listQuery.data?.totalCount ?? 0}
            onChange={state.setPage}
          />
        }
      >
        <DataTable
          columns={columns}
          rows={state.rows}
          getRowKey={(row) => row.instanceKey}
          loading={state.listQuery.isLoading}
          emptyState={
              <EmptyState
                title={t('modelManagement:modelInstances.page.emptyTitle')}
                action={<Button onClick={state.openCreate}>{t('modelManagement:modelInstances.page.createInstance')}</Button>}
              />
          }
        />
      </ManagementListFrame>

      <ModelInstanceDrawer
        key={state.drawer.mode === 'edit' ? `edit:${state.drawer.initialValue?.instanceKey ?? 'none'}` : `create:${state.drawer.open ? 'open' : 'closed'}`}
        open={state.drawer.open}
        mode={state.drawer.mode}
        initialValue={state.drawer.initialValue}
        loading={state.drawer.loading}
        error={state.drawer.error}
        onClose={state.drawer.onClose}
        onSubmit={state.drawer.onSubmit}
      />

      <ConfirmDialog
        open={state.deleteDialog.open}
        title={t('modelManagement:modelInstances.page.deleteTitle')}
        description={state.deleteDialog.description}
        confirmLabel={t('modelManagement:modelInstances.page.confirmDelete')}
        loading={state.deleteDialog.loading}
        onClose={state.deleteDialog.onClose}
        onConfirm={state.deleteDialog.onConfirm}
      />
    </>
  );
}
