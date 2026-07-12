import { useAlertList, useAcknowledgeAlert, useEvaluateAlerts } from './hooks';
import { useTranslation } from 'react-i18next';
import { Button } from '@/shared/ui/Button';
import { EmptyState } from '@/shared/ui/EmptyState';
import { InlineMessage } from '@/shared/ui/InlineMessage';
import { SkeletonRows } from '@/shared/ui/Skeleton';
import { formatCost } from '../../lib/formatters';
import type { AlertData } from '../../lib/contracts';

export function AlertsPage() {
  const { t } = useTranslation(['common', 'costAnalysis']);
  const { data: alerts, isLoading, isError, error, refetch } = useAlertList();
  const ackMutation = useAcknowledgeAlert();
  const evalMutation = useEvaluateAlerts();

  if (isLoading) {
    return <div className="p-6"><SkeletonRows columns={7} rows={5} /></div>;
  }

  if (isError) {
    return (
      <div className="p-6">
        <InlineMessage tone="error">
          {error?.message ?? t('costAnalysis:alerts.error')}
        </InlineMessage>
      </div>
    );
  }

  const unacknowledged = alerts?.filter((a: AlertData) => !a.acknowledgedAtUtc) ?? [];

  return (
    <div className="flex flex-col gap-4 p-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-text">
          {t('costAnalysis:alerts.title')}
          {unacknowledged.length > 0 && (
            <span
              className="ml-2 inline-block rounded-full bg-error/10 px-2 py-0.5 text-xs text-error"
              aria-label={`${unacknowledged.length} ${t('costAnalysis:alerts.statusLabel.pending')}`}
            >
              {unacknowledged.length}
            </span>
          )}
        </h2>
        <Button
          onClick={() => evalMutation.mutateAsync().then(() => refetch())}
          disabled={evalMutation.isPending}
        >
          {t('costAnalysis:alerts.evaluate')}
        </Button>
      </div>

      {!alerts?.length ? (
        <EmptyState title={t('costAnalysis:alerts.emptyTitle')} description={t('costAnalysis:alerts.emptyDescription')} />
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-text-muted">
              <th className="pb-2 font-medium">{t('costAnalysis:alerts.tableHeaders.type')}</th>
              <th className="pb-2 font-medium">{t('costAnalysis:alerts.tableHeaders.scope')}</th>
              <th className="pb-2 font-medium text-right">{t('costAnalysis:alerts.tableHeaders.currentSpend')}</th>
              <th className="pb-2 font-medium text-right">{t('costAnalysis:alerts.tableHeaders.threshold')}</th>
              <th className="pb-2 font-medium">{t('costAnalysis:alerts.tableHeaders.triggeredAt')}</th>
              <th className="pb-2 font-medium text-center">{t('costAnalysis:alerts.tableHeaders.status')}</th>
              <th className="pb-2 font-medium text-right">{t('costAnalysis:alerts.tableHeaders.actions')}</th>
            </tr>
          </thead>
          <tbody>
            {alerts.map((a: AlertData) => (
              <tr key={a.id} className={`border-b border-border-subtle last:border-0 ${!a.acknowledgedAtUtc ? 'bg-warning/3' : ''}`}>
                <td className="py-2">
                  <span className={`inline-block rounded-[2px] px-2 py-0.5 text-xs ${a.alertType === 'exceeded' ? 'bg-error/10 text-error' : 'bg-warning/10 text-warning'}`}>
                    {t(`costAnalysis:alerts.typeLabel.${a.alertType}`, a.alertType)}
                  </span>
                </td>
                <td className="py-2 text-text-secondary">{a.scopeType}: {a.scopeKey}</td>
                <td className="py-2 text-right font-medium text-text">{formatCost(a.currentSpendUsd)}</td>
                <td className="py-2 text-right text-text-secondary">{formatCost(a.thresholdUsd)}</td>
                <td className="py-2 text-text-secondary">{new Date(a.triggeredAtUtc).toLocaleString()}</td>
                <td className="py-2 text-center">
                  {a.acknowledgedAtUtc ? (
                    <span className="text-xs text-success">{t('costAnalysis:alerts.statusLabel.acknowledged')}</span>
                  ) : (
                    <span className="text-xs text-warning">{t('costAnalysis:alerts.statusLabel.pending')}</span>
                  )}
                </td>
                <td className="py-2 text-right">
                  {!a.acknowledgedAtUtc && (
                    <button
                      className="text-xs text-primary hover:underline"
                      onClick={() => ackMutation.mutateAsync(a.id).then(() => refetch())}
                      aria-label={`${t('costAnalysis:alerts.acknowledge')} ${a.id}`}
                    >
                      {t('costAnalysis:alerts.acknowledge')}
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
