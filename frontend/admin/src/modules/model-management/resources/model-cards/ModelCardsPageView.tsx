import { useMemo, useState } from 'react';
import { LayoutGrid, List, Pencil, Play, Plus, Trash2 } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { getEnabledFilterOptions, isEmbeddingModel, isTextModel } from '@/shared/config/catalogOptions';
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
import { Pagination } from '@/shared/ui/Pagination';
import { SelectField } from '@/shared/ui/FormFields';
import { SkeletonCards } from '@/shared/ui/Skeleton';
import type { LlmModelView } from '../../lib/contracts';
import { CardFeatureBadges } from '../../lib/features';
import { ModelDrawer } from './ModelCardDrawer';
import { ModelTestDialog } from './ModelTestDialog';
import { ModelEmbeddingTestDialog } from './ModelEmbeddingTestDialog';
import type { ModelsPageState } from './useModelCardsPageState';
import { defaultModelFilters } from './types';

type ViewMode = 'table' | 'grid';

/* ── View Mode Toggle ── */

function ViewModeToggle({ mode, onChange }: { mode: ViewMode; onChange: (m: ViewMode) => void }) {
  const { t } = useTranslation(['common', 'modelManagement']);
  const options: { value: ViewMode; icon: typeof List; label: string }[] = [
    { value: 'table', icon: List, label: t('modelManagement:models.page.viewModeTable') },
    { value: 'grid', icon: LayoutGrid, label: t('modelManagement:models.page.viewModeGrid') },
  ];

  return (
    <div className="flex overflow-hidden rounded-[2px] border border-border">
      {options.map(({ value, icon: Icon, label }) => (
        <button
          key={value}
          type="button"
          onClick={() => onChange(value)}
          title={label}
          className={`flex items-center gap-1.5 px-3 py-2 text-xs font-medium transition first:rounded-l-[2px] last:rounded-r-[2px] ${
            mode === value
              ? 'bg-primary/10 text-primary'
              : 'bg-surface text-text-muted hover:bg-background-subtle hover:text-text'
          }`}
        >
          <Icon size={15} />
          {label}
        </button>
      ))}
    </div>
  );
}

/* ── Table View ── */

function ModelTableView({ state }: { state: ModelsPageState }) {
  const navigate = useNavigate();
  const { t } = useTranslation(['common', 'modelManagement']);
  const columns = useMemo<TableColumn<LlmModelView>[]>(
    () => [
      {
        key: 'displayName',
        header: t('modelManagement:models.page.columns.displayName'),
        render: (row) => <span className="font-medium text-[var(--color-ink)]">{row.displayName}</span>,
      },
      {
        key: 'instances',
        header: t('modelManagement:models.page.columns.instances'),
        render: (row) => <Badge>{t('modelManagement:models.page.statsInstanceCount', { count: row.instanceCount ?? 0 })}</Badge>,
      },
      {
        key: 'bindings',
        header: t('modelManagement:models.page.columns.bindings'),
        render: (row) => <Badge>{t('modelManagement:models.page.statsBindingCount', { count: (row.bindings ?? []).length })}</Badge>,
      },
      {
        key: 'features',
        header: t('modelManagement:models.page.columns.features'),
        render: (row) => <CardFeatureBadges features={row.features ?? []} />,
      },
      {
        key: 'status',
        header: t('modelManagement:models.page.columns.status'),
        render: (row) => <Badge tone={row.isEnabled ? 'success' : 'warning'}>{row.isEnabled ? t('modelManagement:models.page.status.enabled') : t('modelManagement:models.page.status.disabled')}</Badge>,
      },
      {
        key: 'actions',
        header: t('modelManagement:models.page.columns.actions'),
        render: (row) => (
          <RowActions actions={[
            { label: t('modelManagement:models.page.rowActions.edit'), onClick: () => state.openEdit(row) },
            ...(isTextModel(row.type)
              ? [{ label: t('modelManagement:models.page.rowActions.test'), onClick: () => state.openTest(row) }]
              : []),
            ...(isEmbeddingModel(row.type)
              ? [{ label: t('modelManagement:models.page.rowActions.testEmbedding'), onClick: () => state.openEmbeddingTest(row) }]
              : []),
            { label: t('modelManagement:models.page.rowActions.detail'), onClick: () => navigate(`/model-management/models/${row.modelKey}`) },
            { label: t('modelManagement:models.page.rowActions.delete'), onClick: () => state.requestDelete(row), variant: 'danger' },
          ]} />
        ),
      },
    ],
    [navigate, state, t],
  );

  return (
    <DataTable
      columns={columns}
      rows={state.rows}
      getRowKey={(row) => row.modelKey}
      loading={state.listQuery.isLoading}
      emptyState={
        <EmptyState
          title={t('modelManagement:models.page.emptyTitle')}
          action={<Button onClick={state.openCreate}>{t('modelManagement:models.page.createModel')}</Button>}
        />
      }
    />
  );
}

