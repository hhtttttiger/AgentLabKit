import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { cn } from '@/shared/lib/cn';
import { ArrowLeft, Ban, Pencil, Play, Plus } from 'lucide-react';
import { Badge } from '@/shared/ui/Badge';
import { Button } from '@/shared/ui/Button';
import { ConfirmDialog } from '@/shared/ui/ConfirmDialog';
import { InlineMessage } from '@/shared/ui/InlineMessage';
import { Skeleton } from '@/shared/ui/Skeleton';
import { StatusBadge } from '@/shared/ui/StatusBadge';
import { formatAdminDateTime } from '@/shared/i18n/formatters';
import { useAdminLocale } from '@/shared/i18n/useAdminLocale';
import { useAgent, useAgentMutations } from './hooks';
import { useRunList } from '@/modules/runs/hooks';
import { VersionList, type VersionLaunchAction } from '../versions/VersionList';
import { VersionDrawer } from '../versions/VersionDrawer';
import { useVersionDetail, useVersionList } from '../versions/hooks';
import { AuditList } from '../audits/AuditList';
import type { VersionDetailView } from '../../lib/contracts';

type Tab = 'build' | 'runs' | 'versions' | 'audits';

const am = 'agentManagement:';

const statusTone: Record<string, 'success' | 'warning' | 'neutral'> = {
  draft: 'warning',
  published: 'success',
  disabled: 'neutral',
};

