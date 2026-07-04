import { useMemo, useState } from 'react';
import { LayoutGrid, List } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Badge } from '@/shared/ui/Badge';
import { FilterToolbarActions } from '@/shared/ui/FilterToolbarActions';
import { DataTable, type TableColumn } from '@/shared/ui/DataTable';
import { FormModal } from '@/shared/ui/FormModal';
import { EmptyState } from '@/shared/ui/EmptyState';
import { InlineMessage } from '@/shared/ui/InlineMessage';
import { FilterToolbar } from '@/shared/ui/FilterToolbar';
import { ManagementListFrame } from '@/shared/ui/ManagementListFrame';
import { MetricStrip } from '@/shared/ui/MetricStrip';
import { Pagination } from '@/shared/ui/Pagination';
import { DateField, SelectField } from '@/shared/ui/FormFields';
import { SkeletonCards, SkeletonRows } from '@/shared/ui/Skeleton';
import { useAdminLocale } from '@/shared/i18n/useAdminLocale';
import type { ModelUsageSummary, UsageRequestRow } from '../../lib/contracts';
import { formatCompact, formatDateTime, formatLatency, formatNumber } from '../../lib/formatters';
import { ModelSummaryCard } from '../../components/ModelSummaryCard';
import type { UsagePageState } from './useUsagePageState';

// ---------------------------------------------------------------------------
// View mode toggle
// ---------------------------------------------------------------------------

type ViewMode = 'table' | 'grid';

