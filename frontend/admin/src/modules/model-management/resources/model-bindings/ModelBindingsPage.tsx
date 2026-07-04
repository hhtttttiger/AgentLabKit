import { useEffect, useMemo, useState } from 'react';
import { Plus } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { capabilityOptions, getEnabledFilterOptions, getCapabilityLabel } from '@/shared/config/catalogOptions';
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
import { SelectField, TextField } from '@/shared/ui/FormFields';
import type { LlmModelBindingView } from '../../lib/contracts';
import { ModelBindingDrawer } from './ModelBindingDrawer';
import { defaultModelBindingFilters, toModelBindingQuery } from './types';
import { useModelBindingList, useModelBindingMutations } from './hooks';

export function ModelBindingsPage() {
  const { t } = useTranslation();
  const { toast } = useToast();
  const enabledFilterOptions = getEnabledFilterOptions(t);
  const [filters, setFilters] = useState(defaultModelBindingFilters);
  const [editingItem, setEditingItem] = useState<LlmModelBindingView | null>(null);
  const [deletingItem, setDeletingItem] = useState<LlmModelBindingView | null>(null);
  const [createOpen, setCreateOpen] = useState(false);

  // Debounced modelKey filter — immediate display, delayed API call
  const [modelKeyInput, setModelKeyInput] = useState(filters.modelKey);

  useEffect(() => {
    const timer = setTimeout(() => {
      setFilters((current) => {
        if (current.modelKey === modelKeyInput) return current;
        return { ...current, modelKey: modelKeyInput, page: 1 };
      });
    }, 300);
    return () => clearTimeout(timer);
  }, [modelKeyInput]);

  const query = useMemo(() => toModelBindingQuery(filters), [filters]);
  const listQuery = useModelBindingList(query);
  const mutations = useModelBindingMutations();
  const rows = listQuery.data?.items ?? [];

  const columns = useMemo<TableColumn<LlmModelBindingView>[]>(
    () => [
      {
        key: 'bindingKey',
        header: t('modules.modelManagement.modelBindings.page.columns.bindingKey'),
        render: (row) => (
          <div>
            <div className="font-medium text-text">{row.displayName}</div>
            <div className="mt-1 text-xs text-text-muted">{row.bindingKey}</div>
          </div>
        ),
      },
      {
        key: 'usage',
        header: t('modules.modelManagement.modelBindings.page.columns.usage'),
        render: (row) => (
          <div className="font-medium text-text">{getCapabilityLabel(t, row.capability)}</div>
        ),
      },
      {
        key: 'mapping',
        header: t('modules.modelManagement.modelBindings.page.columns.mapping'),
        render: (row) => (
          <div className="space-y-1">
            <div>{getCapabilityLabel(t, row.capability)}</div>
            <div className="text-xs text-text-muted">{row.modelKey}</div>
          </div>
        ),
      },
      {
        key: 'status',
        header: t('modules.modelManagement.modelBindings.page.columns.status'),
        render: (row) => <Badge tone={row.isEnabled ? 'success' : 'warning'}>{row.isEnabled ? t('modules.modelManagement.modelBindings.page.status.enabled') : t('modules.modelManagement.modelBindings.page.status.disabled')}</Badge>,
      },
      {
        key: 'actions',
        header: t('modules.modelManagement.modelBindings.page.columns.actions'),
        render: (row) => (
          <RowActions actions={[
            { label: t('modules.modelManagement.modelBindings.page.rowActions.edit'), onClick: () => setEditingItem(row) },
            { label: t('modules.modelManagement.modelBindings.page.rowActions.delete'), onClick: () => setDeletingItem(row), variant: 'danger' },
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
                onReset={() => { setFilters(defaultModelBindingFilters); setModelKeyInput(''); }}
              >
                <ToolbarButton variant="primary" onClick={() => setCreateOpen(true)}>
                  <Plus size={14} />
                  {t('modules.modelManagement.modelBindings.page.newBinding')}
                </ToolbarButton>
              </FilterToolbarActions>
            }
          >
            <SelectField fieldSize="compact" label={t('modules.modelManagement.modelBindings.page.filters.capability')} value={filters.capability} onChange={(event) => setFilters((current) => ({ ...current, capability: event.target.value as typeof current.capability, page: 1 }))}>
              <option value="">{t('modules.modelManagement.modelBindings.page.filters.allCapabilities')}</option>
              {capabilityOptions.map((item) => (
                <option key={item.value} value={item.value}>
                  {getCapabilityLabel(t, item.value)}
                </option>
              ))}
            </SelectField>
            <TextField fieldSize="compact" label={t('modules.modelManagement.modelBindings.page.filters.modelKey')} value={modelKeyInput} onChange={(event) => setModelKeyInput(event.target.value)} />
            <div className="filter-narrow">
              <SelectField fieldSize="compact" label={t('modules.modelManagement.modelBindings.page.filters.enableStatus')} value={filters.isEnabled} onChange={(event) => setFilters((current) => ({ ...current, isEnabled: event.target.value as typeof current.isEnabled, page: 1 }))}>
                {enabledFilterOptions.map((item) => (
                  <option key={item.value} value={item.value}>
                    {item.label}
                  </option>
                ))}
              </SelectField>
            </div>
          </FilterToolbar>
        }
        error={listQuery.isError ? <InlineMessage tone="error">{mutations.getMutationMessage(listQuery.error)}</InlineMessage> : undefined}
        pagination={<Pagination page={filters.page} pageSize={filters.pageSize} totalCount={listQuery.data?.totalCount ?? 0} onChange={(page) => setFilters((current) => ({ ...current, page }))} />}
      >
        <DataTable
          columns={columns}
          rows={rows}
          getRowKey={(row) => row.bindingKey}
          loading={listQuery.isLoading}
          emptyState={
              <EmptyState
                title={t('modules.modelManagement.modelBindings.page.emptyTitle')}
                action={<Button onClick={() => setCreateOpen(true)}>{t('modules.modelManagement.modelBindings.page.createBinding')}</Button>}
              />
          }
        />
      </ManagementListFrame>

      <ModelBindingDrawer
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
            await mutations.update.mutateAsync({ bindingKey: editingItem.bindingKey, model });
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
        title={t('modules.modelManagement.modelBindings.page.deleteTitle')}
        description={t('modules.modelManagement.modelBindings.page.deleteDescription', { name: deletingItem?.displayName ?? '' })}
        confirmLabel={t('modules.modelManagement.modelBindings.page.confirmDelete')}
        loading={mutations.remove.isPending}
        onClose={() => {
          setDeletingItem(null);
          mutations.remove.reset();
        }}
        onConfirm={async () => {
          if (!deletingItem) return;
          await mutations.remove.mutateAsync(deletingItem.bindingKey);
          setDeletingItem(null);
          toast(t('toast.deleted'));
        }}
      />
    </>
  );
}
