import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Search } from 'lucide-react';
import { Button } from '@/shared/ui/Button';
import { TextField, NumberField } from '@/shared/ui/FormFields';

import { getErrorMessage } from '@/shared/api/errors';
import { useKbDetail } from '../../resources/knowledge-base/hooks';
import { kbQueryKeys } from '../../resources/knowledge-base/queryKeys';
import { parseKbSettingsJson } from '../../resources/knowledge-base/settings';
import { searchKnowledgeBase } from '../../resources/search/api';
import {
  defaultSearchForm,
  type SearchFormState,
  type SearchMode,
} from '../../resources/search/types';
import { SearchResultItem } from '../../resources/search/components/SearchResultItem';
import type { KbSearchResult } from '../../lib/contracts';

const SEARCH_MODES: Array<{ value: SearchMode; label: string; description: string }> = [
  { value: 'hybrid', label: '混合召回', description: '向量 + 全文综合排序' },
  { value: 'vector', label: '向量召回', description: '只看语义相似度' },
  { value: 'fulltext', label: '全文召回', description: '只看关键词匹配' },
];

const AZURE_SEARCH_MODES = SEARCH_MODES.filter((m) => m.value !== 'vector');

export function KbSearchTab() {
  const { kbId = '' } = useParams<{ kbId: string }>();
  const [form, setForm] = useState<SearchFormState>(defaultSearchForm);
  const [searchParams, setSearchParams] = useState<{ query: string; topK: number; searchMode: SearchMode } | null>(null);
  const detailQuery = useKbDetail(kbId);

  const searchQuery = useQuery({
    queryKey: kbQueryKeys.search(
      kbId,
      searchParams?.query ?? '',
      searchParams?.topK ?? 10,
      searchParams?.searchMode ?? 'hybrid',
    ),
    queryFn: () =>
      searchKnowledgeBase(kbId, {
        query: searchParams!.query,
        topK: searchParams!.topK,
        searchMode: searchParams!.searchMode,
      }),
    enabled: searchParams !== null && searchParams.query.trim().length > 0,
  });

  const results: KbSearchResult[] = searchQuery.data?.results ?? [];
  const isPending = searchQuery.isFetching;
  const isError = searchQuery.isError;
  const error = searchQuery.error;
  const executedSearchMode = searchParams?.searchMode ?? defaultSearchForm.searchMode;

  const handleSearch = () => {
    if (!form.query.trim()) return;
    setSearchParams({
      query: form.query.trim(),
      topK: form.topK,
      searchMode: form.searchMode,
    });
  };

  const provider = parseKbSettingsJson(detailQuery.data?.settingsJson).provider;
  const isAzure = provider === 'azure';
  const modes = isAzure ? AZURE_SEARCH_MODES : SEARCH_MODES;

  return (
    <div className="overflow-y-auto">
      {/* Search Form */}
      <div className="mb-6 rounded-[2px] border border-border bg-surface p-5">
        <div className="mb-4 flex flex-wrap gap-2">
          {modes.map((mode) => {
            const selected = form.searchMode === mode.value;
            return (
              <button
                key={mode.value}
                type="button"
                onClick={() => setForm((current) => ({ ...current, searchMode: mode.value }))}
                className={[
                  'rounded-[2px] border px-4 py-2.5 text-sm font-medium transition',
                  selected
                    ? 'border-primary/25 bg-primary-subtle text-text'
                    : 'border-border bg-surface text-text-secondary hover:bg-background-subtle',
                ].join(' ')}
              >
                {mode.label}
              </button>
            );
          })}
        </div>
        <div className="flex flex-wrap items-end gap-4">
          <div className="min-w-[300px] flex-1">
            <TextField
              label="搜索内容"
              value={form.query}
              onChange={(e) => setForm((f) => ({ ...f, query: e.target.value }))}
              placeholder="输入要搜索的内容..."
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleSearch();
              }}
            />
          </div>
          <div className="w-24">
            <NumberField
              label="返回数量"
              min={1}
              max={50}
              value={form.topK}
              onChange={(e) => setForm((f) => ({ ...f, topK: Number(e.target.value) }))}
            />
          </div>
          <Button onClick={handleSearch} disabled={isPending || !form.query.trim()}>
            <Search size={16} />
            {isPending ? '搜索中...' : '搜索'}
          </Button>
        </div>
      </div>

      {/* Results */}
      {isError && (
        <div className="mb-4 rounded-[2px] border border-error/20 bg-error-subtle p-4 text-sm text-error-text">
          {getErrorMessage(error, '搜索失败，请重试。')}
        </div>
      )}

      {results.length === 0 && !isPending && (
        <div className="flex flex-col items-center justify-center py-16 text-text-secondary">
          <Search size={40} className="mb-3 opacity-30" />
          <p className="text-sm">输入搜索内容并点击搜索查看结果。</p>
        </div>
      )}

      <div className="space-y-3">
        {results.length > 0 && executedSearchMode === 'hybrid' && (
          <div className="rounded-[2px] border border-info/20 bg-info-subtle px-4 py-3 text-sm text-text-secondary">
            {isAzure
              ? '提示：Azure 混合检索使用语义搜索，综合分来自 Azure AI Search 的语义排序。'
              : '提示：混合检索下，向量分和全文分是各自召回通道内的归一化结果，综合分是融合排序分。'}
          </div>
        )}
        {results.map((result) => (
          <SearchResultItem
            key={result.segmentId}
            result={result}
            query={form.query}
            searchMode={executedSearchMode}
          />
        ))}
      </div>
    </div>
  );
}