function ViewModeToggle({ mode, onChange }: { mode: ViewMode; onChange: (m: ViewMode) => void }) {
  const { t } = useTranslation('common');
  const options: { value: ViewMode; icon: typeof List; label: string }[] = [
    { value: 'table', icon: List, label: t('modules.modelMonitoring.usage.viewToggle.list') },
    { value: 'grid', icon: LayoutGrid, label: t('modules.modelMonitoring.usage.viewToggle.card') },
  ];
  return (
    <div className="flex overflow-hidden rounded-[2px] border border-border">
      {options.map(({ value, icon: Icon, label }) => (
        <button
          key={value}
          type="button"
          onClick={() => onChange(value)}
          title={label}
          className={`flex items-center gap-1.5 px-3 py-2 text-xs font-medium transition ${
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

// ---------------------------------------------------------------------------
// Grid view (card layout)
// ---------------------------------------------------------------------------

function GridView({ state }: { state: UsagePageState }) {
  const { t } = useTranslation('common');
  const { overviewQuery, overview } = state;

  if (overviewQuery.isLoading) return <SkeletonCards />;
  if (overviewQuery.isError) {
    return (
      <InlineMessage tone="error">
        {overviewQuery.error?.message ?? t('modules.modelMonitoring.usage.grid.error')}
      </InlineMessage>
    );
  }
  if (!overview.modelSummaries.length) {
    return (
      <EmptyState
        title={t('modules.modelMonitoring.usage.grid.empty.title')}
        description={t('modules.modelMonitoring.usage.grid.empty.description')}
      />
    );
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {overview.modelSummaries.map((card) => (
        <ModelSummaryCard
          key={card.modelKey}
          card={card}
          onClick={state.openDetail}
        />
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Detail drawer
// ---------------------------------------------------------------------------

function UsageDetailDrawer({ state }: { state: UsagePageState }) {
  const { t } = useTranslation('common');
  const { detail } = state;
  const cardName = state.overview.modelSummaries.find((row) => row.modelKey === detail.modelKey)?.displayName ?? detail.modelKey;

  const columns = useMemo<TableColumn<UsageRequestRow>[]>(
    () => [
      { key: 'startedAt', header: t('modules.modelMonitoring.usage.detail.table.headers.startedAt'), render: (row) => formatDateTime(row.startedAtUtc) },
      { key: 'requestId', header: t('modules.modelMonitoring.usage.detail.table.headers.requestId'), render: (row) => <span className="font-mono text-xs text-text">{row.requestId}</span> },
      { key: 'capability', header: t('modules.modelMonitoring.usage.detail.table.headers.capability'), render: (row) => row.capability },
      { key: 'attempts', header: t('modules.modelMonitoring.usage.detail.table.headers.attempts'), render: (row) => formatNumber(row.attemptCount) },
      { key: 'inputTokens', header: t('modules.modelMonitoring.usage.detail.table.headers.inputTokens'), render: (row) => formatCompact(row.totalInputTokens) },
      { key: 'outputTokens', header: t('modules.modelMonitoring.usage.detail.table.headers.outputTokens'), render: (row) => formatCompact(row.totalOutputTokens) },
      { key: 'latency', header: t('modules.modelMonitoring.usage.detail.table.headers.latency'), render: (row) => formatLatency(row.totalDurationMs) },
      {
        key: 'status',
        header: t('modules.modelMonitoring.usage.detail.table.headers.result'),
        render: (row) =>
          row.success ? (
            <Badge tone="success">{t('modules.modelMonitoring.usage.detail.table.status.success')}</Badge>
          ) : (
            <Badge tone="danger">{row.errorCode ?? t('modules.modelMonitoring.usage.detail.table.status.failure')}</Badge>
          ),
      },
    ],
    [t],
  );

  return (
    <FormModal open={detail.open} onClose={detail.onClose} title={`${cardName} — ${t('modules.modelMonitoring.usage.detail.drawerTitle')}`}>
      <div className="space-y-4">
        <FilterToolbar compact>
          <DateField
            label={t('modules.modelMonitoring.usage.detail.filters.startTime')}
            fieldSize="compact"
            value={detail.filters.fromDate}
            onChange={(nextValue) => detail.patchFilters({ fromDate: nextValue, page: 1 })}
          />
          <DateField
            label={t('modules.modelMonitoring.usage.detail.filters.endTime')}
            fieldSize="compact"
            value={detail.filters.toDate}
            onChange={(nextValue) => detail.patchFilters({ toDate: nextValue, page: 1 })}
          />
        </FilterToolbar>

        <DataTable
          columns={columns}
          rows={detail.rows}
          getRowKey={(row) => `${row.requestId}-${row.startedAtUtc}`}
          loading={detail.query.isLoading}
          emptyState={
            <EmptyState
              title={t('modules.modelMonitoring.usage.detail.empty.title')}
              description={t('modules.modelMonitoring.usage.detail.empty.description')}
            />
          }
        />

        <Pagination
          page={detail.filters.page}
          pageSize={detail.filters.pageSize}
          totalCount={detail.query.data?.totalCount ?? 0}
          onChange={detail.setPage}
        />
      </div>
    </FormModal>
  );
}

// ---------------------------------------------------------------------------
// Main view
// ---------------------------------------------------------------------------

export function UsagePageView({ state }: { state: UsagePageState }) {
  useAdminLocale();
  const { t } = useTranslation('common');
  const [viewMode, setViewMode] = useState<ViewMode>('table');

  const columns = useMemo<TableColumn<ModelUsageSummary>[]>(
    () => [
      {
        key: 'displayName',
        header: t('modules.modelMonitoring.usage.table.headers.modelName'),
        render: (row) => (
          <button type="button" className="font-medium text-primary hover:underline" onClick={() => state.openDetail(row.modelKey)}>
            {row.displayName}
          </button>
        ),
      },
      { key: 'requests', header: t('modules.modelMonitoring.usage.table.headers.requests'), render: (row) => formatCompact(row.totalRequests) },
      { key: 'inputTokens', header: t('modules.modelMonitoring.usage.table.headers.inputTokens'), render: (row) => formatCompact(row.totalInputTokens) },
      { key: 'outputTokens', header: t('modules.modelMonitoring.usage.table.headers.outputTokens'), render: (row) => formatCompact(row.totalOutputTokens) },
      { key: 'latency', header: t('modules.modelMonitoring.usage.table.headers.averageLatency'), render: (row) => formatLatency(row.averageLatencyMs) },
    ],
    [state.openDetail, t],
  );

  const filterToolbar = (
    <FilterToolbar
      compact
      actions={
        <div className="flex gap-2">
          <ViewModeToggle mode={viewMode} onChange={setViewMode} />
          <FilterToolbarActions
            onRefresh={() => {
              state.overviewQuery.refetch();
            }}
            refreshing={state.overviewQuery.isFetching}
            onReset={state.resetFilters}
          />
        </div>
      }
    >
      <SelectField
        label={t('modules.modelMonitoring.usage.filters.model')}
        fieldSize="compact"
        value={state.filters.modelKey}
        onChange={(e) => state.patchFilters({ modelKey: e.target.value, page: 1 })}
      >
        <option value="">
          {state.modelOptionsQuery.isLoading
            ? t('modules.modelMonitoring.usage.filters.loading')
            : t('modules.modelMonitoring.usage.filters.allModels')}
        </option>
        {(state.modelOptionsQuery.data ?? []).map((item) => (
          <option key={item.modelKey} value={item.modelKey}>
            {item.displayName}
          </option>
        ))}
      </SelectField>
      <DateField
        label={t('modules.modelMonitoring.usage.filters.startTime')}
        fieldSize="compact"
        value={state.filters.fromDate}
        onChange={(nextValue) => state.patchFilters({ fromDate: nextValue, page: 1 })}
      />
      <DateField
        label={t('modules.modelMonitoring.usage.filters.endTime')}
        fieldSize="compact"
        value={state.filters.toDate}
        onChange={(nextValue) => state.patchFilters({ toDate: nextValue, page: 1 })}
      />
    </FilterToolbar>
  );

  const isLoading = state.overviewQuery.isLoading;

  return (
    <>
      <div className="pb-4">
        <MetricStrip
          items={[
            { label: t('modules.modelMonitoring.usage.metrics.totalRequests'), value: formatCompact(state.overview.totalRequests), accent: 'blue' },
            { label: t('modules.modelMonitoring.usage.metrics.totalTokens'), value: formatCompact(state.overview.totalTokens), accent: 'violet' },
            { label: t('modules.modelMonitoring.usage.metrics.averageLatency'), value: formatLatency(state.overview.averageLatencyMs), accent: 'teal' },
            { label: t('modules.modelMonitoring.usage.metrics.totalErrors'), value: formatCompact(state.overview.totalErrors), accent: 'amber' },
          ]}
        />
      </div>

      {viewMode === 'table' ? (
        <ManagementListFrame
          refreshing={state.overviewQuery.isFetching}
          toolbar={filterToolbar}
          error={
            state.overviewQuery.isError ? (
              <InlineMessage tone="error">
                {state.overviewQuery.error?.message ?? t('modules.modelMonitoring.usage.error')}
              </InlineMessage>
            ) : undefined
          }
          pagination={
            <Pagination
              page={state.filters.page}
              pageSize={state.filters.pageSize}
              totalCount={state.overview.modelSummaries.length}
              onChange={state.setPage}
            />
          }
        >
          {isLoading ? (
            <SkeletonRows columns={5} />
          ) : (
            <DataTable
              columns={columns}
              rows={state.rows}
              getRowKey={(row) => row.modelKey}
              loading={false}
              emptyState={
                <EmptyState
                  title={t('modules.modelMonitoring.usage.empty.title')}
                  description={t('modules.modelMonitoring.usage.empty.description')}
                />
              }
            />
          )}
        </ManagementListFrame>
      ) : (
        <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-hidden">
          <div>{filterToolbar}</div>
          <div className="min-h-0 flex-1 overflow-y-auto pb-6">
            <GridView state={state} />
          </div>
        </div>
      )}

      <UsageDetailDrawer state={state} />
    </>
  );
}
