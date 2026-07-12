import { useCallback, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Plus, RefreshCw } from 'lucide-react';
import { Badge } from '@/shared/ui/Badge';
import { Button } from '@/shared/ui/Button';
import { RowActions } from '@/shared/ui/RowActions';
import { ToolbarButton } from '@/shared/ui/ToolbarButton';
import { useToast } from '@/shared/ui/Toast';
import { DataTable, type TableColumn } from '@/shared/ui/DataTable';
import { EmptyState } from '@/shared/ui/EmptyState';
import { FilterToolbar } from '@/shared/ui/FilterToolbar';
import { InlineMessage } from '@/shared/ui/InlineMessage';
import { ManagementListFrame } from '@/shared/ui/ManagementListFrame';
import { Pagination } from '@/shared/ui/Pagination';
import { SelectField, TextField } from '@/shared/ui/FormFields';
import { formatAdminDateTime } from '@/shared/i18n/formatters';
import { useAdminLocale } from '@/shared/i18n/useAdminLocale';
import type { ToolSummaryView } from './types';
import {
  defaultToolFilters,
  filterToolRows,
  paginateRows,
  toToolListQuery,
} from './types';
import { useToolDefinitionList, useToolDefinitionMutations } from './hooks';
import { ToolDrawer } from './ToolDrawer';

const am = 'agentManagement:';

function SourceTypeBadge({ type }: { type: string }) {
  return (
    <Badge tone="neutral">
      {type === 'builtin' ? 'Built-in' : 'HTTP External'}
    </Badge>
  );
}

function StatusBadge({ status }: { status: string }) {
  const { t } = useTranslation(['common', 'agentManagement']);
  const tone = status === 'active' ? 'success' : status === 'deprecated' ? 'warning' : 'danger';
  return (
    <Badge tone={tone}>
      {t(`${am}tools.status${status.charAt(0).toUpperCase() + status.slice(1)}`, { defaultValue: status })}
    </Badge>
  );
}

