import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
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
import type { SkillSummaryView } from './types';
import {
  defaultSkillFilters,
  filterSkillRows,
  paginateRows,
  toSkillDefinitionApiCreateRequest,
  toSkillDefinitionApiUpdateRequest,
  toSkillListQuery,
} from './types';
import { useSkillList, useSkillMutations } from './hooks';
import { SkillDrawer } from './SkillDrawer';

const am = 'modules.agentManagement';

export function SkillsPage() {
  const { t } = useTranslation('common');
  const { toast } = useToast();
  const navigate = useNavigate();
  const [filters, setFilters] = useState(defaultSkillFilters);
  const [editingItem, setEditingItem] = useState<SkillSummaryView | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [deletingItem, setDeletingItem] = useState<SkillSummaryView | null>(null);

  const query = useMemo(() => toSkillListQuery(filters), [filters]);
  const listQuery = useSkillList(query);
  const mutations = useSkillMutations();
  const { locale } = useAdminLocale();
  const filteredRows = useMemo(() => filterSkillRows(listQuery.data ?? [], filters), [filters, listQuery.data]);
  const pagedRows = useMemo(
    () => paginateRows(filteredRows, filters.page, filters.pageSize),
    [filteredRows, filters.page, filters.pageSize],
  );

  const statusOptions = useMemo(() => [
    { value: '', label: t(`${am}.skills.allStatuses`) },
    { value: 'draft', label: t(`${am}.skills.statusDraft`) },
    { value: 'published', label: t(`${am}.skills.statusPublished`) },
  ], [t]);

  const columns = useMemo<TableColumn<SkillSummaryView>[]>(() => [
    {
      key: 'skillKey',
      header: t(`${am}.skills.columns.skillKey`),
      render: (row) => (
        <div>
          <div className="font-medium text-text">{row.displayName}</div>
          <div className="mt-1 font-mono text-xs text-text-muted">{row.skillKey}</div>
        </div>
      ),
    },
    {
      key: 'status',
      header: t(`${am}.skills.columns.status`),
      render: (row) => (
        <Badge tone={row.status === 'published' ? 'success' : 'warning'}>
          {row.status === 'published' ? t(`${am}.skills.statusPublished`) : t(`${am}.skills.statusDraft`)}
        </Badge>
      ),
    },
    {
      key: 'version',
      header: t(`${am}.skills.columns.version`),
      render: (row) => row.version,
    },
    {
      key: 'tags',
      header: t(`${am}.skills.columns.tags`),
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
      key: 'updatedAtUtc',
      header: t(`${am}.skills.columns.updatedAt`),
      render: (row) => formatAdminDateTime(row.updatedAtUtc ?? row.createdAtUtc, undefined, locale),
    },
    {
      key: 'actions',
      header: t(`${am}.skills.columns.actions`),
      render: (row) => (
        <RowActions actions={[
          { label: t(`${am}.skills.actions.edit`), onClick: () => setEditingItem(row) },
          { label: t(`${am}.skills.actions.workbench`), onClick: () => navigate(`/agent-management/skills/${row.skillKey}/workbench`) },
          ...(row.status === 'draft' ? [{ label: t(`${am}.skills.actions.publish`), onClick: () => mutations.publish.mutate(row.skillKey), disabled: mutations.publish.isPending }] : []),
          { label: t(`${am}.skills.actions.delete`), onClick: () => setDeletingItem(row), variant: 'danger' as const, disabled: mutations.remove.isPending },
        ]} />
      ),
    },
  ], [locale, mutations.publish, mutations.remove.isPending, navigate, t]);

  const actionError = mutations.publish.error
    ? mutations.getMutationMessage(mutations.publish.error)
    : mutations.remove.error
      ? mutations.getMutationMessage(mutations.remove.error)
      : null;

  return (
    <>
      <ManagementListFrame
        refreshing={listQuery.isFetching}
        toolbar={(
          <FilterToolbar
            compact
            actions={(
              <FilterToolbarActions
                onRefresh={() => listQuery.refetch()}
                refreshing={listQuery.isFetching}
                onReset={() => setFilters(defaultSkillFilters)}
              >
                <ToolbarButton
                  variant="primary"
                  onClick={() => setCreateOpen(true)}
                >
                  <Plus size={14} />
                  {t(`${am}.skills.newSkill`)}
                </ToolbarButton>
              </FilterToolbarActions>
            )}
          >
            <SelectField
              label={t(`${am}.skills.filterStatus`)}
              fieldSize="compact"
              value={filters.status}
              onChange={(e) => setFilters((current) => ({ ...current, status: e.target.value as typeof current.status, page: 1 }))}
            >
              {statusOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </SelectField>
            <div className="filter-narrow">
              <TextField
                label={t(`${am}.skills.filterTag`)}
                fieldSize="compact"
                value={filters.tag}
                placeholder={t(`${am}.skills.filterTagPlaceholder`)}
                onChange={(e) => setFilters((current) => ({ ...current, tag: e.target.value, page: 1 }))}
              />
            </div>
            <div className="filter-narrow">
              <TextField
                label={t(`${am}.skills.filterSearch`)}
                fieldSize="compact"
                value={filters.search}
                placeholder={t(`${am}.skills.filterSearchPlaceholder`)}
                onChange={(e) => setFilters((current) => ({ ...current, search: e.target.value, page: 1 }))}
              />
            </div>
          </FilterToolbar>
        )}
        error={
          listQuery.isError || actionError ? (
            <InlineMessage tone="error">
              {listQuery.isError ? mutations.getMutationMessage(listQuery.error) : actionError}
            </InlineMessage>
          ) : undefined
        }
        pagination={(
          <Pagination
            page={filters.page}
            pageSize={filters.pageSize}
            totalCount={filteredRows.length}
            onChange={(page) => setFilters((current) => ({ ...current, page }))}
          />
        )}
      >
          <DataTable
            columns={columns}
            rows={pagedRows}
            getRowKey={(row) => row.id}
            loading={listQuery.isLoading}
            emptyState={
              <EmptyState
                title={t(`${am}.skills.emptyTitle`)}
                description={t(`${am}.skills.emptyDescription`)}
                action={<Button onClick={() => setCreateOpen(true)}>{t(`${am}.common.createNow`)}</Button>}
              />
            }
          />
      </ManagementListFrame>

      <SkillDrawer
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
            await mutations.update.mutateAsync({
              skillKey: editingItem.skillKey,
              model: toSkillDefinitionApiUpdateRequest(model),
            });
            setEditingItem(null);
            toast(t('toast.updated'));
          } else {
            await mutations.create.mutateAsync(toSkillDefinitionApiCreateRequest(model));
            setCreateOpen(false);
            toast(t('toast.created'));
          }
        }}
      />

      <ConfirmDialog
        open={deletingItem !== null}
        title={t(`${am}.skills.confirmDelete.title`)}
        description={t(`${am}.skills.confirmDelete.description`, { name: deletingItem?.displayName ?? '' })}
        confirmLabel={t(`${am}.skills.confirmDelete.label`)}
        loading={mutations.remove.isPending}
        error={mutations.remove.error ? mutations.getMutationMessage(mutations.remove.error) : null}
        onClose={() => {
          setDeletingItem(null);
          mutations.remove.reset();
        }}
        onConfirm={async () => {
          if (!deletingItem) return;
          await mutations.remove.mutateAsync(deletingItem.skillKey);
          setDeletingItem(null);
          toast(t('toast.deleted'));
        }}
      />
    </>
  );
}
