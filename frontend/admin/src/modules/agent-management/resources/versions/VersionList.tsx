import { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Search } from 'lucide-react';
import { Badge } from '@/shared/ui/Badge';
import { Button } from '@/shared/ui/Button';
import { RowActions } from '@/shared/ui/RowActions';
import { DataTable, type TableColumn } from '@/shared/ui/DataTable';
import { EmptyState } from '@/shared/ui/EmptyState';
import { InlineMessage } from '@/shared/ui/InlineMessage';
import { Pagination } from '@/shared/ui/Pagination';
import { formatAdminDateTime } from '@/shared/i18n/formatters';
import { useAdminLocale } from '@/shared/i18n/useAdminLocale';
import type { AgentVersionSummaryView, VersionDetailView, VersionStatus } from '../../lib/contracts';
import { useVersionList, useVersionDetail } from './hooks';
import { VersionDrawer } from './VersionDrawer';

const am = 'agentManagement:';

export type VersionLaunchAction =
  | { kind: 'create'; key: string }
  | { kind: 'edit'; versionNumber: number; key: string }
  | { kind: 'view'; versionNumber: number; key: string }
  | { kind: 'clone'; versionNumber: number; key: string };

const versionStatusTone: Record<string, 'success' | 'warning' | 'neutral'> = {
  draft: 'warning',
  published: 'success',
  archived: 'neutral',
};

