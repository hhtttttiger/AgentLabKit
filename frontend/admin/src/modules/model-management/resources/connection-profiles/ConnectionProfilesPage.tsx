import { useMemo, useState } from 'react';
import { Plus } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { providerOptions, getEnabledFilterOptions, getProviderLabel } from '@/shared/config/catalogOptions';
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
import type { LlmConnectionProfileView } from '../../lib/contracts';
import { ConnectionProfileDrawer } from './ConnectionProfileDrawer';
import { defaultConnectionProfileFilters, toConnectionProfileQuery } from './types';
import { useConnectionProfileList, useConnectionProfileMutations } from './hooks';

export function ConnectionProfilesPage() {
  const { t } = useTranslation();
  const { toast } = useToast();
  const [filters, setFilters] = useState(defaultConnectionProfileFilters);
  const [editingItem, setEditingItem] = useState<LlmConnectionProfileView | null>(null);
  const [deletingItem, setDeletingItem] = useState<LlmConnectionProfileView | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const enabledFilterOptions = getEnabledFilterOptions(t);

  const query = useMemo(() => toConnectionProfileQuery(filters), [filters]);
  const listQuery = useConnectionProfileList(query);
  const mutations = useConnectionProfileMutations();
  const rows = listQuery.data?.items ?? [];

  const columns = useMemo<TableColumn<LlmConnectionProfileView>[]>(
    () => [
      {
        key: 'profileKey',
        header: t('modules.modelManagement.connectionProfiles.page.columns.profileKey'),
        render: (row) => (
          <div>
            <div className="font-medium text-text">{row.displayName}</div>
            <div className="mt-1 text-xs text-text-muted">{row.profileKey}</div>
          </div>
        ),
      },
      {
        key: 'provider',
        header: 'Provider',
        render: (row) => <Badge>{getProviderLabel(row.provider)}</Badge>,
      },
      {
        key: 'endpoint',
        header: t('modules.modelManagement.connectionProfiles.page.columns.endpoint'),
        render: (row) => row.baseUrl ?? row.webSocketBaseUrl ?? '-',
      },
      {
        key: 'status',
        header: t('modules.modelManagement.connectionProfiles.page.columns.status'),
        render: (row) => <Badge tone={row.isEnabled ? 'success' : 'warning'}>{row.isEnabled ? t('modules.modelManagement.connectionProfiles.page.status.enabled') : t('modules.modelManagement.connectionProfiles.page.status.disabled')}</Badge>,
      },
      {
        key: 'actions',
        header: t('modules.modelManagement.connectionProfiles.page.columns.actions'),
        render: (row) => (
          <RowActions actions={[
            { label: t('modules.modelManagement.connectionProfiles.page.rowActions.edit'), onClick: () => setEditingItem(row) },
            { label: t('modules.modelManagement.connectionProfiles.page.rowActions.delete'), onClick: () => setDeletingItem(row), variant: 'danger' },
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
                onReset={() => setFilters(defaultConnectionProfileFilters)}
              >
                <ToolbarButton variant="primary" onClick={() => setCreateOpen(true)}>
                  <Plus size={14} />
                  {t('modules.modelManagement.connectionProfiles.page.newProfile')}
                </ToolbarButton>
              </FilterToolbarActions>
            }
          >
            <SelectField
              label={t('modules.modelManagement.connectionProfiles.page.filters.provider')}
              fieldSize="compact"
              value={filters.provider}
              onChange={(event) => setFilters((current) => ({ ...current, provider: event.target.value as typeof current.provider, page: 1 }))}
            >
              <option value="">{t('modules.modelManagement.connectionProfiles.page.filters.allProviders')}</option>
              {providerOptions.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </SelectField>
            <div className="filter-narrow">
              <SelectField
                label={t('modules.modelManagement.connectionProfiles.page.filters.enableStatus')}
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
          getRowKey={(row) => row.profileKey}
          loading={listQuery.isLoading}
          emptyState={
            <EmptyState
              title={t('modules.modelManagement.connectionProfiles.page.emptyTitle')}
              action={<Button onClick={() => setCreateOpen(true)}>{t('modules.modelManagement.models.page.createModel')}</Button>}
            />
          }
        />
      </ManagementListFrame>

      <ConnectionProfileDrawer
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
            await mutations.update.mutateAsync({ profileKey: editingItem.profileKey, model });
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
        title={t('modules.modelManagement.connectionProfiles.page.deleteTitle')}
        description={deletingItem ? t('modules.modelManagement.connectionProfiles.page.deleteDescription', { name: deletingItem.displayName }) : ''}
        confirmLabel={t('modules.modelManagement.connectionProfiles.page.confirmDelete')}
        loading={mutations.remove.isPending}
        onClose={() => {
          setDeletingItem(null);
          mutations.remove.reset();
        }}
        onConfirm={async () => {
          if (!deletingItem) return;
          await mutations.remove.mutateAsync(deletingItem.profileKey);
          setDeletingItem(null);
          toast(t('toast.deleted'));
        }}
      />
    </>
  );
}
