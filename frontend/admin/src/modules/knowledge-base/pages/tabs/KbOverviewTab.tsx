import { useMemo } from 'react';
import { useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Activity, AlignLeft, BookOpen, Calendar, Clock, FileText } from 'lucide-react';
import { Card } from '@/shared/ui/Card';
import { Badge } from '@/shared/ui/Badge';
import { MetricStrip } from '@/shared/ui/MetricStrip';
import { formatAdminDateTime, formatAdminNumber } from '@/shared/i18n/formatters';
import { useAdminLocale } from '@/shared/i18n/useAdminLocale';
import { useKbDetail } from '../../resources/knowledge-base/hooks';
import { KbTopRecalledPanel } from '../../resources/ranking/components/KbTopRecalledPanel';
import { useTopRecalledDocuments } from '../../resources/ranking/hooks';
import type { KbStatus } from '../../lib/contracts';
import { parseKbSettingsJson } from '../../resources/knowledge-base/settings';

const statusTone: Record<KbStatus, 'success' | 'warning' | 'neutral' | 'danger'> = {
  Active: 'success',
  Processing: 'warning',
  Disabled: 'neutral',
  Deleted: 'danger',
};

export function KbOverviewTab() {
  const { t } = useTranslation(['knowledgeBase']);
  const { kbId } = useParams<{ kbId: string }>();
  const detailQuery = useKbDetail(kbId);
  const rankingQuery = useTopRecalledDocuments(kbId ?? '', 30);
  const kb = detailQuery.data;
  useAdminLocale();

  const totalRecalls = useMemo(
    () => (rankingQuery.data ?? []).reduce((sum, d) => sum + d.recallCount, 0),
    [rankingQuery.data],
  );

  if (detailQuery.isLoading) {
    return (
      <div className="overflow-y-auto">
        <div className="animate-pulse space-y-5">
          <div className="grid grid-cols-3 gap-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-[5.5rem] rounded-[2px] bg-surface" />
            ))}
          </div>
          <div className="h-52 rounded-[2px] bg-surface" />
          <div className="h-28 rounded-[2px] bg-surface" />
        </div>
      </div>
    );
  }

  if (!kb) return null;
  const parsedSettings = parseKbSettingsJson(kb.settingsJson);

  return (
    <div className="overflow-y-auto">
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
          <div className="space-y-6">
            {/* ── Hero Metrics ── */}
            <MetricStrip
              columns={3}
              items={[
                { label: t('knowledgeBase:overview.documents'), value: formatAdminNumber(kb.documentCount), hint: t('knowledgeBase:overview.documentsHint') },
                { label: t('knowledgeBase:overview.totalRecalls'), value: formatAdminNumber(totalRecalls), hint: t('knowledgeBase:overview.totalRecallsHint') },
                {
                  label: t('knowledgeBase:overview.status'),
                  value: <Badge tone={statusTone[kb.status] ?? 'neutral'}>{t(`knowledgeBase:kbStatus.${kb.status}`, { defaultValue: formatKbStatus(kb.status) })}</Badge>,
                  hint: t('knowledgeBase:overview.statusHint'),
                },
              ]}
            />

            {/* ── Properties ── */}
            <Card title={t('knowledgeBase:overview.details')}>
              <div className="grid grid-cols-[140px_minmax(0,1fr)] gap-x-6 gap-y-4">
                <PropertyRow icon={<BookOpen size={14} />} label={t('knowledgeBase:overview.fieldName')}>
                  <span className="text-sm text-text">{kb.name}</span>
                </PropertyRow>
                <PropertyRow icon={<Activity size={14} />} label={t('knowledgeBase:overview.fieldStatus')}>
                  <Badge tone={statusTone[kb.status] ?? 'neutral'}>{t(`knowledgeBase:kbStatus.${kb.status}`, { defaultValue: formatKbStatus(kb.status) })}</Badge>
                </PropertyRow>
                <PropertyRow icon={<FileText size={14} />} label={t('knowledgeBase:overview.fieldDocuments')}>
                  <span className="text-sm text-text">{formatAdminNumber(kb.documentCount)}</span>
                </PropertyRow>
                <PropertyRow icon={<AlignLeft size={14} />} label={t('knowledgeBase:overview.fieldDescription')}>
                  <span className="text-sm text-text-secondary">{kb.description ?? '—'}</span>
                </PropertyRow>
                <PropertyRow icon={<Calendar size={14} />} label={t('knowledgeBase:overview.fieldCreatedAt')}>
                  <span className="text-sm text-text-secondary">{formatAdminDateTime(kb.createdAtUtc)}</span>
                </PropertyRow>
                <PropertyRow icon={<Clock size={14} />} label={t('knowledgeBase:overview.fieldUpdatedAt')}>
                  <span className="text-sm text-text-secondary">{kb.updatedAtUtc ? formatAdminDateTime(kb.updatedAtUtc) : '—'}</span>
                </PropertyRow>
              </div>
            </Card>

            {/* ── Settings JSON ── */}
            {kb.settingsJson && (
              <Card title={t('knowledgeBase:overview.settings')}>
                <div className="space-y-4">
                  <div className="grid gap-3 md:grid-cols-2">
                    <SummaryItem label={t('knowledgeBase:overview.provider')} value={parsedSettings.provider === 'azure' ? 'Azure' : 'Local'} />
                    <SummaryItem label={t('knowledgeBase:overview.azureProfile')} value={parsedSettings.azure.profileId || '—'} />
                    {parsedSettings.provider === 'local' ? (
                      <>
                        <SummaryItem label={t('knowledgeBase:overview.chunkLength')} value={formatAdminNumber(parsedSettings.local.maxLength)} />
                        <SummaryItem label={t('knowledgeBase:overview.chunkOverlap')} value={formatAdminNumber(parsedSettings.local.overlap)} />
                        <SummaryItem label={t('knowledgeBase:overview.splitter')} value={parsedSettings.local.splitter} />
                        <SummaryItem
                          label={t('knowledgeBase:overview.recallSources')}
                          value={parsedSettings.recallSources.length > 0 ? parsedSettings.recallSources.join(', ') : t('knowledgeBase:overview.recallSourcesLocalOnly')}
                        />
                      </>
                    ) : (
                      <SummaryItem label={t('knowledgeBase:overview.recallSources')} value={t('knowledgeBase:overview.azureManaged')} />
                    )}
                  </div>
                  <div className="overflow-x-auto rounded-[2px] border border-border-subtle bg-background-subtle">
                    <pre className="p-4 text-[13px] leading-relaxed text-text-secondary">
                      {(() => {
                        try {
                          return JSON.stringify(JSON.parse(kb.settingsJson), null, 2);
                        } catch {
                          return kb.settingsJson;
                        }
                      })()}
                    </pre>
                  </div>
                </div>
              </Card>
            )}
          </div>

          <KbTopRecalledPanel
            documents={rankingQuery.data ?? []}
            loading={rankingQuery.isLoading}
          />
        </div>
      </div>
  );
}

/* ── helpers ── */

function PropertyRow({ icon, label, children }: { icon: React.ReactNode; label: string; children: React.ReactNode }) {
  return (
    <>
      <div className="flex items-center gap-2 text-sm font-medium text-text-secondary">
        <span className="shrink-0 text-text-muted">{icon}</span>
        <span>{label}</span>
      </div>
      <div className="flex items-center text-sm">{children}</div>
    </>
  );
}

function SummaryItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[2px] border border-border-subtle bg-background-subtle px-4 py-3">
      <div className="text-xs font-medium uppercase tracking-[0.08em] text-text-muted">{label}</div>
      <div className="mt-2 text-sm text-text">{value}</div>
    </div>
  );
}

function formatKbStatus(status: KbStatus) {
  return status.charAt(0).toUpperCase() + status.slice(1);
}
