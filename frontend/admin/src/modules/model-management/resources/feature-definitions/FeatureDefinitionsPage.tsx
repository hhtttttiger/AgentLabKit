import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Plus } from 'lucide-react';
import {
  getEnabledFilterOptions,
  getFilterableFilterOptions,
  getRoutableFilterOptions,
  getValueTypeLabel,
  valueTypeOptions,
} from '@/shared/config/catalogOptions';
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
import { useToast } from '@/shared/ui/Toast';
import { Pagination } from '@/shared/ui/Pagination';
import { SelectField } from '@/shared/ui/FormFields';
import type { LlmFeatureView } from '../../lib/contracts';
import { FeatureDrawer } from './FeatureDefinitionDrawer';
import { defaultFeatureFilters, toFeatureQuery } from './types';
import { useFeatureList, useFeatureMutations } from './hooks';

export function FeaturesPage() {
  const [filters, setFilters] = useState(defaultFeatureFilters);
  const [editingItem, setEditingItem] = useState<LlmFeatureView | null>(null);
  const [deletingItem, setDeletingItem] = useState<LlmFeatureView | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const { t } = useTranslation();
  const { toast } = useToast();
  const enabledFilterOptions = getEnabledFilterOptions(t);
  const filterableFilterOptions = getFilterableFilterOptions(t);
  const routableFilterOptions = getRoutableFilterOptions(t);

  const query = useMemo(() => toFeatureQuery(filters), [filters]);
  const listQuery = useFeatureList(query);
  const mutations = useFeatureMutations();
  const rows = listQuery.data?.items ?? [];

  const columns = useMemo<TableColumn<LlmFeatureView>[]>(
    () => [
      {
        key: 'featureKey',
        header: t('modules.modelManagement.featureDefinitions.page.columns.featureKey'),
        render: (row) => (
          <div>
            <div className="font-medium text-text">{row.displayName}</div>
            <div className="mt-1 text-xs text-text-muted">{row.featureKey}</div>
          </div>
        ),
      },
      {
        key: 'valueType',
        header: t('modules.modelManagement.featureDefinitions.page.columns.valueType'),
        render: (row) => <Badge tone="neutral">{getValueTypeLabel(row.valueType)}</Badge>,
      },
      {
        key: 'flags',
        header: t('modules.modelManagement.featureDefinitions.page.columns.flags'),
        render: (row) => (
          <div className="flex flex-wrap gap-1">
            {row.isFilterable ? <Badge tone="success">{t('modules.modelManagement.featureDefinitions.page.flags.filterable')}</Badge> : null}
            {row.isRoutable ? <Badge tone="warning">{t('modules.modelManagement.featureDefinitions.page.flags.routable')}</Badge> : null}
          </div>
        ),
      },
      {
        key: 'status',
        header: t('modules.modelManagement.featureDefinitions.page.columns.status'),
        render: (row) => <Badge tone={row.isEnabled ? 'success' : 'warning'}>{row.isEnabled ? t('modules.modelManagement.featureDefinitions.page.status.enabled') : t('modules.modelManagement.featureDefinitions.page.status.disabled')}</Badge>,
      },
      {
        key: 'actions',
        header: t('modules.modelManagement.featureDefinitions.page.columns.actions'),
        render: (row) => (
          <RowActions actions={[
            { label: t('modules.modelManagement.featureDefinitions.page.rowActions.edit'), onClick: () => setEditingItem(row) },
            { label: t('modules.modelManagement.featureDefinitions.page.rowActions.delete'), onClick: () => setDeletingItem(row), variant: 'danger' },
          ]} />
        ),
      },
    ],
    [t],
  );

  return (
    <>
      <ManagementListFrame
        refreshing={listQuery.isFetching}
        toolbar={
          <FilterToolbar
            compact
            actions={
              <FilterToolbarActions
                onRefresh={() => listQuery.refetch()}
                refreshing={listQuery.isFetching}
                onReset={() => setFilters(defaultFeatureFilters)}
              >
                <ToolbarButton
                  variant="primary"
                  onClick={() => setCreateOpen(true)}
                >
                  <Plus size={14} />
                  {t('modules.modelManagement.featureDefinitions.page.newFeature')}
                </ToolbarButton>
              </FilterToolbarActions>
            }
          >
            <SelectField
              label={t('modules.modelManagement.featureDefinitions.page.filters.valueType')}
              fieldSize="compact"
              value={filters.valueType}
              onChange={(event) => setFilters((current) => ({ ...current, valueType: event.target.value as typeof current.valueType, page: 1 }))}
            >
              <option value="">{t('modules.modelManagement.featureDefinitions.page.filters.allTypes')}</option>
              {valueTypeOptions.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </SelectField>
            <div className="filter-narrow">
              <SelectField
                label={t('modules.modelManagement.featureDefinitions.page.filters.enableStatus')}
                fieldSize="compact"
                value={filters.isEnabled}
                onChange={(event) => setFilters((current) => ({ ...current, isEnabled: event.target.value as typeof current.isEnabled, page: 1 }))}
              >
                {enabledFilterOptions.map((item) => (
                  <option key={item.value} value={item.value}>
                    {item.label}
                  </option>
                ))}
              </SelectField>
            </div>
            <div className="filter-narrow">
              <SelectField
                label={t('modules.modelManagement.featureDefinitions.page.filters.filterable')}
                fieldSize="compact"
                value={filters.isFilterable}
                onChange={(event) => setFilters((current) => ({ ...current, isFilterable: event.target.value as typeof current.isFilterable, page: 1 }))}
              >
                {filterableFilterOptions.map((item) => (
                  <option key={item.value} value={item.value}>
                    {item.label}
                  </option>
                ))}
              </SelectField>
            </div>
            <div className="filter-narrow">
              <SelectField
                label={t('modules.modelManagement.featureDefinitions.page.filters.routable')}
                fieldSize="compact"
                value={filters.isRoutable}
                onChange={(event) => setFilters((current) => ({ ...current, isRoutable: event.target.value as typeof current.isRoutable, page: 1 }))}
              >
                {routableFilterOptions.map((item) => (
                  <option key={item.value} value={item.value}>
                    {item.label}
                  </option>
                ))}
              </SelectField>
            </div>
          </FilterToolbar>
        }
        error={listQuery.isError ? <InlineMessage tone="error">{mutations.getMutationMessage(listQuery.error)}</InlineMessage> : undefined}
        pagination={
          <Pagination
            page={filters.page}
            pageSize={filters.pageSize}
            totalCount={listQuery.data?.totalCount ?? 0}
            onChange={(page) => setFilters((current) => ({ ...current, page }))}
          />
        }
      >
        <DataTable
          columns={columns}
          rows={rows}
          getRowKey={(row) => row.featureKey}
          loading={listQuery.isLoading}
          emptyState={
            <EmptyState
              title={t('modules.modelManagement.featureDefinitions.page.emptyTitle')}
              action={<Button onClick={() => setCreateOpen(true)}>{t('modules.modelManagement.featureDefinitions.page.createNow')}</Button>}
            />
          }
        />
      </ManagementListFrame>

      <FeatureDrawer
        open={createOpen || editingItem !== null}
        mode={editingItem ? 'edit' : 'create'}
        initialValue={editingItem}
        loading={mutations.create.isPending || mutations.update.isPending}
        error={
          mutations.create.error
            ? mutations.getMutationMessage(mutations.create.error)
            : mutations.update.error
              ? mutations.getMutationMessage(mutations.update.error)
              : null
        }
        onClose={() => {
          setCreateOpen(false);
          setEditingItem(null);
          mutations.create.reset();
          mutations.update.reset();
        }}
        onSubmit={async (model) => {
          if (editingItem) {
            await mutations.update.mutateAsync({ featureKey: editingItem.featureKey, model });
            setEditingItem(null);
            toast(t('toast.updated'));
          } else {
            await mutations.create.mutateAsync(model);
            setCreateOpen(false);
            toast(t('toast.created'));
          }
        }}
      />

      <ConfirmDialog
        open={deletingItem !== null}
        title={t('modules.modelManagement.featureDefinitions.page.deleteTitle')}
        description={t('modules.modelManagement.featureDefinitions.page.deleteDescription', { name: deletingItem?.displayName ?? '' })}
        confirmLabel={t('modules.modelManagement.featureDefinitions.page.confirmDelete')}
        loading={mutations.remove.isPending}
        onClose={() => {
          setDeletingItem(null);
          mutations.remove.reset();
        }}
        onConfirm={async () => {
          if (!deletingItem) return;
          await mutations.remove.mutateAsync(deletingItem.featureKey);
          setDeletingItem(null);
          toast(t('toast.deleted'));
        }}
      />
    </>
  );
}

// Backward-compatible re-export for route lazy loading
export { FeaturesPage as FeatureDefinitionsPage };
