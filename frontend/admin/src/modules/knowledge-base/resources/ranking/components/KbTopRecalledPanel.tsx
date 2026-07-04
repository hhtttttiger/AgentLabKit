import { useMemo } from 'react';
import { FileText, HelpCircle } from 'lucide-react';
import { Badge } from '@/shared/ui/Badge';
import { Card } from '@/shared/ui/Card';
import { EmptyState } from '@/shared/ui/EmptyState';
import { cn } from '@/shared/lib/cn';
import {
  formatRecallTime,
  getKnowledgeDocumentTitle,
  getKnowledgeDocumentTypeLabel,
  getKnowledgeDocumentTypeTone,
} from '../../../lib/ranking';
import type { TopRecalledKbDocumentView } from '../../../lib/contracts';

export function KbTopRecalledPanel({
  documents,
  loading,
}: {
  documents: TopRecalledKbDocumentView[];
  loading: boolean;
  collapsed?: boolean;
  onToggle?: () => void;
}) {
  return (
    <Card
      className="h-fit"
      title="召回文档 / QA Top 30"
      description="按累计召回次数排序，混排显示文件与 QA。"
    >
      {loading ? (
        <div className="divide-y divide-border-subtle">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="flex items-center gap-2.5 px-0.5 py-2">
              <div className="h-5 w-5 animate-pulse rounded-full bg-background-subtle" />
              <div className="h-3.5 w-3.5 shrink-0 animate-pulse rounded bg-background-subtle" />
              <div className="flex-1 space-y-1.5">
                <div className="h-3 w-3/4 animate-pulse rounded bg-background-subtle" />
                <div className="h-2 w-1/2 animate-pulse rounded bg-background-subtle" />
              </div>
            </div>
          ))}
        </div>
      ) : documents.length === 0 ? (
        <EmptyState title="暂无召回数据" description="当文档开始被召回时，排名数据将显示在这里。" />
      ) : (
        <RankedDocumentList documents={documents} />
      )}
    </Card>
  );
}

/* ── Internal Components ── */

function RankedDocumentList({ documents }: { documents: TopRecalledKbDocumentView[] }) {
  const maxRecall = useMemo(() => Math.max(...documents.map((d) => d.recallCount), 1), [documents]);

  return (
    <div className="max-h-[calc(100vh-200px)] overflow-y-auto" style={{ scrollbarGutter: 'stable' }}>
      <ol className="divide-y divide-border-subtle">
        {documents.map((doc, index) => (
          <li
            key={doc.documentId}
            className="group flex items-center gap-2.5 px-0.5 py-2 transition-colors duration-150 hover:bg-state-hover"
          >
            <RankBadge rank={index} />
            <span className={cn('shrink-0', doc.sourceType === 'QaPair' ? 'text-success-text' : 'text-text-muted')}>
              {doc.sourceType === 'File' ? <FileText size={13} /> : <HelpCircle size={13} />}
            </span>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-1.5">
                <span className="truncate text-[13px] font-medium text-text">{getKnowledgeDocumentTitle(doc)}</span>
                <Badge tone={getKnowledgeDocumentTypeTone(doc.sourceType)}>
                  {getKnowledgeDocumentTypeLabel(doc.sourceType)}
                </Badge>
              </div>
              <div className="mt-0.5 flex items-center gap-2.5">
                <div className="h-1 w-16 shrink-0 rounded-full bg-background-subtle">
                  <div
                    className="h-1 rounded-full bg-primary/50 transition-all duration-300"
                    style={{ width: `${(doc.recallCount / maxRecall) * 100}%` }}
                  />
                </div>
                <span className="shrink-0 text-[11px] text-text-muted">{doc.recallCount} 次召回</span>
                <span className="shrink-0 text-[11px] text-text-subtle">最近 {formatRecallTime(doc.lastRecalledAtUtc)}</span>
              </div>
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}

function RankBadge({ rank }: { rank: number }) {
  if (rank === 0) {
    return (
      <div className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-primary/30 bg-primary/10 text-[10px] font-bold text-primary">
        1
      </div>
    );
  }
  if (rank === 1) {
    return (
      <div className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-border-subtle bg-background-subtle text-[10px] font-semibold text-text-secondary">
        2
      </div>
    );
  }
  if (rank === 2) {
    return (
      <div className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-border-subtle bg-background-subtle text-[10px] font-medium text-text-muted">
        3
      </div>
    );
  }
  return (
    <div className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[10px] text-text-muted">
      {rank + 1}
    </div>
  );
}