/* ── Grid (Card) View ── */

function ModelGridView({ state }: { state: ModelsPageState }) {
  const navigate = useNavigate();
  const { t } = useTranslation(['common', 'modelManagement']);

  if (state.listQuery.isLoading) {
    return <SkeletonCards />;
  }

  if (!state.rows.length) {
    return (
      <EmptyState
        title={t('modelManagement:models.page.emptyTitle')}
        action={<Button onClick={state.openCreate}>{t('modelManagement:models.page.createModel')}</Button>}
      />
    );
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {state.rows.map((model) => {
        const instanceCount = model.instanceCount ?? 0;
        const healthyCount = model.healthyInstanceCount ?? 0;
        const bindings = model.bindings ?? [];
        const features = model.features ?? [];

        return (
          <div
            key={model.modelKey}
            onClick={() => navigate(`/model-management/models/${model.modelKey}`)}
            className="group flex cursor-pointer flex-col rounded-[2px] border border-border bg-surface/80 p-5 transition hover:border-primary/40 hover:"
          >
            {/* Header */}
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0 flex-1">
                <Link
                  to={`/model-management/models/${model.modelKey}`}
                  className="text-base font-semibold text-text hover:text-primary transition"
                >
                  {model.displayName}
                </Link>
                <div className="mt-1 text-xs text-text-muted">{model.modelName}</div>
              </div>
              <Badge tone={model.isEnabled ? 'success' : 'warning'}>{model.isEnabled ? t('modelManagement:models.page.status.enabled') : t('modelManagement:models.page.status.disabled')}</Badge>
            </div>

            {/* Description */}
            {model.description ? (
              <p className="mt-2.5 line-clamp-2 text-sm leading-relaxed text-text-secondary">{model.description}</p>
            ) : null}

            {/* Stats */}
            <div className="mt-4 flex flex-wrap gap-x-4 gap-y-1 text-xs text-text-muted">
              <span>{instanceCount > 0 ? t('modelManagement:models.page.statsInstanceCountWithHealth', { count: instanceCount, healthy: healthyCount }) : t('modelManagement:models.page.statsInstanceCount', { count: instanceCount })}</span>
              <span>{t('modelManagement:models.page.statsBindingCount', { count: bindings.length })}</span>
            </div>

            {/* Features */}
            <div className="mt-3">
              <CardFeatureBadges features={features} limit={4} />
            </div>

            {/* Footer */}
            <div className="mt-4 flex items-center justify-between gap-2 border-t border-border-subtle pt-3" onClick={(e) => e.stopPropagation()}>
              <span className="truncate text-xs text-text-muted">{model.modelKey}</span>
              <div className="flex shrink-0 gap-0.5">
                {isTextModel(model.type) && (
                  <button
                    type="button"
                    title={t('modelManagement:models.page.rowActions.test')}
                    onClick={() => state.openTest(model)}
                    className="flex h-7 w-7 items-center justify-center rounded-lg text-text-muted transition hover:bg-primary/10 hover:text-primary"
                  >
                    <Play size={14} />
                  </button>
                )}
                {isEmbeddingModel(model.type) && (
                  <button
                    type="button"
                    title={t('modelManagement:models.page.rowActions.testEmbedding')}
                    onClick={() => state.openEmbeddingTest(model)}
                    className="flex h-7 w-7 items-center justify-center rounded-lg text-text-muted transition hover:bg-primary/10 hover:text-primary"
                  >
                    <Play size={14} />
                  </button>
                )}
                <button
                  type="button"
                  title={t('modelManagement:models.page.rowActions.edit')}
                  onClick={() => state.openEdit(model)}
                  className="flex h-7 w-7 items-center justify-center rounded-lg text-text-muted transition hover:bg-primary/10 hover:text-primary"
                >
                  <Pencil size={14} />
                </button>
                <button
                  type="button"
                  title={t('modelManagement:models.page.rowActions.delete')}
                  onClick={() => state.requestDelete(model)}
                  className="flex h-7 w-7 items-center justify-center rounded-lg text-text-muted transition hover:bg-error/10 hover:text-error"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

/* ── Page View (orchestrator) ── */

export function ModelsPageView({ state }: { state: ModelsPageState }) {
  const [viewMode, setViewMode] = useState<ViewMode>('grid');
  const { t } = useTranslation(['common', 'modelManagement']);
  const enabledFilterOptions = getEnabledFilterOptions(t);

  return (
    <>
    <ManagementListFrame
        refreshing={state.listQuery.isFetching}
        toolbar={
          <FilterToolbar
            compact
            actions={
              <div className="flex items-center gap-2">
                <ViewModeToggle mode={viewMode} onChange={setViewMode} />
                <FilterToolbarActions
                  onRefresh={() => state.listQuery.refetch()}
                  refreshing={state.listQuery.isFetching}
                  onReset={state.resetFilters}
                >
                  <ToolbarButton variant="primary" onClick={state.openCreate}>
                    <Plus size={14} />
                    {t('modelManagement:models.page.newModel')}
                  </ToolbarButton>
                </FilterToolbarActions>
              </div>
            }
          >
            <SelectField
              label={t('modelManagement:models.page.filterFeature')}
              fieldSize="compact"
              value={state.filters.featureKey}
              onChange={(event) => state.patchFilters({ featureKey: event.target.value, page: 1 })}
            >
              <option value="">{state.featureOptionsQuery.isLoading ? t('modelManagement:models.drawer.features.loading') : t('modelManagement:models.page.filterFeatureAll')}</option>
              {(state.featureOptionsQuery.data ?? []).map((item) => (
                <option key={item.featureKey} value={item.featureKey}>
                  {item.displayName}
                </option>
              ))}
            </SelectField>
            <div className="filter-narrow">
              <SelectField
                label={t('modelManagement:models.page.filterEnableStatus')}
                fieldSize="compact"
                value={state.filters.isEnabled}
                onChange={(event) => state.patchFilters({ isEnabled: event.target.value as typeof defaultModelFilters.isEnabled, page: 1 })}
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
        error={state.listQuery.isError ? <InlineMessage tone="error">{state.listQuery.error instanceof Error ? state.listQuery.error.message : String(state.listQuery.error)}</InlineMessage> : undefined}
        pagination={
          <Pagination
            page={state.filters.page}
            pageSize={state.filters.pageSize}
            totalCount={state.listQuery.data?.totalCount ?? 0}
            onChange={state.setPage}
          />
        }
      >
        {viewMode === 'table' ? <ModelTableView state={state} /> : <ModelGridView state={state} />}
      </ManagementListFrame>

      <ModelDrawer
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
        title={t('modelManagement:models.deleteDialog.title')}
        description={state.deleteDialog.description}
        confirmLabel={t('modelManagement:models.deleteDialog.confirmLabel')}
        loading={state.deleteDialog.loading}
        onClose={state.deleteDialog.onClose}
        onConfirm={state.deleteDialog.onConfirm}
      />

      <ModelTestDialog
        open={state.testDialog.open}
        model={state.testDialog.model}
        onClose={state.testDialog.onClose}
      />

      <ModelEmbeddingTestDialog
        open={state.embeddingTestDialog.open}
        model={state.embeddingTestDialog.model}
        onClose={state.embeddingTestDialog.onClose}
      />
    </>
  );
}
