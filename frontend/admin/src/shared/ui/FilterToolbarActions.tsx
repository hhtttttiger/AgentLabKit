import { type PropsWithChildren } from 'react';
import { RefreshCw } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { ToolbarButton } from './ToolbarButton';

interface FilterToolbarActionsProps {
  /** Called when the user clicks the refresh button. */
  onRefresh: () => void;
  /** When true the refresh button shows a spinning icon and is disabled. */
  refreshing?: boolean;
  /** Called when the user clicks the reset button. Resets all filter fields to defaults. */
  onReset: () => void;
  /** Optional extra buttons (e.g. a "新建" CTA) rendered after refresh/reset. */
  children?: React.ReactNode;
}

/**
 * Standard action group for `FilterToolbar`'s `actions` slot.
 *
 * Renders: [刷新] [重置] [children…]
 *
 * Usage:
 * ```tsx
 * <FilterToolbar
 *   actions={
 *     <FilterToolbarActions
 *       onRefresh={() => listQuery.refetch()}
 *       refreshing={listQuery.isFetching}
 *       onReset={() => setFilters(defaultFilters)}
 *     >
 *       <ToolbarButton variant="primary" onClick={() => setCreateOpen(true)}>
 *         <Plus size={14} /> 新建
 *       </ToolbarButton>
 *     </FilterToolbarActions>
 *   }
 * >
 *   ...filters...
 * </FilterToolbar>
 * ```
 */
export function FilterToolbarActions({
  onRefresh,
  refreshing = false,
  onReset,
  children,
}: PropsWithChildren<FilterToolbarActionsProps>) {
  const { t } = useTranslation('common');

  return (
    <div className="flex gap-2">
      <ToolbarButton variant="secondary" onClick={onRefresh} disabled={refreshing}>
        <RefreshCw size={14} className={refreshing ? 'animate-spin' : undefined} />
        {t('actions.refresh')}
      </ToolbarButton>
      <ToolbarButton variant="secondary" onClick={onReset}>
        {t('actions.reset')}
      </ToolbarButton>
      {children}
    </div>
  );
}
