import { useState } from 'react';
import { useMemoryList, useMemoryStats, useDeactivateMemory, useDeleteMemory, useConsolidateMemories } from './hooks';
import { MetricStrip } from '@/shared/ui/MetricStrip';
import { Pagination } from '@/shared/ui/Pagination';
import { SkeletonCards } from '@/shared/ui/Skeleton';
import { EmptyState } from '@/shared/ui/EmptyState';
import { InlineMessage } from '@/shared/ui/InlineMessage';
import { useToast } from '@/shared/ui/Toast';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@/shared/auth';

const TYPE_STYLES: Record<string, string> = {
  episodic: 'bg-blue-500/10 text-blue-500',
  semantic: 'bg-violet-500/10 text-violet-500',
  procedural: 'bg-teal-500/10 text-teal-500',
};

const METRIC_ACCENTS = ['blue', 'violet', 'teal', 'amber'] as const;

export function MemoryListPage() {
  const { t } = useTranslation(['common', 'memory']);
  const { toast } = useToast();
  const { user } = useAuth();
  const userId = user?.userId ?? '';
  const [filterType, setFilterType] = useState<string | undefined>(undefined);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  const {
    data: result,
    isLoading,
    isError,
    error,
  } = useMemoryList({ userId, memoryType: filterType, page, pageSize });
  const { data: stats } = useMemoryStats(userId);
  const deactivateMutation = useDeactivateMemory();
  const deleteMutation = useDeleteMemory();
  const consolidateMutation = useConsolidateMemories();

  const memories = result?.items ?? [];
  const total = result?.totalCount ?? 0;

  const typeLabels: Record<string, string> = {
    episodic: t('memory:list.typeLabels.episodic'),
    semantic: t('memory:list.typeLabels.semantic'),
    procedural: t('memory:list.typeLabels.procedural'),
  };

  const metrics = stats
    ? [
        { label: t('memory:list.metrics.totalActive'), value: String(stats.totalActive), accent: METRIC_ACCENTS[0] },
        { label: t('memory:list.metrics.episodic'), value: String(stats.countsByType.episodic || 0), accent: METRIC_ACCENTS[1] },
        { label: t('memory:list.metrics.semantic'), value: String(stats.countsByType.semantic || 0), accent: METRIC_ACCENTS[2] },
        { label: t('memory:list.metrics.procedural'), value: String(stats.countsByType.procedural || 0), accent: METRIC_ACCENTS[3] },
      ]
    : [];

  return (
    <div className="flex flex-col gap-6 p-6 pb-10 h-[calc(100vh-var(--header-height,3.5rem))] overflow-hidden">
      {/* 类型过滤 + 操作 */}
      <div className="flex items-center justify-between gap-2 shrink-0">
        <div className="flex items-center gap-2" role="radiogroup" aria-label={t('memory:list.filterLabel')}>
          <button
            onClick={() => { setFilterType(undefined); setPage(1); }}
            className={`rounded-[2px] px-3 py-1 text-xs ${!filterType ? 'bg-primary text-background' : 'bg-surface border border-border text-text-secondary'}`}
            role="radio"
            aria-checked={!filterType}
            aria-label={t('memory:list.filterAll')}
          >
            {t('memory:list.filterAll')}
          </button>
          {Object.entries(typeLabels).map(([key, label]) => (
            <button
              key={key}
              onClick={() => { setFilterType(key); setPage(1); }}
              className={`rounded-[2px] px-3 py-1 text-xs ${filterType === key ? 'bg-primary text-background' : 'bg-surface border border-border text-text-secondary'}`}
              role="radio"
              aria-checked={filterType === key}
              aria-label={label}
            >
              {label}
            </button>
          ))}
        </div>
        <button
          className="rounded-[2px] bg-primary px-3 py-2 text-xs text-background shrink-0"
          onClick={() => consolidateMutation.mutateAsync({}).then(() => { setPage(1); toast(t('toast.consolidateDone')); }).catch(() => {})}
          disabled={consolidateMutation.isPending}
        >
          {consolidateMutation.isPending ? t('processing') : t('memory:list.consolidate')}
        </button>
      </div>

      {/* 统计 */}
      {metrics.length > 0 && (
        <div className="shrink-0">
          <MetricStrip items={metrics} columns={4} />
        </div>
      )}

      {/* 错误状态 */}
      {isError && (
        <InlineMessage tone="error">
          {t('memory:list.loadError', { message: (error as Error)?.message || '' })}
        </InlineMessage>
      )}

      {/* 列表 — 撑开剩余空间，内部滚动 */}
      <div className="flex-1 min-h-0 overflow-y-auto" role="list" aria-busy={isLoading}>
        {isLoading ? (
          <SkeletonCards count={6} />
        ) : !memories.length ? (
          <EmptyState
            title={t('memory:list.emptyTitle')}
            description={t('memory:list.emptyDescription')}
          />
        ) : (
          <div className="flex flex-col gap-2">
            {memories.map((m) => {
              const typeLabel = typeLabels[m.memoryType] || m.memoryType;
              const style = TYPE_STYLES[m.memoryType] || TYPE_STYLES.episodic;
              return (
                <div
                  key={m.id}
                  className="flex items-start gap-4 rounded-[2px] border border-border bg-surface px-6 py-4"
                  role="listitem"
                  aria-label={`${typeLabel}: ${m.content.slice(0, 60)}`}
                >
                  <span className={`mt-0.5 shrink-0 rounded-[2px] px-2 py-0.5 text-xs ${style}`}>
                    {typeLabel}
                  </span>
                  <div className="flex-1">
                    <p className="text-sm text-text line-clamp-3">{m.content}</p>
                    <div className="mt-2 flex items-center gap-3 text-xs text-text-muted">
                      <span>{t('memory:list.accessCount', { count: m.accessCount })}</span>
                      <span>{t('memory:list.relevance', { score: m.relevanceScore.toFixed(2) })}</span>
                      <span>{new Date(m.createdAtUtc).toLocaleString()}</span>
                    </div>
                  </div>
                  <div className="shrink-0 flex flex-col items-end gap-1">
                    <button
                      className="text-xs text-text-muted hover:text-error hover:underline"
                      onClick={() => deactivateMutation.mutate(m.id, {
                        onSuccess: () => toast(t('toast.deactivateDone')),
                      })}
                      disabled={deactivateMutation.isPending}
                      aria-label={`${t('memory:list.deactivate')} ${typeLabel}`}
                    >
                      {t('memory:list.deactivate')}
                    </button>
                    <button
                      className="text-xs text-text-muted hover:text-error hover:underline"
                      onClick={() => deleteMutation.mutate(m.id, {
                        onSuccess: () => toast(t('toast.deleted')),
                      })}
                      disabled={deleteMutation.isPending}
                      aria-label={`${t('delete')} ${typeLabel}`}
                    >
                      {t('delete')}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* 分页 — 固定底部 */}
      <div className="shrink-0">
        <Pagination
          page={page}
          pageSize={pageSize}
          totalCount={total}
          onChange={setPage}
          onPageSizeChange={(size) => { setPageSize(size); setPage(1); }}
        />
      </div>
    </div>
  );
}
