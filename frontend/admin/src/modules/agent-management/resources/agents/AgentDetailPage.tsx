import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { cn } from '@/shared/lib/cn';
import { ArrowLeft, Ban, Plus } from 'lucide-react';
import { Badge } from '@/shared/ui/Badge';
import { Button } from '@/shared/ui/Button';
import { ConfirmDialog } from '@/shared/ui/ConfirmDialog';
import { InlineMessage } from '@/shared/ui/InlineMessage';
import { Skeleton } from '@/shared/ui/Skeleton';
import { formatAdminDateTime } from '@/shared/i18n/formatters';
import { useAdminLocale } from '@/shared/i18n/useAdminLocale';
import { useAgent, useAgentMutations } from './hooks';
import { VersionList, type VersionLaunchAction } from '../versions/VersionList';
import { AuditList } from '../audits/AuditList';

type Tab = 'versions' | 'audits';

const am = 'agentManagement:';

const statusTone: Record<string, 'success' | 'warning' | 'neutral'> = {
  draft: 'warning',
  published: 'success',
  disabled: 'neutral',
};

function getTab(searchParams: URLSearchParams): Tab {
  return searchParams.get('tab') === 'audits' ? 'audits' : 'versions';
}

function getLaunchAction(searchParams: URLSearchParams): VersionLaunchAction | null {
  const action = searchParams.get('action');
  const versionParam = searchParams.get('version');
  const versionNumber = versionParam ? Number(versionParam) : null;
  const key = searchParams.toString();

  if (action === 'create') {
    return { kind: 'create', key };
  }

  if (!versionNumber || Number.isNaN(versionNumber)) {
    return null;
  }

  if (action === 'edit') {
    return { kind: 'edit', versionNumber, key };
  }

  if (action === 'view') {
    return { kind: 'view', versionNumber, key };
  }

  if (action === 'clone') {
    return { kind: 'clone', versionNumber, key };
  }

  return null;
}

