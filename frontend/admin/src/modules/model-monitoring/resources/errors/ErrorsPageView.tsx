
import { ChevronDown, ChevronRight } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Badge } from '@/shared/ui/Badge';
import { FilterToolbarActions } from '@/shared/ui/FilterToolbarActions';
import { EmptyState } from '@/shared/ui/EmptyState';
import { InlineMessage } from '@/shared/ui/InlineMessage';
import { FilterToolbar } from '@/shared/ui/FilterToolbar';
import { ManagementListFrame } from '@/shared/ui/ManagementListFrame';
import { Pagination } from '@/shared/ui/Pagination';
import { DateField, SelectField } from '@/shared/ui/FormFields';
import { SkeletonRows } from '@/shared/ui/Skeleton';
import { useAdminLocale } from '@/shared/i18n/useAdminLocale';
import type { ModelErrorRecord } from '../../lib/contracts';
import { formatDateTime, formatLatency } from '../../lib/formatters';
import type { ErrorsPageState } from './useErrorsPageState';
import { useErrorCodeOptions } from './errorCodes';

function ErrorRowDetail({ record }: { record: ModelErrorRecord }) {
  const { t } = useTranslation('common');
  return (
    <div className="rounded-[2px] border border-border-subtle bg-background-subtle/70 p-4 text-sm">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <div>
          <div className="text-[11px] uppercase tracking-[0.16em] text-text-muted">{t('modules.modelMonitoring.errors.detail.errorMessage')}</div>
          <div className="mt-1 text-text">{record.errorMessage ?? '-'}</div>
        </div>
        <div>
          <div className="text-[11px] uppercase tracking-[0.16em] text-text-muted">{t('modules.modelMonitoring.errors.detail.instance')}</div>
          <div className="mt-1 font-mono text-xs text-text">{record.instanceKey ?? '-'}</div>
        </div>
        <div>
          <div className="text-[11px] uppercase tracking-[0.16em] text-text-muted">{t('modules.modelMonitoring.errors.detail.capability')}</div>
          <div className="mt-1 text-text">{record.capability ?? '-'}</div>
        </div>
        <div>
          <div className="text-[11px] uppercase tracking-[0.16em] text-text-muted">{t('modules.modelMonitoring.errors.detail.duration')}</div>
          <div className="mt-1 text-text">{formatLatency(record.durationMs)}</div>
        </div>
      </div>
    </div>
  );
}

