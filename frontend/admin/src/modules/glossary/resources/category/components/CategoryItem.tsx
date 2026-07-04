import { Button } from '@/shared/ui/Button';
import { cn } from '@/shared/lib/cn';
import { useTranslation } from 'react-i18next';
import type { GlossaryCategoryView } from '../../../lib/contracts';

export function CategoryItem({
  category,
  active,
  onSelect,
  onEdit,
  onDelete,
}: {
  category: GlossaryCategoryView;
  active: boolean;
  onSelect: () => void;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const { t } = useTranslation();
  return (
    <div
      className={cn(
        'rounded-[2px] border bg-surface/80 p-4 transition',
        active ? 'border-primary/35 bg-primary-subtle/50' : 'border-border hover:bg-background-subtle',
      )}
    >
      <button type="button" className="w-full text-left" onClick={onSelect}>
        <div className="text-sm font-semibold text-text">{category.name}</div>
        <div className="mt-2 text-sm leading-6 text-text-secondary">
          {category.description?.trim() ? category.description : t('modules.glossary.categoryItem.descriptionFallback')}
        </div>
      </button>
      <div className="mt-4 flex gap-2">
        <Button variant="secondary" className="min-h-control-sm px-3 py-2 text-xs" onClick={onEdit}>
          {t('modules.glossary.categoryItem.actions.edit')}
        </Button>
        <Button variant="ghost" className="min-h-control-sm px-3 py-2 text-xs" onClick={onDelete}>
          {t('modules.glossary.categoryItem.actions.delete')}
        </Button>
      </div>
    </div>
  );
}