export function ToolsPage() {
  const { t } = useTranslation(['common', 'agentManagement']);
  const { toast } = useToast();
  const [filters, setFilters] = useState(defaultToolFilters);
  const [editingTool, setEditingTool] = useState<ToolSummaryView | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [mutationError, setMutationError] = useState<string | null>(null);

  const query = useMemo(() => toToolListQuery(filters), [filters]);
  const listQuery = useToolDefinitionList(query);
  const mutations = useToolDefinitionMutations();
  const { locale } = useAdminLocale();
  const filteredRows = useMemo(
    () => filterToolRows(listQuery.data ?? [], filters),
    [filters, listQuery.data],
  );
  const pagedRows = useMemo(
    () => paginateRows(filteredRows, filters.page, filters.pageSize),
    [filteredRows, filters.page, filters.pageSize],
  );

  const sourceTypeOptions = useMemo(() => [
    { value: '', label: t(`${am}tools.allTypes`) },
    { value: 'builtin', label: 'Builtin' },
    { value: 'http_external', label: 'HTTP External' },
  ], [t]);

  const statusOptions = useMemo(() => [
    { value: '', label: t(`${am}tools.allStatuses`) },
    { value: 'active', label: t(`${am}tools.statusActive`) },
    { value: 'deprecated', label: t(`${am}tools.statusDeprecated`) },
    { value: 'disabled', label: t(`${am}tools.statusDisabled`) },
  ], [t]);

  const columns = useMemo<TableColumn<ToolSummaryView>[]>(
    () => [
      {
        key: 'toolName',
        header: t(`${am}tools.columns.toolName`),
        render: (row) => (
          <div>
            <div className="font-medium text-text">{row.displayName}</div>
            <div className="mt-1 font-mono text-xs text-text-muted">{row.toolName}</div>
          </div>
        ),
      },
      {
        key: 'sourceType',
        header: t(`${am}tools.columns.type`),
        render: (row) => <SourceTypeBadge type={row.sourceType} />,
      },
      {
        key: 'status',
        header: t(`${am}tools.columns.status`),
        render: (row) => <StatusBadge status={row.status} />,
      },
      {
        key: 'tags',
        header: t(`${am}tools.columns.tags`),
        render: (row) => (
          <div className="flex flex-wrap gap-1">
            {row.tags.map((tag) => (
              <Badge key={tag} tone="neutral">{tag}</Badge>
            ))}
          </div>
        ),
      },
      {
        key: 'timeoutSeconds',
        header: t(`${am}tools.columns.timeout`),
        render: (row) => <span className="text-sm text-text-secondary">{row.timeoutSeconds}s</span>,
      },
      {
        key: 'updatedAtUtc',
        header: t(`${am}tools.columns.updatedAt`),
        render: (row) => (
          <span className="text-sm text-text-muted">{formatAdminDateTime(row.updatedAtUtc ?? row.createdAtUtc, undefined, locale)}</span>
        ),
      },
      {
        key: 'actions',
        header: '',
        render: (row) => (
          <RowActions actions={[
            {
              label: row.sourceType === 'builtin' ? t(`${am}tools.actions.view`) : t(`${am}tools.actions.edit`),
              onClick: () => { setEditingTool(row); setDrawerOpen(true); setMutationError(null); },
            },
            ...(row.sourceType === 'http_external' && row.status === 'active' ? [{
              label: t(`${am}tools.actions.disable`),
              onClick: async () => {
                if (!confirm(t(`${am}tools.confirmDisable`, { name: row.displayName }))) return;
                try {
                  await mutations.disable.mutateAsync(row.toolName);
                  toast(t('toast.updated'));
                } catch (e) {
                  setMutationError(mutations.getMutationMessage(e));
                }
              },
              variant: 'danger' as const,
            }] : []),
          ]} />
        ),
      },
    ],
    [locale, mutations, t],
  );

  const handleCreate = async (draft: Parameters<typeof mutations.create.mutateAsync>[0]) => {
    setMutationError(null);
    try {
      await mutations.create.mutateAsync(draft);
      setDrawerOpen(false);
      toast(t('toast.created'));
    } catch (e) {
      setMutationError(mutations.getMutationMessage(e));
    }
  };

  const handleUpdate = async (
    toolName: string,
    draft: Parameters<typeof mutations.update.mutateAsync>[0]['model'],
  ) => {
    setMutationError(null);
    try {
      await mutations.update.mutateAsync({ toolName, model: draft });
      setDrawerOpen(false);
      toast(t('toast.updated'));
    } catch (e) {
      setMutationError(mutations.getMutationMessage(e));
    }
  };

  const handleSync = useCallback(async () => {
    setMutationError(null);
    try {
      const result = await mutations.sync.mutateAsync();
      toast(t(`${am}tools.syncResult`, { count: result.synced }));
    } catch (e) {
      setMutationError(mutations.getMutationMessage(e));
    }
  }, [mutations, t, toast]);

  return (
    <>
      {mutationError && (
        <InlineMessage tone="error">
          {mutationError}
        </InlineMessage>
      )}

      <ManagementListFrame
        toolbar={
          <FilterToolbar
            compact
            actions={
              <div className="flex gap-2">
                <Button
                  variant="secondary"
                  onClick={() => listQuery.refetch()}
                  disabled={listQuery.isFetching}
                >
                  <RefreshCw size={14} className="mr-1" />
                  {t(`${am}tools.refreshButton`)}
                </Button>
                <ToolbarButton
                  variant="secondary"
                  onClick={handleSync}
                  disabled={mutations.sync.isPending}
                >
                  <RefreshCw size={14} />
                  {t(`${am}tools.syncButton`)}
                </ToolbarButton>
                <ToolbarButton
                  variant="primary"
                  onClick={() => {
                    setEditingTool(null);
                    setDrawerOpen(true);
                    setMutationError(null);
                  }}
                >
                  <Plus size={14} />
                  {t(`${am}tools.newToolButton`)}
                </ToolbarButton>
              </div>
            }
          >
            <SelectField
              label={t(`${am}tools.filterType`)}
              fieldSize="compact"
              value={filters.sourceType}
              onChange={(e) =>
                setFilters((f) => ({
                  ...f,
                  sourceType: e.target.value as typeof f.sourceType,
                  page: 1,
                }))
              }
            >
              {sourceTypeOptions.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </SelectField>

            <SelectField
              label={t(`${am}tools.filterStatus`)}
              fieldSize="compact"
              value={filters.status}
              onChange={(e) =>
                setFilters((f) => ({
                  ...f,
                  status: e.target.value as typeof f.status,
                  page: 1,
                }))
              }
            >
              {statusOptions.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </SelectField>

            <div className="filter-narrow">
              <TextField
                label={t(`${am}tools.filterSearch`)}
                fieldSize="compact"
                placeholder={t(`${am}tools.filterSearchPlaceholder`)}
                value={filters.search}
                onChange={(e) =>
                  setFilters((f) => ({ ...f, search: e.target.value, page: 1 }))
                }
              />
            </div>
          </FilterToolbar>
        }
        error={
          listQuery.isError ? (
            <InlineMessage tone="error">{t(`${am}tools.loadError`)}</InlineMessage>
          ) : undefined
        }
        pagination={
          filteredRows.length > 0 ? (
            <Pagination
              page={filters.page}
              pageSize={filters.pageSize}
              totalCount={filteredRows.length}
              onChange={(p) => setFilters((f) => ({ ...f, page: p }))}
            />
          ) : undefined
        }
      >
        {listQuery.isLoading ? (
          <p className="text-sm text-text-muted">{t(`${am}tools.loadingText`)}</p>
        ) : filteredRows.length === 0 ? (
          <EmptyState title={t(`${am}tools.emptyTitle`)} description={t(`${am}tools.emptyDescription`)} />
        ) : (
          <DataTable
            columns={columns}
            rows={pagedRows}
            getRowKey={(row) => row.id}
            emptyState={<EmptyState title={t(`${am}tools.emptyTitle`)} description={t(`${am}tools.emptyDescription`)} />}
          />
        )}
      </ManagementListFrame>

      <ToolDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        editingTool={editingTool}
        onCreateSubmit={handleCreate}
        onUpdateSubmit={handleUpdate}
        errorMessage={mutationError ?? undefined}
        loading={mutations.create.isPending || mutations.update.isPending}
      />
    </>
  );
}
