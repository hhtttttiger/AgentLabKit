import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Copy, Search } from 'lucide-react';
import { Badge } from '@/shared/ui/Badge';
import { DataTable, type TableColumn } from '@/shared/ui/DataTable';
import { EmptyState } from '@/shared/ui/EmptyState';
import { InlineMessage } from '@/shared/ui/InlineMessage';
import { Pagination } from '@/shared/ui/Pagination';
import { RowActions } from '@/shared/ui/RowActions';
import { formatAdminDateTime } from '@/shared/i18n/formatters';
import { useAdminLocale } from '@/shared/i18n/useAdminLocale';
import type { ExecutionAuditView } from '../../lib/contracts';
import { AuditDetailDrawer } from './AuditDetailDrawer';
import { defaultAuditFilters, toAuditListQuery } from './types';
import { useAuditList } from './hooks';

const am = 'agentManagement:';

const statusTone: Record<string, 'success' | 'danger' | 'warning' | 'neutral'> = {
  success: 'success',
  completed: 'success',
  error: 'danger',
  failed: 'danger',
  timeout: 'warning',
};

function copyToClipboard(text: string) {
  void navigator.clipboard.writeText(text);
}

export function AuditList({ agentKey }: { agentKey: string }) {
  const { t } = useTranslation(['common', 'agentManagement']);
  const [filters, setFilters] = useState(defaultAuditFilters);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);

  const [runIdSearch, setRunIdSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | string>('all');

  const query = useMemo(() => toAuditListQuery(filters), [filters]);
  const listQuery = useAuditList(agentKey, query);
  const { locale } = useAdminLocale();

  const rows = useMemo(() => {
    const allRows = listQuery.data?.items ?? [];
    let result = allRows;
    if (runIdSearch.trim()) {
      const term = runIdSearch.toLowerCase();
      result = result.filter((r) => r.runId.toLowerCase().includes(term));
    }
    if (statusFilter !== 'all') {
      result = result.filter((r) => r.status === statusFilter);
    }
    return result;
  }, [listQuery.data, runIdSearch, statusFilter]);

  const filterStatusOptions = useMemo(() => [
    { value: 'all', label: t(`${am}audits.filterStatuses.all`) },
    { value: 'success', label: t(`${am}audits.filterStatuses.success`) },
    { value: 'error', label: t(`${am}audits.filterStatuses.error`) },
    { value: 'timeout', label: t(`${am}audits.filterStatuses.timeout`) },
  ], [t]);

  const columns = useMemo<TableColumn<ExecutionAuditView>[]>(
    () => [
      {
        key: 'runId',
        header: 'Run ID',
        render: (row) => (
          <div className="flex items-center gap-1.5">
            <span className="font-mono text-xs" title={row.runId}>
              {row.runId.slice(0, 8)}…
            </span>
            <button
              type="button"
              title={t(`${am}audits.actions.copyRunId`)}
              onClick={() => copyToClipboard(row.runId)}
              className="rounded p-0.5 text-text-muted transition hover:bg-state-hover hover:text-text"
            >
              <Copy size={12} />
            </button>
          </div>
        ),
      },
      {
        key: 'agentVersion',
        header: t(`${am}audits.columns.version`),
        render: (row) => (
          <span className="font-mono">{row.agentVersion != null ? `v${row.agentVersion}` : '-'}</span>
        ),
      },
      {
        key: 'status',
        header: t(`${am}audits.columns.status`),
        render: (row) => (
          <Badge tone={statusTone[row.status] ?? 'neutral'}>
            {t(`${am}audits.statusLabels.${row.status}`, { defaultValue: row.status })}
          </Badge>
        ),
      },
      {
        key: 'outputSummary',
        header: t(`${am}audits.columns.replyPreview`),
        className: 'max-w-[22rem]',
        headerClassName: 'w-[22rem]',
        render: (row) => (
          <div
            className="rounded-[2px] border border-border bg-surface-subtle px-3 py-2.5 text-xs leading-6 text-text"
            title={row.outputSummary ?? row.errorMessage ?? '-'}
          >
            {row.outputSummary?.trim() || row.errorMessage?.trim() || '-'}
          </div>
        ),
      },
      {
        key: 'durationMs',
        header: t(`${am}audits.columns.duration`),
        render: (row) => (
          <span className="text-sm">{row.durationMs != null ? `${row.durationMs}ms` : '-'}</span>
        ),
      },
      {
        key: 'createdAtUtc',
        header: t(`${am}audits.columns.startedAt`),
        render: (row) => formatAdminDateTime(row.createdAtUtc, undefined, locale),
      },
      {
        key: 'actions',
        header: t(`${am}audits.columns.details`),
        render: (row) => (
          <RowActions actions={[{ label: t(`${am}audits.actions.viewTrace`), onClick: () => setSelectedRunId(row.runId) }]} />
        ),
      },
    ],
    [locale, t],
  );

  return (
    <>
      {/* Panel header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-6 py-4">
        <div>
          <h3 className="text-base font-semibold text-text">{t(`${am}audits.panel.title`)}</h3>
          <p className="mt-0.5 text-xs text-text-secondary">{t(`${am}audits.panel.description`)}</p>
        </div>
      </div>

      {/* Filter toolbar */}
      <div className="flex flex-wrap items-center gap-3 border-b border-border bg-background-subtle/40 px-6 py-3">
        <div className="relative flex-1 min-w-[180px] max-w-[280px]">
          <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-text-muted" />
          <input
            type="text"
            value={runIdSearch}
            onChange={(e) => setRunIdSearch(e.target.value)}
            placeholder={t(`${am}audits.searchPlaceholder`)}
            className="w-full rounded-[2px] border border-border bg-surface py-1.5 pl-7 pr-3 text-xs text-text placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary/30"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="rounded-[2px] border border-border bg-surface px-3 py-1.5 text-xs text-text focus:outline-none focus:ring-2 focus:ring-primary/30"
        >
          {filterStatusOptions.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      </div>

      {/* Content */}
      <div className="space-y-4 px-6 py-5">
        {listQuery.isError && (
          <InlineMessage tone="error">{t(`${am}audits.loadError`)}</InlineMessage>
        )}

        <DataTable
          columns={columns}
          rows={rows}
          getRowKey={(row) => row.runId}
          loading={listQuery.isLoading}
          emptyState={
            runIdSearch || statusFilter !== 'all' ? (
              <EmptyState
                title={t(`${am}audits.emptyFiltered.title`)}
                description={t(`${am}audits.emptyFiltered.description`)}
                action={
                  <button
                    type="button"
                    className="text-xs text-primary hover:underline"
                    onClick={() => { setRunIdSearch(''); setStatusFilter('all'); }}
                  >
                    {t(`${am}audits.emptyFiltered.clearFilters`)}
                  </button>
                }
              />
            ) : (
              <EmptyState title={t(`${am}audits.emptyAll.title`)} />
            )
          }
        />

        <Pagination
          page={filters.page}
          pageSize={filters.pageSize}
          totalCount={listQuery.data?.totalCount ?? 0}
          onChange={(page) => setFilters((current) => ({ ...current, page }))}
          onPageSizeChange={(pageSize) => setFilters({ page: 1, pageSize })}
        />
      </div>

      <AuditDetailDrawer
        agentKey={agentKey}
        runId={selectedRunId}
        open={selectedRunId !== null}
        onClose={() => setSelectedRunId(null)}
      />
    </>
  );
}