export function AgentDetailPage() {
  const { t } = useTranslation(['common', 'agentManagement']);
  const { agentKey } = useParams<{ agentKey: string }>();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const agentQuery = useAgent(agentKey ?? '');
  const mutations = useAgentMutations();
  useAdminLocale();

  const [activeTab, setActiveTab] = useState<Tab>(() => getTab(searchParams));
  const [publishVersion, setPublishVersion] = useState<{
    versionNumber: number;
    rowVersion: number;
  } | null>(null);
  const [disableOpen, setDisableOpen] = useState(false);
  const [createVersionTrigger, setCreateVersionTrigger] = useState(0);

  useEffect(() => {
    setActiveTab(getTab(searchParams));
  }, [searchParams]);

  const versionLaunchAction = useMemo(() => getLaunchAction(searchParams), [searchParams]);

  const handleTabChange = useCallback(
    (tab: Tab) => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          next.set('tab', tab);
          return next;
        },
        { replace: true },
      );
    },
    [setSearchParams],
  );

  const agent = agentQuery.data;

  if (agentQuery.isLoading) {
    return (
      <div className="flex h-full flex-col">
        <header className="mm-grid-pattern border-b border-border bg-surface/70 px-8 py-3">
          <div className="h-8 w-40 animate-pulse rounded-lg bg-background-subtle" />
        </header>
        <div className="flex min-h-0 flex-1 flex-col px-8 pt-5 pb-3">
          <Skeleton />
        </div>
      </div>
    );
  }

  if (agentQuery.isError || !agent) {
    return (
      <div className="flex h-full flex-col">
        <header className="mm-grid-pattern border-b border-border bg-surface/70 px-8 py-3">
          <span className="text-base font-semibold text-text">{t(`${am}agents.detail.eyebrow`)}</span>
        </header>
        <div className="flex min-h-0 flex-1 flex-col px-8 pt-5 pb-3">
          <InlineMessage tone="error">
            {mutations.getMutationMessage(agentQuery.error ?? new Error(t(`${am}agents.detail.agentNotFound`)))}
          </InlineMessage>
        </div>
      </div>
    );
  }

  const handlePublish = async () => {
    if (!publishVersion || !agentKey) return;
    try {
      await mutations.publish.mutateAsync({
        agentKey,
        model: {
          versionNumber: publishVersion.versionNumber,
          definitionRowVersion: agent.rowVersion,
          versionRowVersion: publishVersion.rowVersion,
        },
      });
      setPublishVersion(null);
    } catch {
      // surfaced by the mutation state
    }
  };

  const handleDisable = async () => {
    if (!agentKey) return;
    try {
      await mutations.disable.mutateAsync({
        agentKey,
        model: { reason: null, rowVersion: agent.rowVersion },
      });
      setDisableOpen(false);
    } catch {
      // surfaced by the mutation state
    }
  };

  const tabs: { key: Tab; label: string }[] = [
    { key: 'versions', label: t(`${am}agents.detail.tabVersions`) },
    { key: 'audits', label: t(`${am}agents.detail.tabAudits`) },
  ];

  return (
    <div className="flex h-full flex-col">
      {/* Nav bar: back | breadcrumb | actions */}
      <header className="mm-grid-pattern border-b border-border bg-surface/70 px-8 py-3">
        <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={() => navigate('/agent-management/agents')}
              className="flex h-8 w-8 items-center justify-center rounded-lg text-text-secondary transition hover:bg-state-hover hover:text-text"
              title={t(`${am}agents.detail.backTitle`)}
            >
              <ArrowLeft size={18} />
            </button>
            <div className="flex items-baseline gap-1.5">
              <span className="text-xs font-medium text-text-muted">{t(`${am}agents.detail.breadcrumb`)}</span>
              <span className="text-xs text-border">/</span>
              <h1 className="text-base font-semibold text-text">{agent.displayName}</h1>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            {activeTab === 'versions' && (
              <Button onClick={() => setCreateVersionTrigger((n) => n + 1)}>
                <Plus size={16} />
                {t(`${am}agents.detail.createVersion`)}
              </Button>
            )}
            {agent.status !== 'disabled' && (
              <Button
                variant="ghost"
                className="rounded-[2px] border border-border"
                onClick={() => setDisableOpen(true)}
              >
                <Ban size={16} />
                {t(`${am}agents.detail.disable`)}
              </Button>
            )}
          </div>
        </div>
      </header>

      {/* Content area */}
      <div className="flex min-h-0 flex-1 flex-col px-8 pt-5 pb-3">
        {/* Single merged box: fixed agent info + scrollable list */}
        <div className="flex flex-1 flex-col overflow-hidden rounded-[2px] border border-border bg-surface">
          {/* Fixed: Agent info */}
          <div
            data-testid="agent-detail-top"
            className="shrink-0 border-b border-border px-8 py-6"
          >
            <div data-testid="agent-detail-title-row" className="flex flex-wrap items-start gap-3">
              <div className="min-w-0 flex-1">
                <div className="text-xs font-semibold uppercase tracking-[0.18em] text-primary">
                  {t(`${am}agents.detail.eyebrow`)}
                </div>
                <div className="mt-2 flex flex-wrap items-center gap-3">
                  <h2 className="text-[1.75rem] font-semibold leading-tight tracking-[-0.03em] text-text">
                    {agent.displayName}
                  </h2>
                  <Badge tone={statusTone[agent.status] ?? 'neutral'}>
                    {t(`${am}status.${agent.status}`, { defaultValue: agent.status })}
                  </Badge>
                </div>
                {agent.description ? (
                  <p className="mt-2 max-w-2xl text-sm leading-relaxed text-text-secondary">{agent.description}</p>
                ) : null}
              </div>
            </div>

            <div
              data-testid="agent-detail-info-row"
              className="mt-5 overflow-hidden rounded-[2px] border border-border-subtle bg-background-subtle/40"
            >
              <div className="grid grid-cols-2 divide-x divide-y divide-border-subtle xl:grid-cols-4">
                <div className="px-5 py-3.5">
                  <div className="text-[11px] uppercase tracking-[0.16em] text-text-muted">Agent Key</div>
                  <div className="mt-1.5 font-mono text-[13px] text-text">{agent.agentKey}</div>
                </div>
                <div className="px-5 py-3.5">
                  <div className="text-[11px] uppercase tracking-[0.16em] text-text-muted">
                    {t(`${am}agents.detail.publishedVersion`)}
                  </div>
                  <div className="mt-1.5 font-semibold text-[13px] text-text">
                    {agent.publishedVersionNumber !== null
                      ? `v${agent.publishedVersionNumber}`
                      : t(`${am}agents.detail.notPublished`)}
                  </div>
                </div>
                <div className="px-5 py-3.5">
                  <div className="text-[11px] uppercase tracking-[0.16em] text-text-muted">
                    {t(`${am}agents.detail.createdAt`)}
                  </div>
                  <div className="mt-1.5 font-semibold text-[13px] text-text">
                    {formatAdminDateTime(agent.createdAtUtc)}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Fixed: Mutation error banner */}
          {(mutations.publish.error || mutations.disable.error) && (
            <div className="shrink-0 border-b border-border px-8 py-3">
              <InlineMessage tone="error">
                {mutations.getMutationMessage(mutations.publish.error ?? mutations.disable.error)}
              </InlineMessage>
            </div>
          )}

          {/* Fixed: Tab bar */}
          <div
            data-testid="agent-detail-workspace"
            className="shrink-0 border-b border-border px-2"
          >
            <div role="tablist" aria-label={t(`${am}agents.detail.ariaLabel`)} className="flex">
              {tabs.map((tab) => (
                <button
                  key={tab.key}
                  type="button"
                  role="tab"
                  aria-selected={activeTab === tab.key}
                  onClick={() => handleTabChange(tab.key)}
                  className={cn(
                    'relative px-5 py-3.5 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30',
                    activeTab === tab.key
                      ? 'text-primary after:absolute after:bottom-0 after:left-0 after:right-0 after:h-0.5 after:rounded-full after:bg-primary'
                      : 'text-text-secondary hover:text-text',
                  )}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          </div>

          {/* Scrollable: Tab content */}
          <div className="flex-1 overflow-y-auto">
            {activeTab === 'versions' && (
              <VersionList
                agentKey={agentKey!}
                createTrigger={createVersionTrigger}
                launchAction={versionLaunchAction}
                onPublish={(versionNumber, rowVersion) =>
                  setPublishVersion({ versionNumber, rowVersion })
                }
              />
            )}
            {activeTab === 'audits' && <AuditList agentKey={agentKey!} />}
          </div>
        </div>
      </div>

      <ConfirmDialog
        open={publishVersion !== null}
        title={t(`${am}agents.detail.confirmPublish.title`)}
        description={t(`${am}agents.detail.confirmPublish.description`, {
          versionNumber: publishVersion?.versionNumber ?? '',
        })}
        confirmLabel={t(`${am}agents.detail.confirmPublish.label`)}
        tone="primary"
        body={t(`${am}agents.detail.confirmPublish.body`)}
        error={mutations.publish.error ? mutations.getMutationMessage(mutations.publish.error) : null}
        loading={mutations.publish.isPending}
        onClose={() => {
          setPublishVersion(null);
          mutations.publish.reset();
        }}
        onConfirm={handlePublish}
      />

      <ConfirmDialog
        open={disableOpen}
        title={t(`${am}agents.detail.confirmDisable.title`)}
        description={t(`${am}agents.detail.confirmDisable.description`, { name: agent.displayName })}
        confirmLabel={t(`${am}agents.detail.confirmDisable.label`)}
        body={t(`${am}agents.detail.confirmDisable.body`)}
        error={mutations.disable.error ? mutations.getMutationMessage(mutations.disable.error) : null}
        loading={mutations.disable.isPending}
        onClose={() => {
          setDisableOpen(false);
          mutations.disable.reset();
        }}
        onConfirm={handleDisable}
      />
    </div>
  );
}
