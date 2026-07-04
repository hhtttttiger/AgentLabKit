import { useState } from 'react';
import { ChevronDown, ChevronUp, FileText, HelpCircle } from 'lucide-react';
import { Badge } from '@/shared/ui/Badge';
import type { KbSearchResult } from '../../../lib/contracts';
import type { SearchMode } from '../types';

type ScoreBarProps = {
  label: string;
  value?: number;
  colorClass: string;
};

export function SearchResultItem({
  result,
  query,
  searchMode,
}: {
  result: KbSearchResult;
  query: string;
  searchMode: SearchMode;
}) {
  const [expanded, setExpanded] = useState(false);
  const recallSources = parseRecallSources(result.metadataJson);
  const azureScore = parseAzureScore(result.metadataJson);
  const localScore = parseLocalScore(result.metadataJson);
  const scoreRows = getScoreRows(result, searchMode, recallSources, azureScore, localScore);
  const headlineScoreLabel = getHeadlineScoreLabel(result.score, recallSources, azureScore, localScore);

  return (
    <div className="rounded-[2px] border border-border bg-surface p-4 transition hover:border-primary/20">
      <div className="flex items-start gap-3">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary-subtle">
          {result.documentType === 'QaPair' ? (
            <HelpCircle size={14} className="text-success-text" />
          ) : (
            <FileText size={14} className="text-primary" />
          )}
        </div>
        <div className="min-w-0 flex-1">
          {/* Document name + score */}
          <div className="flex items-center justify-between gap-2">
            <div className="flex min-w-0 items-center gap-2">
              <span className="truncate text-sm font-medium text-text">
                {result.documentName ?? `文档 ${result.documentId}`}
              </span>
              {result.documentType && (
                <Badge tone={result.documentType === 'QaPair' ? 'success' : 'neutral'}>
                  {result.documentType === 'QaPair' ? 'QA' : '文件'}
                </Badge>
              )}
              {recallSources.map((src) => (
                <Badge key={src} tone={src === 'azure_chunk_push' || src === 'azure' ? 'info' : 'neutral'}>
                  {src === 'azure_chunk_push' ? 'Azure' : src === 'azure' ? 'Azure' : src}
                </Badge>
              ))}
            </div>
            <span className="shrink-0 text-xs font-semibold text-primary">
              {headlineScoreLabel} {formatScore(result.score)}
            </span>
          </div>

          <div className="mt-1.5 flex flex-wrap items-center gap-x-4 gap-y-1">
            {scoreRows.map((row) => (
              <ScoreBar key={row.label} {...row} />
            ))}
          </div>

          <p className="mt-2 text-sm leading-6 text-text-secondary">
            {expanded ? result.content : truncateSnippet(result.content, query)}
          </p>

          {/* Toggle */}
          {result.content.length > 200 && (
            <button
              className="mt-2 flex items-center gap-1 text-xs font-medium text-primary hover:underline"
              onClick={() => setExpanded(!expanded)}
            >
              {expanded ? (
                <><ChevronUp size={12} /> 收起</>
              ) : (
                <><ChevronDown size={12} /> 展开全文</>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function ScoreBar({ label, value, colorClass }: ScoreBarProps) {
  const percent = Math.max(0, Math.min(100, Math.round((value ?? 0) * 100)));

  return (
    <div className="flex items-center gap-2">
      <span className="w-10 shrink-0 text-[11px] text-text-muted">{label}</span>
      <div className="h-1 w-20 shrink-0 overflow-hidden rounded-full bg-background-subtle">
        <div className={`h-full rounded-full transition-all duration-300 ${colorClass}`} style={{ width: `${percent}%` }} />
      </div>
      <span className="shrink-0 font-mono text-[11px] tabular-nums text-text-secondary">{formatScore(value)}</span>
    </div>
  );
}

function getScoreRows(result: KbSearchResult, searchMode: SearchMode, recallSources: string[], azureScore?: number, localScore?: number): ScoreBarProps[] {
  const hasAzure = recallSources.includes('azure_chunk_push') || recallSources.includes('azure');
  const hasLocal = recallSources.includes('local') || (!hasAzure && recallSources.length === 0);

  if (searchMode === 'vector') {
    const rows: ScoreBarProps[] = [];
    if (hasLocal) rows.push({ label: '相似度', value: result.vectorScore ?? result.score, colorClass: 'bg-violet-500' });
    if (hasAzure) rows.push({ label: 'Azure', value: azureScore, colorClass: 'bg-sky-500' });
    if (hasLocal) rows.push({ label: '综合分', value: localScore ?? result.score, colorClass: 'bg-amber-500' });
    return rows;
  }

  if (searchMode === 'fulltext') {
    const rows: ScoreBarProps[] = [];
    if (hasLocal) rows.push({ label: '匹配度', value: result.fulltextScore ?? result.score, colorClass: 'bg-emerald-500' });
    if (hasAzure) rows.push({ label: 'Azure', value: azureScore, colorClass: 'bg-sky-500' });
    if (hasLocal) rows.push({ label: '综合分', value: localScore ?? result.score, colorClass: 'bg-amber-500' });
    return rows;
  }

  const rows: ScoreBarProps[] = [];
  if (hasLocal) {
    rows.push(
      { label: '向量分', value: result.vectorScore, colorClass: 'bg-violet-500' },
      { label: '全文分', value: result.fulltextScore, colorClass: 'bg-emerald-500' },
    );
  }
  if (hasAzure) {
    rows.push({ label: 'Azure', value: azureScore, colorClass: 'bg-sky-500' });
  }
  if (hasLocal) {
    rows.push({ label: '综合分', value: localScore ?? result.score, colorClass: 'bg-amber-500' });
  }
  if (!hasLocal && !hasAzure) {
    rows.push({ label: '综合分', value: result.score, colorClass: 'bg-amber-500' });
  }
  return rows;
}

function getHeadlineScoreLabel(resultScore: number, recallSources: string[], azureScore?: number, localScore?: number): string {
  const hasAzure = recallSources.includes('azure_chunk_push') || recallSources.includes('azure');
  const hasLocal = recallSources.includes('local') || (!hasAzure && recallSources.length === 0);

  if (!hasAzure || !hasLocal || localScore === undefined) {
    return '综合';
  }

  const differsFromLocalComposite = Math.abs(resultScore - localScore) > 0.0001;
  const matchesAzureScore = azureScore !== undefined && Math.abs(resultScore - azureScore) <= 0.0001;
  return differsFromLocalComposite && matchesAzureScore ? '排序' : '综合';
}

function formatScore(value?: number): string {
  return (value ?? 0).toFixed(2);
}

function truncateSnippet(text: string, query: string): string {
  if (text.length <= 200) return text;
  if (!query) return text.slice(0, 200) + '...';
  const idx = text.toLowerCase().indexOf(query.toLowerCase());
  if (idx === -1) return text.slice(0, 200) + '...';
  const start = Math.max(0, idx - 50);
  const end = Math.min(text.length, idx + query.length + 150);
  return (start > 0 ? '...' : '') + text.slice(start, end) + (end < text.length ? '...' : '');
}

function parseRecallSources(metadataJson?: string): string[] {
  if (!metadataJson) return [];
  try {
    const meta = JSON.parse(metadataJson);
    const sources = meta?.recall_sources;
    if (!Array.isArray(sources)) return [];
    return sources.filter((s: unknown) => typeof s === 'string');
  } catch {
    return [];
  }
}

function parseAzureScore(metadataJson?: string): number | undefined {
  if (!metadataJson) return undefined;
  try {
    const meta = JSON.parse(metadataJson);
    const val = meta?.azure_search_score;
    return typeof val === 'number' ? val : undefined;
  } catch {
    return undefined;
  }
}

function parseLocalScore(metadataJson?: string): number | undefined {
  if (!metadataJson) return undefined;
  try {
    const meta = JSON.parse(metadataJson);
    const val = meta?.local_search_score;
    return typeof val === 'number' ? val : undefined;
  } catch {
    return undefined;
  }
}
