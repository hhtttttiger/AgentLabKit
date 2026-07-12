import { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { EmptyState } from '@/shared/ui/EmptyState';
import { useSegmentList } from '../hooks';
import { defaultSegmentListFilters } from '../types';
import type { KbSegmentView } from '../../../lib/contracts';

export function SegmentViewer({ kbId, docId }: { kbId: string; docId: string }) {
  const { t } = useTranslation(['common', 'knowledgeBase']);
  const [page, setPage] = useState(1);
  const pageSize = defaultSegmentListFilters.pageSize;

  const query = useSegmentList(kbId, docId, { page, pageSize });
  const segments = query.data?.items ?? [];
  const totalCount = query.data?.totalCount ?? 0;
  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));

  return (
    <div className="space-y-2">
      <p className="text-xs text-text-muted">共 {totalCount} 个分段</p>

      {query.isLoading && <p className="text-sm text-text-muted">加载中…</p>}

      {!query.isLoading && segments.length === 0 && (
        <EmptyState title={t('knowledgeBase:detail.segmentEmptyTitle')} />
      )}

      <div className="space-y-2">
        {segments.map((seg) => (
          <SegmentRow key={seg.id} segment={seg} />
        ))}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between pt-2 text-xs text-text-muted">
          <span>第 {page} / {totalPages} 页</span>
          <div className="flex gap-2">
            <button
              type="button"
              className="disabled:opacity-40"
              disabled={page <= 1}
              onClick={() => setPage(page - 1)}
            >
              上一页
            </button>
            <button
              type="button"
              className="disabled:opacity-40"
              disabled={page >= totalPages}
              onClick={() => setPage(page + 1)}
            >
              下一页
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function SegmentRow({ segment }: { segment: KbSegmentView }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="rounded-lg border border-border">
      <button
        type="button"
        className="flex w-full items-start gap-2 px-3 py-2 text-left text-sm hover:bg-state-hover/70"
        onClick={() => setExpanded(!expanded)}
      >
        {expanded ? <ChevronDown size={14} className="mt-0.5 shrink-0" /> : <ChevronRight size={14} className="mt-0.5 shrink-0" />}
        <span className="flex-1 text-text-secondary">
          <span className="mr-2 font-mono text-xs text-text-muted">#{segment.segmentIndex}</span>
          {expanded ? '' : truncate(segment.content, 120)}
        </span>
        {segment.tokenCount != null && (
          <span className="shrink-0 text-xs text-text-muted">{segment.tokenCount} tokens</span>
        )}
      </button>
      {expanded && (
        <div className="border-t border-border px-3 py-2">
          <pre className="whitespace-pre-wrap text-sm text-text">{segment.content}</pre>
        </div>
      )}
    </div>
  );
}

function truncate(str: string, len: number): string {
  if (str.length <= len) return str;
  return str.slice(0, len) + '…';
}