export function ErrorsPageView({ state }: { state: ErrorsPageState }) {
  useAdminLocale();
  const { t } = useTranslation('common');
  const errorCodeOptions = useErrorCodeOptions(t);
  return (
    <ManagementListFrame
      refreshing={state.listQuery.isFetching}
      error={
        state.listQuery.isError ? (
          <InlineMessage tone="error">
            {state.listQuery.error?.message ?? t('modules.modelMonitoring.errors.error')}
          </InlineMessage>
        ) : undefined
      }
      toolbar={
        <FilterToolbar
          compact
          actions={
            <FilterToolbarActions
              onRefresh={() => state.listQuery.refetch()}
              refreshing={state.listQuery.isFetching}
              onReset={state.resetFilters}
            />
          }
        >
          <SelectField
            label={t('modules.modelMonitoring.errors.filters.model')}
            fieldSize="compact"
            value={state.filters.modelKey}
            onChange={(e) => state.patchFilters({ modelKey: e.target.value, page: 1 })}
          >
            <option value="">
              {state.modelOptionsQuery.isLoading
                ? t('modules.modelMonitoring.errors.filters.loading')
                : t('modules.modelMonitoring.errors.filters.allModels')}
            </option>
            {(state.modelOptionsQuery.data ?? []).map((item) => (
              <option key={item.modelKey} value={item.modelKey}>
                {item.displayName}
              </option>
            ))}
          </SelectField>
          <SelectField
            label={t('modules.modelMonitoring.errors.filters.errorCode')}
            fieldSize="compact"
            value={state.filters.errorCode}
            onChange={(e) => state.patchFilters({ errorCode: e.target.value, page: 1 })}
          >
            <option value="">{t('modules.modelMonitoring.errors.filters.allErrorCodes')}</option>
            {errorCodeOptions.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </SelectField>
          <DateField
            label={t('modules.modelMonitoring.errors.filters.startTime')}
            fieldSize="compact"
            value={state.filters.fromDate}
            onChange={(nextValue) => state.patchFilters({ fromDate: nextValue, page: 1 })}
          />
          <DateField
            label={t('modules.modelMonitoring.errors.filters.endTime')}
            fieldSize="compact"
            value={state.filters.toDate}
            onChange={(nextValue) => state.patchFilters({ toDate: nextValue, page: 1 })}
          />
        </FilterToolbar>
      }
      pagination={
        <Pagination
          page={state.filters.page}
          pageSize={state.filters.pageSize}
          totalCount={state.listQuery.data?.totalCount ?? 0}
          onChange={state.setPage}
        />
      }
    >
        {state.listQuery.isLoading ? (
          <SkeletonRows columns={5} />
        ) : !state.rows.length ? (
          <EmptyState
            title={t('modules.modelMonitoring.errors.empty.title')}
            description={t('modules.modelMonitoring.errors.empty.description')}
          />
        ) : (
          <div className="overflow-hidden rounded-[2px] border border-border bg-surface">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-border">
                <thead className="bg-background-subtle text-left">
                  <tr>
                    <th className="w-8 px-3 py-3" />
                    <th className="px-4 py-3 text-xs font-semibold uppercase tracking-[0.12em] text-text-muted">{t('modules.modelMonitoring.errors.table.headers.time')}</th>
                    <th className="px-4 py-3 text-xs font-semibold uppercase tracking-[0.12em] text-text-muted">{t('modules.modelMonitoring.errors.table.headers.model')}</th>
                    <th className="px-4 py-3 text-xs font-semibold uppercase tracking-[0.12em] text-text-muted">{t('modules.modelMonitoring.errors.table.headers.errorCode')}</th>
                    <th className="px-4 py-3 text-xs font-semibold uppercase tracking-[0.12em] text-text-muted">{t('modules.modelMonitoring.errors.table.headers.capability')}</th>
                    <th className="px-4 py-3 text-xs font-semibold uppercase tracking-[0.12em] text-text-muted">{t('modules.modelMonitoring.errors.table.headers.errorMessage')}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {state.rows.map((record) => {
                    const isExpanded = state.expandedRowId === `${record.requestId}-${record.startedAtUtc}`;
                    return (
                      <ErrorRow
                        key={`${record.requestId}-${record.startedAtUtc}`}
                        record={record}
                        isExpanded={isExpanded}
                        onToggle={() => state.toggleExpand(`${record.requestId}-${record.startedAtUtc}`)}
                        uncategorizedLabel={t('modules.modelMonitoring.errors.table.uncategorized')}
                      />
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </ManagementListFrame>
  );
}

function ErrorRow({
  record,
  isExpanded,
  onToggle,
  uncategorizedLabel,
}: {
  record: ModelErrorRecord;
  isExpanded: boolean;
  onToggle: () => void;
  uncategorizedLabel: string;
}) {
  return (
    <>
      <tr className="cursor-pointer align-top transition hover:bg-state-hover/70" onClick={onToggle}>
        <td className="px-3 py-4 text-text-muted">
          {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </td>
        <td className="px-4 py-4 text-sm text-text-secondary">{formatDateTime(record.startedAtUtc)}</td>
        <td className="px-4 py-4 text-sm font-medium text-text">{record.displayName}</td>
        <td className="px-4 py-4">
          <Badge tone="danger">{record.errorCode ?? uncategorizedLabel}</Badge>
        </td>
        <td className="px-4 py-4 text-sm text-text-secondary">{record.capability ?? '-'}</td>
        <td className="max-w-xs truncate px-4 py-4 text-sm text-text-secondary">{record.errorMessage ?? '-'}</td>
      </tr>
      {isExpanded ? (
        <tr>
          <td colSpan={6} className="px-4 py-3">
            <ErrorRowDetail record={record} />
          </td>
        </tr>
      ) : null}
    </>
  );
}