export function VersionList({
  agentKey,
  onPublish,
  launchAction,
  createTrigger,
}: {
  agentKey: string;
  onPublish: (versionNumber: number, rowVersion: number) => void;
  launchAction?: VersionLaunchAction | null;
  createTrigger?: number;
}) {
  const { t } = useTranslation(['common', 'agentManagement']);
  const [createOpen, setCreateOpen] = useState(false);
  const [editVersionNumber, setEditVersionNumber] = useState<number | null>(null);
  const [viewVersionNumber, setViewVersionNumber] = useState<number | null>(null);
  const [cloneSourceVersionNumber, setCloneSourceVersionNumber] = useState<number | null>(null);

  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | VersionStatus>('all');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  const listQuery = useVersionList(agentKey, { page, pageSize });
  const editDetailQuery = useVersionDetail(agentKey, editVersionNumber);
  const viewDetailQuery = useVersionDetail(agentKey, viewVersionNumber);
  const cloneSourceQuery = useVersionDetail(agentKey, cloneSourceVersionNumber);
  const { locale } = useAdminLocale();

  useEffect(() => {
    if (!launchAction) return;

    if (launchAction.kind === 'create') {
      setCloneSourceVersionNumber(null);
      setCreateOpen(true);
      return;
    }

    if (launchAction.kind === 'edit') {
      setEditVersionNumber(launchAction.versionNumber);
      return;
    }

    if (launchAction.kind === 'view') {
      setViewVersionNumber(launchAction.versionNumber);
      return;
    }

    setCloneSourceVersionNumber(launchAction.versionNumber);
    setCreateOpen(true);
  }, [launchAction]);

  useEffect(() => {
    if (!createTrigger) return;
    setCloneSourceVersionNumber(null);
    setCreateOpen(true);
  }, [createTrigger]);

  const filteredRows = useMemo(() => {
    const allRows = listQuery.data?.items ?? [];
    let result = allRows;
    if (statusFilter !== 'all') {
      result = result.filter((r) => r.versionStatus === statusFilter);
    }
    if (search.trim()) {
      const term = search.toLowerCase();
      result = result.filter(
        (r) =>
          `v${r.versionNumber}`.includes(term) ||
          (r.versionLabel?.toLowerCase().includes(term) ?? false) ||
          (r.changeSummary?.toLowerCase().includes(term) ?? false),
      );
    }
    return result;
  }, [listQuery.data, statusFilter, search]);

  const totalCount = listQuery.data?.totalCount ?? filteredRows.length;

  useEffect(() => { setPage(1); }, [search, statusFilter]);

  const columns = useMemo<TableColumn<AgentVersionSummaryView>[]>(
    () => [
      {
        key: 'versionNumber',
        header: t(`${am}versions.columns.versionNumber`),
        render: (row) => (
          <span className="font-mono font-medium text-text">v{row.versionNumber}</span>
        ),
      },
      {
        key: 'versionStatus',
        header: t(`${am}versions.columns.status`),
        render: (row) => (
          <Badge tone={versionStatusTone[row.versionStatus] ?? 'neutral'}>
            {t(`${am}versions.status${row.versionStatus.charAt(0).toUpperCase() + row.versionStatus.slice(1)}`, { defaultValue: row.versionStatus })}
          </Badge>
        ),
      },
      {
        key: 'versionLabel',
        header: t(`${am}versions.columns.label`),
        render: (row) => row.versionLabel ?? '-',
      },
      {
        key: 'changeSummary',
        header: t(`${am}versions.columns.changelog`),
        className: 'max-w-[18rem]',
        render: (row) => {
          const text = row.changeSummary;
          if (!text) return <span className="text-text-muted">-</span>;
          const truncated = text.length > 80 ? `${text.slice(0, 80)}…` : text;
          return (
            <span className="block truncate text-text-secondary" title={text}>
              {truncated}
            </span>
          );
        },
      },
      {
        key: 'modelKey',
        header: t(`${am}versions.columns.model`),
        render: (row) => <span className="font-mono text-xs">{row.modelKey}</span>,
      },
      {
        key: 'publishedAtUtc',
        header: t(`${am}versions.columns.publishedAt`),
        render: (row) => formatAdminDateTime(row.publishedAtUtc, undefined, locale),
      },
      {
        key: 'createdAtUtc',
        header: t(`${am}versions.columns.createdAt`),
        render: (row) => formatAdminDateTime(row.createdAtUtc, undefined, locale),
      },
      {
        key: 'actions',
        header: t(`${am}versions.columns.actions`),
        render: (row) => {
          if (row.versionStatus === 'published') {
            return (
              <RowActions actions={[
                { label: t(`${am}versions.actions.view`), onClick: () => setViewVersionNumber(row.versionNumber) },
                { label: t(`${am}versions.actions.createDraft`), onClick: () => { setCloneSourceVersionNumber(row.versionNumber); setCreateOpen(true); } },
              ]} />
            );
          }
          if (row.versionStatus === 'draft') {
            return (
              <RowActions actions={[
                { label: t(`${am}versions.actions.editDraft`), onClick: () => setEditVersionNumber(row.versionNumber) },
                { label: t(`${am}versions.actions.publish`), onClick: () => onPublish(row.versionNumber, row.rowVersion) },
              ]} />
            );
          }
          return null;
        },
      },
    ],
    [locale, onPublish, t],
  );

  return (
    <>
      <div className="flex flex-wrap items-center gap-3 border-b border-border bg-background-subtle/40 px-6 py-3">
        <div className="relative flex-1 min-w-[180px] max-w-[280px]">
          <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-text-muted" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={t(`${am}versions.searchPlaceholder`)}
            className="w-full rounded-[2px] border border-border bg-surface py-1.5 pl-7 pr-3 text-xs text-text placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary/30"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as 'all' | VersionStatus)}
          className="rounded-[2px] border border-border bg-surface px-3 py-1.5 text-xs text-text focus:outline-none focus:ring-2 focus:ring-primary/30"
        >
          <option value="all">{t(`${am}versions.allStatuses`)}</option>
          <option value="draft">{t(`${am}versions.statusDraft`)}</option>
          <option value="published">{t(`${am}versions.statusPublished`)}</option>
          <option value="archived">{t(`${am}versions.statusArchived`)}</option>
        </select>
      </div>

      <div className="space-y-4 px-6 py-5">
        <InlineMessage tone="info">
          {t(`${am}versions.publishedReadonlyInfo`)}
        </InlineMessage>

        {listQuery.isError && (
          <InlineMessage tone="error">{t(`${am}versions.loadError`)}</InlineMessage>
        )}

        <DataTable
          columns={columns}
          rows={filteredRows}
          getRowKey={(row) => String(row.versionNumber)}
          loading={listQuery.isLoading}
          emptyState={
            search || statusFilter !== 'all' ? (
              <EmptyState
                title={t(`${am}versions.emptyFiltered.title`)}
                description={t(`${am}versions.emptyFiltered.description`)}
                action={<Button variant="secondary" onClick={() => { setSearch(''); setStatusFilter('all'); }}>{t(`${am}versions.emptyFiltered.clearFilters`)}</Button>}
              />
            ) : (
              <EmptyState
                title={t(`${am}versions.emptyAll.title`)}
                description={t(`${am}versions.emptyAll.description`)}
                action={<Button onClick={() => setCreateOpen(true)}>{t(`${am}versions.emptyAll.createFirst`)}</Button>}
              />
            )
          }
        />

        <Pagination
          page={page}
          pageSize={pageSize}
          totalCount={totalCount}
          onChange={setPage}
          onPageSizeChange={(newSize) => { setPageSize(newSize); setPage(1); }}
        />
      </div>

      <VersionDrawer
        open={createOpen && (cloneSourceVersionNumber === null || cloneSourceQuery.isSuccess)}
        agentKey={agentKey}
        seedVersion={cloneSourceQuery.data}
        onClose={() => {
          setCreateOpen(false);
          setCloneSourceVersionNumber(null);
        }}
      />

      <VersionDrawer
        open={editVersionNumber !== null && editDetailQuery.isSuccess}
        agentKey={agentKey}
        editVersion={editDetailQuery.data as VersionDetailView | undefined}
        onClose={() => setEditVersionNumber(null)}
      />

      <VersionDrawer
        open={viewVersionNumber !== null && viewDetailQuery.isSuccess}
        agentKey={agentKey}
        editVersion={viewDetailQuery.data as VersionDetailView | undefined}
        readOnly
        onClose={() => setViewVersionNumber(null)}
      />
    </>
  );
}
