import { Activity, AlertTriangle, Clock, Zap } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { formatCompact, formatLatency } from '../lib/formatters';
import type { ModelUsageSummary } from '../lib/contracts';

type CardProps = {
  card: ModelUsageSummary;
  onClick?: (modelKey: string) => void;
};

/**
 * Shared model-summary card used in both the overview page and the usage grid view.
 */
export function ModelSummaryCard({ card, onClick }: CardProps) {
  const { t } = useTranslation(['common', 'modelMonitoring']);

  const content = (
    <>
      <div className="min-w-0">
        <div className="text-base font-semibold text-text">{card.displayName}</div>
        <div className="mt-1 text-xs text-text-muted">{card.modelKey}</div>
      </div>
      <div className="mt-4 grid grid-cols-2 gap-3">
        <div className="flex items-center gap-2 text-xs text-text-muted">
          <Zap size={13} className="shrink-0 text-primary" />
          <span>{t('modelMonitoring:overview.card.requests', { value: formatCompact(card.totalRequests) })}</span>
        </div>
        <div className="flex items-center gap-2 text-xs text-text-muted">
          <Activity size={13} className="shrink-0 text-primary" />
          <span>{t('modelMonitoring:overview.card.tokens', { value: formatCompact(card.totalInputTokens + card.totalOutputTokens) })}</span>
        </div>
        <div className="flex items-center gap-2 text-xs text-text-muted">
          <Clock size={13} className="shrink-0 text-text-muted" />
          <span>{formatLatency(card.averageLatencyMs)}</span>
        </div>
        <div className="flex items-center gap-2 text-xs text-text-muted">
          <AlertTriangle size={13} className="shrink-0 text-warning-text" />
          <span>{t('modelMonitoring:overview.card.errors', { value: card.errorCount })}</span>
        </div>
      </div>
    </>
  );

  const className =
    'group flex flex-col rounded-[2px] border border-border bg-surface/80 p-5 transition hover:border-primary/40';

  if (onClick) {
    return (
      <button
        type="button"
        onClick={() => onClick(card.modelKey)}
        className={`${className} text-left cursor-pointer`}
      >
        {content}
      </button>
    );
  }

  return <div className={className}>{content}</div>;
}
