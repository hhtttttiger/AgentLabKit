import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Plus } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Badge } from '@/shared/ui/Badge';
import { Button } from '@/shared/ui/Button';
import { ToolbarButton } from '@/shared/ui/ToolbarButton';
import { useToast } from '@/shared/ui/Toast';
import { DataTable, type TableColumn } from '@/shared/ui/DataTable';
import { EmptyState } from '@/shared/ui/EmptyState';
import { FilterToolbar } from '@/shared/ui/FilterToolbar';
import { FilterToolbarActions } from '@/shared/ui/FilterToolbarActions';
import { InlineMessage } from '@/shared/ui/InlineMessage';
import { ManagementListFrame } from '@/shared/ui/ManagementListFrame';
import { Pagination } from '@/shared/ui/Pagination';
import { RowActions } from '@/shared/ui/RowActions';
import { SelectField } from '@/shared/ui/FormFields';
import { formatAdminDateTime } from '@/shared/i18n/formatters';
import { useAdminLocale } from '@/shared/i18n/useAdminLocale';
import type { AgentSummaryView } from '../../lib/contracts';
import { AgentDrawer } from './AgentDrawer';
import { defaultAgentFilters, toAgentListQuery } from './types';
import { useAgent, useAgentList, useAgentMutations } from './hooks';

const statusTone: Record<string, 'success' | 'warning' | 'neutral'> = {
  draft: 'warning',
  published: 'success',
  disabled: 'neutral',
};

export function AgentsPage() {
  const { t } = useTranslation(['common', 'agentManagement']);
  const { toast } = useToast();
  const navigate = useNavigate();
  const [filters, setFilters] = useState(defaultAgentFilters);
  const [editingAgentKey, setEditingAgentKey] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);

  const query = useMemo(() => toAgentListQuery(filters), [filters]);
  const listQuery = useAgentList(query);
  const editingAgentQuery = useAgent(editingAgentKey ?? '');
  const mutations = useAgentMutations();
  const rows = listQuery.data?.items ?? [];
  const isEditOpen = editingAgentKey !== null;
  const { locale } = useAdminLocale();

  const am = 'agentManagement';

  const statusOptions = useMemo(() => [
    { value: '', label: t(`${am}.status.allStatuses`) },
    { value: 'draft', label: t(`${am}.status.draft`) },
    { value: 'published', label: t(`${am}.status.published`) },
    { value: 'disabled', label: t(`${am}.status.disabled`) },
  ], [t, am]);

  const columns = useMemo<TableColumn<AgentSummaryView>[]>(
    () => [
      {
        key: 'agentKey',
        header: 'Agent',
        render: (row) => (
          <div>
            <div className="font-medium text-text">{row.displayName}</div>
            <div className="mt-1 font-mono text-xs text-text-muted">{row.agentKey}</div>
          </div>
        ),
      },
      {
        key: 'status',
        header: t(`${am}.agents.columns.status`),
        render: (row) => (
          <Badge tone={statusTone[row.status] ?? 'neutral'}>
            {t(`${am}.status.${row.status}`, { defaultValue: row.status })}
          </Badge>
        ),
      },
      {
        key: 'publishedVersion',
        header: t(`${am}.agents.columns.publishedVersion`),
        render: (row) =>
          row.publishedVersionNumber !== null ? (
            <span className="font-mono text-sm">v{row.publishedVersionNumber}</span>
          ) : (
            <span className="text-text-muted">-</span>
          ),
      },
      {
        key: 'createdAtUtc',
        header: t(`${am}.agents.columns.createdAt`),
        render: (row) => formatAdminDateTime(row.createdAtUtc, undefined, locale),
      },
      {
        key: 'actions',
        header: t(`${am}.agents.columns.actions`),
        render: (row) => (
          <RowActions
            actions={[
              {
                label: t(`${am}.agents.actions.manageVersions`),
                onClick: () => navigate(`${row.agentKey}?tab=versions`),
              },
              {
                label: t(`${am}.agents.actions.editDefinition`),
                onClick: () => setEditingAgentKey(row.agentKey),
              },
            ]}
          />
        ),
      },
    ],
    [locale, navigate, t, am],
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
                onReset={() => setFilters(defaultAgentFilters)}
              >
                <ToolbarButton
                  variant="primary"
                  onClick={() => setCreateOpen(true)}
                >
                  <Plus size={14} />
                  {t(`${am}.agents.page.newAgent`)}
                </ToolbarButton>
              </FilterToolbarActions>
            }
          >
            <SelectField
              label={t(`${am}.agents.columns.status`)}
              fieldSize="compact"
              value={filters.status}
              onChange={(e) =>
                setFilters((c) => ({ ...c, status: e.target.value as typeof c.status, page: 1 }))
              }
            >
              {statusOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </SelectField>
          </FilterToolbar>
        }
        error={
          listQuery.isError ? (
            <InlineMessage tone="error">
              {mutations.getMutationMessage(listQuery.error)}
            </InlineMessage>
          ) : undefined
        }
        pagination={
          <Pagination
            page={filters.page}
            pageSize={filters.pageSize}
            totalCount={listQuery.data?.totalCount ?? 0}
            onChange={(page) => setFilters((c) => ({ ...c, page }))}
          />
        }
      >
        <DataTable
          columns={columns}
          rows={rows}
          getRowKey={(row) => row.agentKey}
          loading={listQuery.isLoading}
          emptyState={
            <EmptyState
              title={t(`${am}.agents.page.emptyTitle`)}
              action={<Button onClick={() => setCreateOpen(true)}>{t(`${am}.common.createNow`)}</Button>}
            />
          }
        />
      </ManagementListFrame>

      <AgentDrawer
        open={createOpen || isEditOpen}
        mode={isEditOpen ? 'edit' : 'create'}
        initialValue={isEditOpen ? (editingAgentQuery.data ?? null) : null}
        loading={
          mutations.create.isPending ||
          mutations.update.isPending ||
          (isEditOpen && editingAgentQuery.isLoading)
        }
        error={
          isEditOpen && editingAgentQuery.isError
            ? mutations.getMutationMessage(editingAgentQuery.error)
            : mutations.create.error
              ? mutations.getMutationMessage(mutations.create.error)
              : mutations.update.error
                ? mutations.getMutationMessage(mutations.update.error)
                : null
        }
        onClose={() => {
          setCreateOpen(false);
          setEditingAgentKey(null);
          mutations.create.reset();
          mutations.update.reset();
        }}
        onSubmit={async (model) => {
          if (editingAgentKey) {
            const current = editingAgentQuery.data;
            if (!current) {
              return;
            }

            await mutations.update.mutateAsync({
              agentKey: editingAgentKey,
              model: {
                displayName: model.displayName,
                description: model.description,
                tags: model.tags,
                metadata: model.metadata,
                rowVersion: current.rowVersion,
              },
            });
            setEditingAgentKey(null);
            toast(t('toast.updated'));
            return;
          }

          await mutations.create.mutateAsync(model);
          setCreateOpen(false);
          toast(t('toast.created'));
        }}
      />
    </>
  );
}
