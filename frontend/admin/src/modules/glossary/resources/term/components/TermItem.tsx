import { Button } from '@/shared/ui/Button';
import { cn } from '@/shared/lib/cn';
import { useTranslation } from 'react-i18next';
import type { GlossaryTermView } from '../../../lib/contracts';

export function TermItem({
  term,
  onEdit,
  onDelete,
}: {
  term: GlossaryTermView;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const { t } = useTranslation();
  return (
    <div className={cn('rounded-[2px] border border-border bg-surface/80 p-4 transition hover:bg-background-subtle')}>
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="text-sm font-semibold text-text">{term.term}</div>
          <div className="mt-2 flex flex-wrap gap-2">
            {term.synonyms.length > 0 ? (
              term.synonyms.map((item) => (
                <span key={item} className="rounded-full border border-border px-2.5 py-1 text-xs text-text-secondary">
                  {item}
                </span>
              ))
            ) : (
              <span className="text-xs text-text-muted">{t('modules.glossary.termItem.noSynonyms')}</span>
            )}
          </div>
        </div>
        <div className="flex shrink-0 gap-2">
          <Button variant="secondary" className="min-h-control-sm px-3 py-2 text-xs" onClick={onEdit}>
            {t('modules.glossary.termItem.actions.edit')}
          </Button>
          <Button variant="ghost" className="min-h-control-sm px-3 py-2 text-xs" onClick={onDelete}>
            {t('modules.glossary.termItem.actions.delete')}
          </Button>
        </div>
      </div>
    </div>
  );
}
