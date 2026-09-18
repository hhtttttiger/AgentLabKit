import { useEffect, useMemo, useState } from 'react';
import { ArrowLeft, CheckCircle2, FolderOpen, LoaderCircle, Play, Wrench, XCircle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { streamAgentChatMessage } from '@/modules/ai-chat/api';
import { useChatAgentOptions } from '@/modules/ai-chat/hooks';
import type { AgentStreamEvent, ModelOption } from '@/modules/ai-chat/lib/contracts';
import { loadLocalProject, pickLocalProject, saveLocalProject, type LocalProject } from '@/modules/overview/lib/workspace';

type TimelineItem = { id: string; title: string; detail?: string; tone: 'active' | 'done' | 'error' };

export function NewSessionPage() {
  const navigate = useNavigate();
  const { data: agents = [], isLoading: agentsLoading } = useChatAgentOptions();
  const [project, setProject] = useState<LocalProject | null>(loadLocalProject);
  const [task, setTask] = useState('');
  const [agent, setAgent] = useState<ModelOption | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [timeline, setTimeline] = useState<TimelineItem[]>([]);
  const [output, setOutput] = useState('');
  const [runId, setRunId] = useState<string | null>(null);

  useEffect(() => {
    if (!agent && agents[0]) setAgent(agents[0]);
  }, [agent, agents]);

  const canRun = Boolean(project && task.trim() && agent && !running);
  const statusLabel = running ? 'Running' : runId ? 'Completed' : 'Ready';

  async function handleProject() {
    try {
      const selected = await pickLocalProject();
      if (selected) { saveLocalProject(selected); setProject(selected); }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not open a project.');
    }
  }

  function addTimeline(item: TimelineItem) {
    setTimeline((current) => [...current, item]);
  }

  function handleEvent(event: AgentStreamEvent) {
    if (event.runId) setRunId(event.runId);
    if (event.type === 'context') addTimeline({ id: `${Date.now()}-context`, title: 'Started', detail: 'Agent runtime is ready', tone: 'active' });
    if (event.type === 'tool_call') addTimeline({ id: `${Date.now()}-${event.toolName}`, title: 'Tool', detail: event.toolName ?? 'Unknown tool', tone: 'active' });
    if (event.type === 'tool_result') addTimeline({ id: `${Date.now()}-${event.toolName}-result`, title: 'Tool completed', detail: event.toolName ?? 'Unknown tool', tone: 'done' });
    if (event.type === 'reply_delta' && event.delta) setOutput((current) => current + event.delta);
    if (event.type === 'completed') {
      setOutput(event.replyText ?? output);
      setTimeline((current) => [...current, { id: `${Date.now()}-complete`, title: 'Completed', detail: 'Run finished successfully', tone: 'done' }]);
    }
    if (event.type === 'error') {
      const message = event.errorMessage ?? 'Agent execution failed.';
      setError(message);
      setTimeline((current) => [...current, { id: `${Date.now()}-error`, title: 'Execution failed', detail: message, tone: 'error' }]);
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

  const timelineContent = useMemo(() => timeline.length ? timeline : [{ id: 'placeholder', title: 'Waiting to run', detail: 'Your execution timeline will appear here.', tone: 'active' as const }], [timeline]);

  return (
    <div className="desktop-page new-session-page">
      <header className="desktop-page__header">
        <div>
          <button type="button" className="desktop-back-action" onClick={() => navigate('/overview')}><ArrowLeft size={15} /> Workspace</button>
          <p className="desktop-kicker">Run work</p><h1>New Session</h1><p>Give one Agent a real task in a local project.</p>
        </div>
        <span className={`session-status session-status--${running ? 'running' : runId ? 'completed' : 'ready'}`}>{running && <LoaderCircle size={14} className="spin" />}{statusLabel}</span>
      </header>

      <div className="new-session-layout">
        <section className="session-form-card">
          <div className="project-context"><div><p className="desktop-kicker">Project</p><strong>{project?.displayName ?? 'No project selected'}</strong><span>{project?.path ?? 'Choose a local directory to begin.'}</span></div><button type="button" className="desktop-secondary-action" onClick={handleProject}><FolderOpen size={15} /> {project ? 'Change' : 'Open Project'}</button></div>
          <label className="session-field"><span>What do you want to work on?</span><textarea value={task} onChange={(event) => setTask(event.target.value)} disabled={running} rows={7} placeholder="Fix the failing evaluation test…" /></label>
          <label className="session-field"><span>Agent</span><select value={agent?.id ?? ''} onChange={(event) => setAgent(agents.find((item) => item.id === event.target.value) ?? null)} disabled={running || agentsLoading}><option value="">{agentsLoading ? 'Loading agents…' : 'Select an agent'}</option>{agents.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
          <div className="session-field"><span>Context</span><div className="working-directory"><strong>Working directory</strong><code>{project?.path ?? 'Select a project first'}</code></div></div>
          {error && <p className="session-error" role="alert"><XCircle size={15} /> {error}</p>}
          <button type="button" className="desktop-primary-action session-run-button" disabled={!canRun} onClick={handleRun}><Play size={16} /> Run</button>
        </section>

        <aside className="execution-card" aria-live="polite"><div className="execution-card__header"><div><p className="desktop-kicker">Live execution</p><h2>{running ? 'Agent is working…' : runId ? 'Run complete' : 'Ready when you are'}</h2></div><Wrench size={18} /></div><div className="execution-timeline">{timelineContent.map((item) => <div className="timeline-item" key={item.id}><span className={`timeline-item__icon timeline-item__icon--${item.tone}`}>{item.tone === 'error' ? <XCircle size={14} /> : item.tone === 'done' ? <CheckCircle2 size={14} /> : <span />}</span><div><strong>{item.title}</strong>{item.detail && <span>{item.detail}</span>}</div></div>)}</div>{output && <div className="execution-output"><p className="desktop-kicker">Output</p><p>{output}</p></div>}{runId && !running && <button type="button" className="desktop-secondary-action execution-inspect" onClick={() => navigate(`/runs/${encodeURIComponent(runId)}`)}>Inspect Run <ArrowLeft size={15} className="rotate-180" /></button>}</aside>
      </div>
    </div>
  );
}
