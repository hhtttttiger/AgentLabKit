/**
 * PlaygroundShell — Reorganized layout for the Playground.
 *
 * Structure:
 *   SessionSidebar | ConversationPane | RunInspector
 *
 * This component wraps the existing session/stream logic
 * and provides a cleaner separation of concerns.
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { ExternalLink } from 'lucide-react';
import { cn } from '@/shared/lib/cn';
import { AgentTraceView } from '@/shared/agent-trace/AgentTraceView';
import type { ChatSession, ModelOption } from '../lib/contracts';
import { ChatInputArea } from './ChatInputArea';
import { ChatMessagePanel } from './ChatMessagePanel';
import { SessionList } from './SessionList';
import { useRunDetail, useRunCost, useRunEvaluation } from '@/modules/runs/hooks';
import { StatusBadge } from '@/shared/ui/StatusBadge';

type InspectorTab = 'run' | 'trace' | 'tools' | 'context' | 'cost' | 'eval';

interface PlaygroundShellProps {
  // Session state
  sessions: ChatSession[];
  currentSession: ChatSession | null;
  isLoadingMessages: boolean;
  selectedTraceMessageId: string | null;

  // Model state
  agentOptions: ModelOption[];
  modelOptions: ModelOption[];
  selectedModel: ModelOption | null;

  // Streaming state
  isStreaming: boolean;

  // Callbacks
  onSelectSession: (session: ChatSession) => void;
  onDeleteSession: (id: string | number) => void;
  onNewChat: () => void;
  onSelectTrace: (messageId: string) => void;
  onRegenerate: (assistantMessageId: string) => Promise<void>;
  onSend: (message: string) => void;
  onStop: () => void;
  onSelectModel: (model: ModelOption) => void;

  // Trace data
  currentTrace: ReturnType<typeof AgentTraceView>['props']['trace'] | null;
}

export function PlaygroundShell({
  sessions,
  currentSession,
  isLoadingMessages,
  selectedTraceMessageId,
  agentOptions,
  modelOptions,
  selectedModel,
  isStreaming,
  onSelectSession,
  onDeleteSession,
  onNewChat,
  onSelectTrace,
  onRegenerate,
  onSend,
  onStop,
  onSelectModel,
  currentTrace,
}: PlaygroundShellProps) {
  const { t } = useTranslation(['common', 'aiChat']);
  const navigate = useNavigate();
  const [activeInspectorTab, setActiveInspectorTab] = useState<InspectorTab>('trace');

  // Get the runId from the current trace for linking to Run Detail
  const runId = currentTrace?.runId ?? null;

  const inspectorTabs: Array<{ id: InspectorTab; label: string }> = [
    { id: 'run', label: t('aiChat:inspector.tabs.run') },
    { id: 'trace', label: t('aiChat:inspector.tabs.trace') },
    { id: 'tools', label: t('aiChat:inspector.tabs.tools') },
    { id: 'context', label: t('aiChat:inspector.tabs.context') },
    { id: 'cost', label: t('aiChat:inspector.tabs.cost') },
    { id: 'eval', label: t('aiChat:inspector.tabs.eval') },
  ];

  return (
    <div className="flex h-full min-h-0 gap-5 overflow-hidden bg-transparent p-5">
      {/* Session Sidebar */}
      <SessionList
        sessions={sessions}
        currentSessionId={currentSession?.id ?? null}
        onSelect={onSelectSession}
        onDelete={onDeleteSession}
        onNewChat={onNewChat}
      />

      {/* Main Content Area */}
      <div className="flex min-h-0 min-w-0 flex-1 gap-5">
        {/* Conversation Pane */}
        <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden rounded-[2px] border border-border bg-surface dark:bg-surface">
          <ChatMessagePanel
            messages={currentSession?.messages ?? []}
            isLoading={isLoadingMessages}
            selectedTraceMessageId={selectedTraceMessageId}
            onSelectTrace={onSelectTrace}
            onRegenerate={(messageId) => { void onRegenerate(messageId); }}
          />
          <ChatInputArea
            onSend={onSend}
            onStop={onStop}
            disabled={!selectedModel}
            isStreaming={isStreaming}
            agentOptions={agentOptions}
            modelOptions={modelOptions}
            selectedModel={selectedModel}
            onSelectModel={onSelectModel}
          />
        </div>

        {/* Run Inspector */}
        <div
          className={cn(
            'min-h-0 shrink-0 overflow-hidden transition-all duration-300',
            selectedTraceMessageId ? 'w-[420px]' : 'w-0',
          )}
        >
          <div className="h-full overflow-hidden rounded-[2px] border border-border bg-surface dark:bg-surface">
            <div className="min-w-[360px] h-full flex flex-col">
              {/* Inspector Tabs */}
              <div className="border-b border-border px-3 py-2">
                <nav className="flex gap-1 overflow-x-auto">
                  {inspectorTabs.map((tab) => (
                    <button
                      key={tab.id}
                      type="button"
                      onClick={() => setActiveInspectorTab(tab.id)}
                      className={cn(
                        'shrink-0 px-2 py-1 text-xs font-medium transition rounded-[2px]',
                        activeInspectorTab === tab.id
                          ? 'bg-primary/10 text-primary'
                          : 'text-text-muted hover:text-text hover:bg-surface-hover',
                      )}
                    >
                      {tab.label}
                    </button>
                  ))}
                </nav>
              </div>

              {/* Inspector Content */}
              <div className="flex-1 overflow-y-auto">
                {activeInspectorTab === 'trace' && (
                  <div className="h-full flex flex-col">
                    <AgentTraceView
                      trace={currentSession?.modelType === 'agent' ? currentTrace : null}
                      emptyTitle={
                        currentSession?.modelType === 'model'
                          ? t('aiChat:trace.cardModeTitle')
                          : t('aiChat:trace.emptyTitle')
                      }
                      emptyDescription={
                        currentSession?.modelType === 'model'
                          ? t('aiChat:trace.cardModeDescription')
                          : t('aiChat:trace.noTraceDescription')
                      }
                    />
                    {/* Link to Run Detail */}
                    {runId && (
                      <div className="border-t border-border px-3 py-2">
                        <button
                          type="button"
                          onClick={() => navigate(`/runs/${runId}`)}
                          className="inline-flex items-center gap-1.5 text-xs text-primary hover:underline"
                        >
                          <ExternalLink size={12} />
                          {t('aiChat:inspector.openRunDetail')}
                        </button>
                      </div>
                    )}
                  </div>
                )}
                {activeInspectorTab === 'run' && (
                  <RunInspectorTab runId={runId} onNavigate={navigate} />
                )}
                {activeInspectorTab === 'cost' && <InspectorCostTab runId={runId} />}
                {activeInspectorTab === 'eval' && <InspectorEvaluationTab runId={runId} />}
                {activeInspectorTab !== 'trace' && activeInspectorTab !== 'run' && activeInspectorTab !== 'cost' && activeInspectorTab !== 'eval' && <InspectorPlaceholder tab={activeInspectorTab} />}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function InspectorPlaceholder({ tab }: { tab: InspectorTab }) {
  const { t } = useTranslation(['aiChat']);

  const messages: Record<InspectorTab, string> = {
    run: '', // handled by RunInspectorTab
    trace: '', // handled by AgentTraceView
    tools: t('aiChat:inspector.notAvailable.tools'),
    context: t('aiChat:inspector.notAvailable.context'),
    cost: t('aiChat:inspector.notAvailable.cost'),
    eval: t('aiChat:inspector.notAvailable.eval'),
  };

  return (
    <div className="flex h-full items-center justify-center px-4 py-8">
      <p className="text-center text-sm text-text-muted">{messages[tab]}</p>
    </div>
  );
}

