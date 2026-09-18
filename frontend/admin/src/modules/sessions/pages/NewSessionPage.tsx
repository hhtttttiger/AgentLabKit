import { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ArrowLeft, CheckCircle2, FolderOpen, LoaderCircle, Play, Wrench, XCircle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { streamAgentChatMessage } from '@/modules/ai-chat/api';
import { useChatAgentOptions } from '@/modules/ai-chat/hooks';
import type { AgentStreamEvent, ModelOption } from '@/modules/ai-chat/lib/contracts';
import { loadLocalProject, pickLocalProject, saveLocalProject, type LocalProject } from '@/modules/overview/lib/workspace';
import { useQuery } from '@tanstack/react-query';
import { getDesktopModelSettings } from '@/modules/settings/api';
import { isLocalDesktopMode } from '@/shared/runtime/config';

type TimelineItem = { id: string; title: string; detail?: string; tone: 'active' | 'done' | 'error' };

export function NewSessionPage() {
  const { t } = useTranslation('desktop');
  const navigate = useNavigate();
  const { data: agents = [], isLoading: agentsLoading } = useChatAgentOptions();
  const interactiveAgents = useMemo(() => agents.filter((item) => item.agentKind !== 'external'), [agents]);
  const modelSettings = useQuery({ queryKey: ['desktop-settings', 'models'], queryFn: getDesktopModelSettings, enabled: isLocalDesktopMode() });
  const [project, setProject] = useState<LocalProject | null>(loadLocalProject);
  const [task, setTask] = useState('');
  const [agent, setAgent] = useState<ModelOption | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [timeline, setTimeline] = useState<TimelineItem[]>([]);
  const [output, setOutput] = useState('');
  const [runId, setRunId] = useState<string | null>(null);

  useEffect(() => {
    if (!agent && interactiveAgents[0]) setAgent(interactiveAgents[0]);
  }, [agent, interactiveAgents]);

  const nativeNeedsConfiguration = isLocalDesktopMode() && agent?.id === 'local-agent' && modelSettings.data && !modelSettings.data.apiKeyConfigured;
  const canRun = Boolean(project && task.trim() && agent && !running && !nativeNeedsConfiguration);
  const statusLabel = running ? t('session.running') : runId ? t('session.completed') : t('session.ready');

  async function handleProject() {
    try {
      const selected = await pickLocalProject();
      if (selected) { saveLocalProject(selected); setProject(selected); }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : t('session.chooseDirectory'));
    }
  }

  function addTimeline(item: TimelineItem) {
    setTimeline((current) => [...current, item]);
  }

  function handleEvent(event: AgentStreamEvent) {
    if (event.runId) setRunId(event.runId);
    if (event.type === 'context') addTimeline({ id: `${Date.now()}-context`, title: t('session.started'), detail: t('session.runtimeReady'), tone: 'active' });
    if (event.type === 'tool_call') addTimeline({ id: `${Date.now()}-${event.toolName}`, title: t('session.tool'), detail: event.toolName ?? t('session.unknownTool'), tone: 'active' });
    if (event.type === 'tool_result') addTimeline({ id: `${Date.now()}-${event.toolName}-result`, title: t('session.toolCompleted'), detail: event.toolName ?? t('session.unknownTool'), tone: 'done' });
    if (event.type === 'reply_delta' && event.delta) setOutput((current) => current + event.delta);
    if (event.type === 'completed') {
      setOutput((current) => event.replyText ?? current);
      setTimeline((current) => [...current, { id: `${Date.now()}-complete`, title: t('session.completed'), detail: t('session.completedDetail'), tone: 'done' }]);
    }
    if (event.type === 'error') {
      const message = event.errorMessage ?? t('session.agentExecutionFailed');
      setError(message);
      setTimeline((current) => [...current, { id: `${Date.now()}-error`, title: t('session.executionFailed'), detail: message, tone: 'error' }]);
    }
  }

  function handleRun() {
    if (!canRun || !agent || !project) return;
    setRunning(true); setError(null); setOutput(''); setRunId(null); setTimeline([]);
    const stop = streamAgentChatMessage(agent.id, {
      message: task.trim(),
      sessionId: `desktop-${Date.now()}`,
      workingDirectory: project.path,
    }, {
      onEvent: handleEvent,
      onError: (reason) => { setError(reason.message); setRunning(false); },
      onComplete: () => setRunning(false),
    });
    void stop;
  }

  const timelineContent = useMemo(() => timeline.length ? timeline : [{ id: 'placeholder', title: t('session.waiting'), detail: t('session.timelineHint'), tone: 'active' as const }], [timeline, t]);

  return (
    <div className="desktop-page new-session-page">
      <header className="desktop-page__header">
        <div>
          <button type="button" className="desktop-back-action" onClick={() => navigate('/overview')}><ArrowLeft size={15} /> {t('home.workspace')}</button>
          <p className="desktop-kicker">{t('session.runWork')}</p><h1>{t('session.newSession')}</h1><p>{t('session.description')}</p>
        </div>
        <span className={`session-status session-status--${running ? 'running' : runId ? 'completed' : 'ready'}`}>{running && <LoaderCircle size={14} className="spin" />}{statusLabel}</span>
      </header>

      <div className="new-session-layout">
        <section className="session-form-card">
          <div className="project-context"><div><p className="desktop-kicker">{t('session.project')}</p><strong>{project?.displayName ?? t('session.noProject')}</strong><span>{project?.path ?? t('session.chooseDirectory')}</span></div><button type="button" className="desktop-secondary-action" onClick={handleProject}><FolderOpen size={15} /> {project ? t('session.change') : t('session.open')}</button></div>
          <label className="session-field"><span>{t('session.task')}</span><textarea value={task} onChange={(event) => setTask(event.target.value)} disabled={running} rows={7} placeholder={t('session.taskPlaceholder')} /></label>
          <label className="session-field"><span>{t('session.agent')}</span><select value={agent?.id ?? ''} onChange={(event) => setAgent(interactiveAgents.find((item) => item.id === event.target.value) ?? null)} disabled={running || agentsLoading}><option value="">{agentsLoading ? t('session.loadingAgents') : t('session.selectAgent')}</option>{interactiveAgents.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
          {nativeNeedsConfiguration && <div className="session-error" role="status"><XCircle size={15} /><span>{t('session.nativeNotConfigured')}</span><button type="button" className="text-xs font-semibold underline" onClick={() => navigate('/settings/models')}>{t('session.openModelSettings')}</button></div>}
          <div className="session-field"><span>{t('session.context')}</span><div className="working-directory"><strong>{t('session.workingDirectory')}</strong><code>{project?.path ?? t('session.selectProject')}</code></div></div>
          {error && <p className="session-error" role="alert"><XCircle size={15} /> {error}</p>}
          <button type="button" className="desktop-primary-action session-run-button" disabled={!canRun} onClick={handleRun}><Play size={16} /> {t('session.run')}</button>
        </section>

        <aside className="execution-card" aria-live="polite"><div className="execution-card__header"><div><p className="desktop-kicker">{t('session.liveExecution')}</p><h2>{running ? t('session.working') : runId ? t('session.runComplete') : t('session.readyWhen')}</h2></div><Wrench size={18} /></div><div className="execution-timeline">{timelineContent.map((item) => <div className="timeline-item" key={item.id}><span className={`timeline-item__icon timeline-item__icon--${item.tone}`}>{item.tone === 'error' ? <XCircle size={14} /> : item.tone === 'done' ? <CheckCircle2 size={14} /> : <span />}</span><div><strong>{item.title}</strong>{item.detail && <span>{item.detail}</span>}</div></div>)}</div>{output && <div className="execution-output"><p className="desktop-kicker">{t('session.output')}</p><p>{output}</p></div>}{runId && !running && <button type="button" className="desktop-secondary-action execution-inspect" onClick={() => navigate(`/runs/${encodeURIComponent(runId)}`)}>{t('session.inspectRun')} <ArrowLeft size={15} className="rotate-180" /></button>}</aside>
      </div>
    </div>
  );
}
