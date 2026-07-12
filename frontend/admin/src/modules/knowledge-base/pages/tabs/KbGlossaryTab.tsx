import { useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { getErrorMessage } from '@/shared/api/errors';
import { Button } from '@/shared/ui/Button';
import { EmptyState } from '@/shared/ui/EmptyState';
import { InlineMessage } from '@/shared/ui/InlineMessage';

import { useKbGlossaryBinding, useKbGlossaryBindingMutations } from '../../resources/glossary-binding/hooks';

function sameIds(left: string[], right: string[]) {
  if (left.length !== right.length) {
    return false;
  }

  const rightSet = new Set(right);
  return left.every((item) => rightSet.has(item));
}

export function KbGlossaryTab() {
  const { kbId } = useParams<{ kbId: string }>();
  const { t } = useTranslation(['common', 'knowledgeBase']);
  const bindingQuery = useKbGlossaryBinding(kbId);
  const mutations = useKbGlossaryBindingMutations();
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  useEffect(() => {
    setSelectedIds(bindingQuery.data?.categoryIds ?? []);
  }, [bindingQuery.data?.categoryIds]);

  const orderedSelectedIds = useMemo(() => {
    const categoryIds = bindingQuery.data?.categories.map((item) => item.id) ?? [];
    return categoryIds.filter((item) => selectedIds.includes(item));
  }, [bindingQuery.data?.categories, selectedIds]);

  const isDirty = !sameIds(orderedSelectedIds, bindingQuery.data?.categoryIds ?? []);

  const shouldShowInitialLoadError = bindingQuery.isError && !bindingQuery.data;
  const shouldShowReloadWarning = bindingQuery.isError && Boolean(bindingQuery.data);

  return (
    <div className="overflow-y-auto">
      <div className="mx-auto flex w-full max-w-4xl flex-col gap-6">
        <div className="rounded-[2px] border border-border bg-surface/80 p-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <h2 className="text-xl font-semibold text-text">{t('knowledgeBase:detail.sections.glossary')}</h2>
              <p className="mt-2 text-sm leading-6 text-text-secondary">
                {t('knowledgeBase:detail.glossaryBindingDescription')}
              </p>
            </div>
            {bindingQuery.data && bindingQuery.data.categories.length > 0 ? (
              <Button
                onClick={() => {
                  if (!kbId) {
                    return;
                  }

                  mutations.replace.mutate({ kbId, categoryIds: orderedSelectedIds });
                }}
                disabled={mutations.replace.isPending || !isDirty}
              >
                {mutations.replace.isPending ? t('knowledgeBase:detail.glossarySaving') : t('knowledgeBase:detail.glossarySave')}
              </Button>
            ) : null}
          </div>
        </div>

        {shouldShowInitialLoadError ? (
          <InlineMessage tone="error">{getErrorMessage(bindingQuery.error)}</InlineMessage>
        ) : null}

        {shouldShowReloadWarning ? (
          <InlineMessage tone="info">{t('knowledgeBase:detail.glossaryRefreshFailed')}</InlineMessage>
        ) : null}

        {bindingQuery.isLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 4 }).map((_, index) => (
              <div key={index} className="h-20 animate-pulse rounded-[2px] border border-border bg-surface" />
            ))}
          </div>
        ) : bindingQuery.data && bindingQuery.data.categories.length === 0 ? (
          <EmptyState
            title={t('knowledgeBase:detail.glossaryEmptyTitle')}
            description={t('knowledgeBase:detail.glossaryEmptyDescription')}
          />
        ) : (
          <div className="space-y-3">
            {bindingQuery.data?.categories.map((category) => {
              const checked = selectedIds.includes(category.id);

              return (
                <label
                  key={category.id}
                  className="flex cursor-pointer items-start gap-4 rounded-[2px] border border-border bg-surface/80 px-5 py-4 transition hover:bg-background-subtle"
                >
                  <input
                    type="checkbox"
                    aria-label={category.name}
                    className="mt-1 h-4 w-4 accent-primary"
                    checked={checked}
                    onChange={() =>
                      setSelectedIds((current) =>
                        current.includes(category.id)
                          ? current.filter((item) => item !== category.id)
                          : [...current, category.id],
                      )
                    }
                  />
                  <span className="min-w-0">
                    <span className="block text-sm font-semibold text-text">{category.name}</span>
                    <span className="mt-2 block text-sm leading-6 text-text-secondary">
                      {category.description?.trim() ? category.description : t('knowledgeBase:detail.glossaryDescriptionFallback')}
                    </span>
                  </span>
                </label>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