function RunInspectorTab({
  runId,
  onNavigate,
}: {
  runId: string | null;
  onNavigate: (path: string) => void;
}) {
  const { t } = useTranslation(['aiChat']);
  const { data: run, isLoading, error } = useRunDetail(runId ?? '');

  if (!runId) {
    return (
      <div className="flex h-full items-center justify-center px-4 py-8">
        <p className="text-center text-sm text-text-muted">{t('aiChat:inspector.noRunId')}</p>
      </div>
    );
  }

  if (isLoading) return <div className="p-4 text-sm text-text-muted">Loading…</div>;
  if (error || !run) return <div className="p-4 text-sm text-error">Run data is unavailable.</div>;

  return (
    <div className="flex flex-col gap-4 px-4 py-8">
      <div className="space-y-2">
        <div className="flex items-center justify-between"><span className="text-xs text-text-muted">Status</span><StatusBadge status={run.status} /></div>
        <div className="flex items-center justify-between"><span className="text-xs text-text-muted">Run ID</span><span className="font-mono text-xs text-text">{run.id.slice(0, 12)}…</span></div>
        <div className="flex items-center justify-between"><span className="text-xs text-text-muted">Agent</span><span className="text-xs text-text">{run.agentKey}</span></div>
        <div className="flex items-center justify-between"><span className="text-xs text-text-muted">Version</span><span className="text-xs text-text">{run.agentVersion ? `v${run.agentVersion}` : '—'}</span></div>
        <div className="flex items-center justify-between"><span className="text-xs text-text-muted">Duration</span><span className="text-xs text-text">{run.durationMs != null ? `${run.durationMs}ms` : '—'}</span></div>
      </div>
      <button
        type="button"
        onClick={() => onNavigate(`/runs/${runId}`)}
        className="inline-flex items-center gap-2 rounded-[2px] bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition hover:bg-primary/90"
      >
        <ExternalLink size={14} />
        {t('aiChat:inspector.openRunDetail')}
      </button>
    </div>
  );
}

function InspectorCostTab({ runId }: { runId: string | null }) {
  const { data, isLoading, error } = useRunCost(runId ?? '');
  if (!runId) return <InspectorUnavailable text="No run is selected." />;
  if (isLoading) return <InspectorUnavailable text="Loading…" />;
  if (error || !data) return <InspectorUnavailable text="Cost data is not available for this run." />;
  return <div className="space-y-2 p-4 text-sm"><div className="flex justify-between"><span>Total</span><strong>{data.totalUsd != null ? `$${data.totalUsd.toFixed(4)}` : '—'}</strong></div><div className="flex justify-between"><span>Input tokens</span><span>{data.inputTokens ?? '—'}</span></div><div className="flex justify-between"><span>Output tokens</span><span>{data.outputTokens ?? '—'}</span></div></div>;
}

function InspectorEvaluationTab({ runId }: { runId: string | null }) {
  const { data, isLoading, error } = useRunEvaluation(runId ?? '');
  if (!runId) return <InspectorUnavailable text="No run is selected." />;
  if (isLoading) return <InspectorUnavailable text="Loading…" />;
  if (error || !data || data.overallScore == null) return <InspectorUnavailable text="No evaluation is available for this run." />;
  return <div className="p-4 text-sm"><div className="flex justify-between"><span>Overall</span><strong>{(data.overallScore * 100).toFixed(1)}%</strong></div></div>;
}

function InspectorUnavailable({ text }: { text: string }) { return <div className="p-4 text-center text-sm text-text-muted">{text}</div>; }