function getTab(searchParams: URLSearchParams): Tab {
  const tab = searchParams.get('tab');
  const legacyBuildTabs = ['overview', 'prompt', 'capabilities', 'knowledge', 'evaluation'];
  if (!tab || legacyBuildTabs.includes(tab)) return 'build';
  const validTabs: Tab[] = ['build', 'runs', 'versions', 'audits'];
  return validTabs.includes(tab as Tab) ? (tab as Tab) : 'build';
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
  const [buildEditOpen, setBuildEditOpen] = useState(false);
  const [buildEditVersion, setBuildEditVersion] = useState<VersionDetailView | null>(null);
  const [buildSeed, setBuildSeed] = useState<VersionDetailView | null>(null);
  const [publishSuccess, setPublishSuccess] = useState(false);

  useEffect(() => {
    setActiveTab(getTab(searchParams));
  }, [searchParams]);

  useEffect(() => {
    if (activeTab !== 'build') setPublishSuccess(false);
  }, [activeTab]);

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
      setPublishSuccess(true);
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

  const buildVersionsQuery = useVersionList(agent.agentKey, { page: 1, pageSize: 100 });
  const hasPublished = agent.publishedVersionNumber !== null;
  const hasDraft = (buildVersionsQuery.data?.items ?? []).some((row) => row.versionStatus === 'draft');
  const canTestPublished = hasPublished;
  const testLabel = hasDraft ? `${am}agents.detail.testPublished` : `${am}agents.detail.test`;

  const tabs: { key: Tab; label: string }[] = [
    { key: 'build', label: t(`${am}agents.detail.tabBuild`) },
    { key: 'runs', label: t(`${am}agents.detail.tabRuns`) },
    { key: 'versions', label: t(`${am}agents.detail.tabVersions`) },
    { key: 'audits', label: t(`${am}agents.detail.tabAudits`) },
  ];

  const testAgent = () => navigate(`/playground?agent=${encodeURIComponent(agent.agentKey)}`);

  return (
    <div className="flex h-full flex-col">
      {/* Nav bar: back | breadcrumb | actions */}
      <header className="mm-grid-pattern border-b border-border bg-surface/70 px-8 py-3">
        <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={() => navigate('/agents')}
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
            {activeTab === 'build' && canTestPublished && (
              <Button variant="secondary" onClick={testAgent}><Play size={16} />{t(testLabel)}</Button>
            )}
            {activeTab === 'versions' && (
              <Button onClick={() => { setPublishSuccess(false); setCreateVersionTrigger((n) => n + 1); }}>
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
            {publishSuccess && activeTab === 'build' && (
              <div className="mx-6 mt-5 flex items-center justify-between gap-4 rounded-[2px] border border-success/30 bg-success/5 px-4 py-3 text-sm">
                <span className="text-text">{t(`${am}agents.detail.publishedSuccess`)}</span>
                <Button variant="secondary" onClick={testAgent}><Play size={14} />{t(`${am}agents.detail.testInPlayground`)}</Button>
              </div>
            )}
            {activeTab === 'build' && (
              <AgentBuildTab
                agent={agent}
                onEdit={(version, seed) => {
                  setPublishSuccess(false);
                  setBuildEditVersion(version);
                  setBuildSeed(seed);
                  setBuildEditOpen(true);
                }}
                onPublish={(version) => setPublishVersion({ versionNumber: version.versionNumber, rowVersion: version.rowVersion })}
                canTestPublished={canTestPublished}
                testLabel={testLabel}
              />
            )}
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
            {activeTab === 'runs' && <AgentRunsTab agentKey={agentKey!} />}
            {activeTab === 'audits' && <AuditList agentKey={agentKey!} />}
          </div>
        </div>
      </div>

      <VersionDrawer
        open={buildEditOpen}
        agentKey={agentKey!}
        editVersion={buildEditVersion}
        seedVersion={buildSeed}
        onClose={() => {
          setBuildEditOpen(false);
          setBuildEditVersion(null);
          setBuildSeed(null);
        }}
      />

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

function AgentBuildTab({
  agent,
  onEdit,
  onPublish,
  canTestPublished,
  testLabel,
}: {
  agent: AgentDetailPageAgent;
  onEdit: (version: VersionDetailView | null, seed: VersionDetailView | null) => void;
  onPublish: (version: VersionDetailView) => void;
  canTestPublished: boolean;
  testLabel: string;
}) {
  const { t } = useTranslation(['common', 'agentManagement']);
  const navigate = useNavigate();
  const versionsQuery = useVersionList(agent.agentKey, { page: 1, pageSize: 100 });
  const rows = versionsQuery.data?.items ?? [];
  const draftRow = rows.find((row) => row.versionStatus === 'draft') ?? null;
  const publishedRow = rows.find((row) => row.versionNumber === agent.publishedVersionNumber) ?? null;
  const displayRow = draftRow ?? publishedRow;
  const detailQuery = useVersionDetail(agent.agentKey, displayRow?.versionNumber ?? null);
  const version = detailQuery.data;
  const isEditable = draftRow !== null;

  if (versionsQuery.isLoading || (displayRow && detailQuery.isLoading)) {
    return <div className="p-6 text-sm text-text-muted">{t('common:states.loading')}</div>;
  }

  if (!version) {
    return (
      <div className="m-6 rounded-[2px] border border-border bg-background-subtle/40 p-6">
        <h2 className="text-lg font-semibold text-text">{t(`${am}agents.detail.setupTitle`)}</h2>
        <p className="mt-2 text-sm text-text-secondary">{t(`${am}agents.detail.setupDescription`)}</p>
        <div className="mt-5 space-y-2 text-sm text-text-secondary">
          <div>✓ {t(`${am}agents.detail.setupAgentCreated`)}</div>
          <div>○ {t(`${am}agents.detail.setupModel`)}</div>
          <div>○ {t(`${am}agents.detail.setupInstructions`)}</div>
        </div>
        <Button className="mt-5" onClick={() => onEdit(null, null)}><Plus size={15} />{t(`${am}agents.detail.configure`)}</Button>
      </div>
    );
  }

  const bindingCount = version.toolBindings.length + version.knowledgeBaseBindings.length + version.skillBindings.length + version.mcpBindings.length;
  return (
    <div className="space-y-4 p-6">
      {!isEditable && <InlineMessage tone="info">{t(`${am}agents.detail.publishedReadonlyInfo`)}</InlineMessage>}
      {isEditable && canTestPublished && <InlineMessage tone="info">{t(`${am}agents.detail.draftChangesNotPublished`)}</InlineMessage>}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="text-xs text-text-muted">{t(`${am}agents.detail.versionLabel`)}</div>
          <div className="mt-1 font-mono text-sm text-text">
            {isEditable && !canTestPublished
              ? t(`${am}agents.detail.draftNotPublished`, { versionNumber: version.versionNumber })
              : `v${version.versionNumber} · ${version.modelKey || t(`${am}agents.detail.notConfigured`)}`}
          </div>
        </div>
        <div className="flex gap-2">
          {isEditable ? <Button onClick={() => onPublish(version)}>{t(`${am}agents.detail.publishDraft`)}</Button> : <Button onClick={() => onEdit(null, version)}><Pencil size={14} />{t(`${am}agents.detail.editAgent`)}</Button>}
          {canTestPublished && (
            <Button variant="secondary" onClick={() => navigate(`/playground?agent=${encodeURIComponent(agent.agentKey)}`)}><Play size={14} />{t(testLabel)}</Button>
          )}
        </div>
      </div>
      <BuildSummary title={t(`${am}agents.detail.model`)} value={version.modelKey || t(`${am}agents.detail.notConfigured`)} />
      <BuildSummary title={t(`${am}agents.detail.instructions`)} help={t(`${am}agents.detail.instructionsHelp`)} value={version.systemPromptTemplate || t(`${am}agents.detail.notConfigured`)} multiline />
      <BuildSummary title={t(`${am}agents.detail.tools`)} value={version.toolBindings.length ? version.toolBindings.map((item) => item.displayName || item.toolName).join(', ') : t(`${am}agents.detail.noneConfigured`)} />
      <BuildSummary title={t(`${am}agents.detail.knowledge`)} value={version.knowledgeBaseBindings.length ? `${version.knowledgeBaseBindings.length} ${t(`${am}agents.detail.bindings`)}` : t(`${am}agents.detail.noneConfigured`)} />
      <BuildSummary title={t(`${am}agents.detail.skillsMcp`)} value={bindingCount - version.toolBindings.length - version.knowledgeBaseBindings.length ? `${version.skillBindings.length} skills · ${version.mcpBindings.length} MCP` : t(`${am}agents.detail.noneConfigured`)} />
      <BuildSummary title={t(`${am}agents.detail.advanced`)} value={Object.keys(version.runtimeOptions ?? {}).length || Object.keys(version.guardrailsPolicy ?? {}).length ? t(`${am}agents.detail.configured`) : t(`${am}agents.detail.default`)} />
    </div>
  );
}

type AgentDetailPageAgent = import('../../lib/contracts').AgentDetailView;

function BuildSummary({ title, value, help, multiline = false }: { title: string; value: string; help?: string; multiline?: boolean }) {
  return <section className="rounded-[2px] border border-border bg-surface p-4"><div className="flex items-center justify-between gap-3"><h2 className="text-sm font-semibold text-text">{title}</h2><span className="text-xs text-text-muted">{help}</span></div><p className={`mt-2 text-sm ${multiline ? 'max-w-3xl whitespace-pre-wrap leading-relaxed' : ''} text-text-secondary`}>{value}</p></section>;
}

function AgentRunsTab({ agentKey }: { agentKey: string }) {
  const { t } = useTranslation(['common', 'agentManagement', 'runs']);
  const navigate = useNavigate();
  const { data, isLoading, error } = useRunList({ agentKey });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-sm text-text-muted">{t('common:states.loading')}</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-sm text-error">{t('common:states.loadingFailed')}</div>
      </div>
    );
  }

  const runs = data?.items ?? [];

  if (runs.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <p className="text-sm text-text-muted">{t('agentManagement:agents.detail.noRuns')}</p>
        <button
          type="button"
          onClick={() => navigate(`/playground?agent=${encodeURIComponent(agentKey)}`)}
          className="mt-3 text-sm font-medium text-primary hover:underline"
        >
          {t('runs:empty.openPlayground')}
        </button>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="space-y-2">
        {runs.map((run) => (
          <button
            key={run.id}
            type="button"
            onClick={() => navigate(`/runs/${run.id}`)}
            className="flex w-full items-center justify-between rounded-[2px] border border-border bg-surface p-4 text-left transition hover:bg-surface-hover"
          >
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <StatusBadge status={run.status} />
                <span className="font-mono text-xs text-text-muted">{run.id.slice(0, 8)}</span>
              </div>
              {run.durationMs != null && (
                <span className="mt-1 text-xs text-text-muted">
                  {run.durationMs < 1000 ? `${run.durationMs}ms` : `${(run.durationMs / 1000).toFixed(2)}s`}
                </span>
              )}
            </div>
            <div className="text-xs text-text-muted">
              {formatAdminDateTime(run.startedAt)}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
