import { useMemo } from 'react';
import { useParams } from 'react-router-dom';
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

const statusLabel: Record<KbStatus, string> = {
  Active: '活跃',
  Processing: '处理中',
  Disabled: '已禁用',
  Deleted: '已删除',
};

export function KbOverviewTab() {
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
                { label: '文档数量', value: formatAdminNumber(kb.documentCount), hint: '知识库中的文档总数' },
                { label: '累计召回', value: formatAdminNumber(totalRecalls), hint: '所有文档的累计召回总次数' },
                {
                  label: '状态',
                  value: <Badge tone={statusTone[kb.status] ?? 'neutral'}>{statusLabel[kb.status] ?? kb.status}</Badge>,
                  hint: '当前知识库运行状态',
                },
              ]}
            />

            {/* ── Properties ── */}
            <Card title="基本信息">
              <div className="grid grid-cols-[140px_minmax(0,1fr)] gap-x-6 gap-y-4">
                <PropertyRow icon={<BookOpen size={14} />} label="名称">
                  <span className="text-sm text-text">{kb.name}</span>
                </PropertyRow>
                <PropertyRow icon={<Activity size={14} />} label="状态">
                  <Badge tone={statusTone[kb.status] ?? 'neutral'}>{statusLabel[kb.status] ?? kb.status}</Badge>
                </PropertyRow>
                <PropertyRow icon={<FileText size={14} />} label="文档数量">
                  <span className="text-sm text-text">{formatAdminNumber(kb.documentCount)}</span>
                </PropertyRow>
                <PropertyRow icon={<AlignLeft size={14} />} label="描述">
                  <span className="text-sm text-text-secondary">{kb.description ?? '—'}</span>
                </PropertyRow>
                <PropertyRow icon={<Calendar size={14} />} label="创建时间">
                  <span className="text-sm text-text-secondary">{formatAdminDateTime(kb.createdAtUtc)}</span>
                </PropertyRow>
                <PropertyRow icon={<Clock size={14} />} label="更新时间">
                  <span className="text-sm text-text-secondary">{kb.updatedAtUtc ? formatAdminDateTime(kb.updatedAtUtc) : '—'}</span>
                </PropertyRow>
              </div>
            </Card>

            {/* ── Settings JSON ── */}
            {kb.settingsJson && (
              <Card title="配置">
                <div className="space-y-4">
                  <div className="grid gap-3 md:grid-cols-2">
                    <SummaryItem label="Provider" value={parsedSettings.provider === 'azure' ? 'Azure' : 'Local'} />
                    <SummaryItem label="Azure Profile" value={parsedSettings.azure.profileId || '—'} />
                    {parsedSettings.provider === 'local' ? (
                      <>
                        <SummaryItem label="Chunk Length" value={formatAdminNumber(parsedSettings.local.maxLength)} />
                        <SummaryItem label="Chunk Overlap" value={formatAdminNumber(parsedSettings.local.overlap)} />
                        <SummaryItem label="Splitter" value={parsedSettings.local.splitter} />
                        <SummaryItem
                          label="Recall Sources"
                          value={parsedSettings.recallSources.length > 0 ? parsedSettings.recallSources.join(', ') : 'local only'}
                        />
                      </>
                    ) : (
                      <SummaryItem label="Recall Sources" value="managed Azure search" />
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
