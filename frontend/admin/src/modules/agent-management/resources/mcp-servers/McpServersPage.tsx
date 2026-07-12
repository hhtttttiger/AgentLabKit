import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Plus } from 'lucide-react';
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
import { formatAdminDateTime } from '@/shared/i18n/formatters';
import { useAdminLocale } from '@/shared/i18n/useAdminLocale';
import { McpServerDrawer } from './McpServerDrawer';
import {
  defaultMcpServerFilters,
  filterMcpServerRows,
  paginateRows,
  toMcpServerApiCreateRequest,
  toMcpServerApiUpdateRequest,
  toMcpServerListQuery,
} from './types';
import type { McpServerSummaryView, McpTransport } from './types';
import { useMcpServer, useMcpServerList, useMcpServerMutations } from './hooks';

const am = 'agentManagement:';

const transportTone: Record<McpTransport, 'neutral' | 'warning' | 'success'> = {
  stdio: 'neutral',
  sse: 'warning',
  http: 'success',
};

export function McpServersPage() {
  const { t } = useTranslation(['common', 'agentManagement']);
  const { toast } = useToast();
  const [filters, setFilters] = useState(defaultMcpServerFilters);
  const [editingName, setEditingName] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [deletingItem, setDeletingItem] = useState<McpServerSummaryView | null>(null);

  const query = useMemo(() => toMcpServerListQuery(filters), [filters]);
  const listQuery = useMcpServerList(query);
  const mutations = useMcpServerMutations();
  const detailQuery = useMcpServer(editingName ?? '');
  const { locale } = useAdminLocale();

  const filteredRows = useMemo(
    () => filterMcpServerRows(listQuery.data ?? [], filters),
    [filters, listQuery.data],
  );
  const pagedRows = useMemo(
    () => paginateRows(filteredRows, filters.page, filters.pageSize),
    [filteredRows, filters.page, filters.pageSize],
  );

  const transportOptions = useMemo(() => [
    { value: '', label: t(`${am}mcpServers.allTransportTypes`) },
    { value: 'stdio', label: 'stdio' },
    { value: 'sse', label: 'sse' },
    { value: 'http', label: 'http' },
  ], [t]);

  const handleDelete = (row: McpServerSummaryView) => {
    setDeletingItem(row);
  };

  const columns = useMemo<TableColumn<McpServerSummaryView>[]>(
    () => [
      {
        key: 'name',
        header: t(`${am}mcpServers.columns.name`),
        render: (row) => <span className="font-medium text-text">{row.name}</span>,
      },
      {
        key: 'transport',
        header: t(`${am}mcpServers.columns.transport`),
        render: (row) => <Badge tone={transportTone[row.transport]}>{row.transport}</Badge>,
      },
      {
        key: 'endpoint',
        header: t(`${am}mcpServers.columns.endpoint`),
        render: (row) => (
          <span className="font-mono text-xs text-text-muted">
            {row.transport === 'stdio' ? row.command ?? '-' : row.endpoint ?? '-'}
          </span>
        ),
      },
      {
        key: 'tags',
        header: t(`${am}mcpServers.columns.tags`),
        render: (row) => (
          <div className="flex flex-wrap gap-1">
            {row.tags.length === 0 && <span className="text-text-muted">-</span>}
            {row.tags.slice(0, 3).map((tag) => (
              <Badge key={tag} tone="neutral">
                {tag}
              </Badge>
            ))}
          </div>
        ),
      },
      {
        key: 'isEnabled',
        header: t(`${am}mcpServers.columns.status`),
        render: (row) => (
          row.isEnabled
            ? <Badge tone="success">{t(`${am}mcpServers.statusEnabled`)}</Badge>
            : <Badge tone="neutral">{t(`${am}mcpServers.statusStopped`)}</Badge>
        ),
      },
      {
        key: 'createdAtUtc',
        header: t(`${am}mcpServers.columns.createdAt`),
        render: (row) => formatAdminDateTime(row.createdAtUtc, undefined, locale),
      },
      {
        key: 'actions',
        header: t(`${am}mcpServers.columns.actions`),
        render: (row) => (
          <RowActions actions={[
            { label: t(`${am}mcpServers.actions.edit`), onClick: () => setEditingName(row.name) },
            { label: t(`${am}mcpServers.actions.delete`), onClick: () => handleDelete(row), variant: 'danger', disabled: mutations.delete.isPending },
          ]} />
        ),
      },
    ],
    [locale, mutations.delete.isPending, t],
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
              onReset={() => setFilters(defaultMcpServerFilters)}
            >
              <ToolbarButton
                variant="primary"
                onClick={() => setCreateOpen(true)}
              >
                <Plus size={14} />
                {t(`${am}mcpServers.newServer`)}
              </ToolbarButton>
            </FilterToolbarActions>
          }
        >
          <SelectField
            label={t(`${am}mcpServers.filterTransport`)}
            fieldSize="compact"
            value={filters.transport}
            onChange={(e) => setFilters((current) => ({ ...current, transport: e.target.value as typeof current.transport, page: 1 }))}
          >
            {transportOptions.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </SelectField>
          <div className="filter-narrow">
            <TextField
              label={t(`${am}mcpServers.searchLabel`)}
              fieldSize="compact"
              value={filters.search}
              placeholder={t(`${am}mcpServers.searchPlaceholder`)}
              onChange={(e) => setFilters((current) => ({ ...current, search: e.target.value, page: 1 }))}
            />
          </div>
        </FilterToolbar>
      }
      error={
        (listQuery.isError || mutations.delete.isError) ? (
          <InlineMessage tone="error">
            {listQuery.isError ? mutations.getMutationMessage(listQuery.error) : mutations.getMutationMessage(mutations.delete.error)}
          </InlineMessage>
        ) : undefined
      }
      pagination={
        <Pagination
          page={filters.page}
          pageSize={filters.pageSize}
          totalCount={filteredRows.length}
          onChange={(page) => setFilters((current) => ({ ...current, page }))}
        />
      }
    >
      <DataTable
        columns={columns}
        rows={pagedRows}
        getRowKey={(row) => row.id}
        loading={listQuery.isLoading}
        emptyState={
          <EmptyState
            title={t(`${am}mcpServers.emptyTitle`)}
            action={<Button onClick={() => setCreateOpen(true)}>{t(`${am}common.createNow`)}</Button>}
          />
        }
      />
    </ManagementListFrame>

    <McpServerDrawer
      open={createOpen || editingName !== null}
      mode={editingName ? 'edit' : 'create'}
      initialValue={detailQuery.data ?? null}
      loading={detailQuery.isLoading || mutations.create.isPending || mutations.update.isPending}
      error={
        detailQuery.error
          ? mutations.getMutationMessage(detailQuery.error)
          : mutations.create.error
            ? mutations.getMutationMessage(mutations.create.error)
            : mutations.update.error
              ? mutations.getMutationMessage(mutations.update.error)
              : null
      }
      onClose={() => {
        setCreateOpen(false);
        setEditingName(null);
        mutations.create.reset();
        mutations.update.reset();
      }}
      onSubmit={async (model) => {
        if (editingName) {
          await mutations.update.mutateAsync({
            name: editingName,
            model: toMcpServerApiUpdateRequest(model),
          });
          setEditingName(null);
          toast(t('toast.updated'));
        } else {
          await mutations.create.mutateAsync(toMcpServerApiCreateRequest(model));
          setCreateOpen(false);
          toast(t('toast.created'));
        }
      }}
    />

    <ConfirmDialog
      open={deletingItem !== null}
      title={t(`${am}mcpServers.confirmDelete.title`)}
      description={t(`${am}mcpServers.confirmDelete.description`, { name: deletingItem?.name ?? '' })}
      confirmLabel={t(`${am}mcpServers.confirmDelete.label`)}
      loading={mutations.delete.isPending}
      error={mutations.delete.error ? mutations.getMutationMessage(mutations.delete.error) : null}
      onClose={() => {
        setDeletingItem(null);
        mutations.delete.reset();
      }}
      onConfirm={async () => {
        if (!deletingItem) return;
        await mutations.delete.mutateAsync(deletingItem.name);
        setDeletingItem(null);
        toast(t('toast.deleted'));
      }}
    />
    </>
  );
}
