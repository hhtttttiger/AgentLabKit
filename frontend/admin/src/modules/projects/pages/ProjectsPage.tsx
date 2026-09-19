import { useEffect, useState } from 'react';
import { apiRequest } from '@/shared/api/client';

type Project = { projectId: string; name: string; workspace: string };
type Conversation = { conversationId: string; title: string };
type Turn = { turnId: string; role: 'user' | 'assistant'; content: string; runId?: string | null };

export function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [project, setProject] = useState<Project | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadProjects() { setProjects(await apiRequest<Project[]>('/api/projects')); }
  useEffect(() => { void loadProjects().catch((e) => setError(String(e))); }, []);
  async function selectProject(next: Project) {
    setProject(next); setConversation(null); setTurns([]);
    setConversations(await apiRequest<Conversation[]>(`/api/projects/${next.projectId}/conversations`));
  }
  async function createProject() {
    const name = window.prompt('Project name', 'AgentLabKit');
    const workspace = window.prompt('Workspace path', '~/Code/AgentLabKit');
    if (!name || !workspace) return;
    const created = await apiRequest<Project>('/api/projects', { method: 'POST', body: { name, workspace } });
    setProjects((items) => [created, ...items]); await selectProject(created);
  }
  async function createConversation() {
    if (!project) return;
    const created = await apiRequest<Conversation>(`/api/projects/${project.projectId}/conversations`, { method: 'POST', body: { title: 'New conversation' } });
    setConversations((items) => [created, ...items]); await selectConversation(created);
  }
  async function selectConversation(next: Conversation) {
    setConversation(next); setTurns(await apiRequest<Turn[]>(`/api/conversations/${next.conversationId}/turns`));
  }
  async function send() {
    if (!conversation || !message.trim() || busy) return;
    const text = message.trim(); setMessage(''); setBusy(true); setError(null);
    try {
      const result = await apiRequest<{ conversation: Conversation; userTurn: Turn; assistantTurn: Turn }>(`/api/conversations/${conversation.conversationId}/messages`, { method: 'POST', body: { message: text } });
      setTurns((items) => [...items, result.userTurn, result.assistantTurn]);
      setConversation(result.conversation); setConversations((items) => items.map((item) => item.conversationId === result.conversation.conversationId ? result.conversation : item));
    } catch (e) { setError(String(e)); } finally { setBusy(false); }
  }
  return <div className="flex h-full min-h-0 flex-col bg-surface text-text">
    <div className="border-b border-border px-6 py-4"><h1 className="text-xl font-semibold">Projects</h1><p className="text-sm text-text-secondary">Continue work in a persistent project conversation.</p></div>
    <div className="grid min-h-0 flex-1 grid-cols-[220px_260px_1fr]">
      <aside className="border-r border-border p-4"><div className="mb-3 flex items-center justify-between"><span className="text-xs font-semibold uppercase text-text-muted">Projects</span><button className="text-sm" onClick={() => void createProject()}>+ New</button></div>{projects.map((item) => <button key={item.projectId} className={`mb-1 w-full rounded px-3 py-2 text-left text-sm ${project?.projectId === item.projectId ? 'bg-primary/10 text-primary' : 'hover:bg-surface-muted'}`} onClick={() => void selectProject(item)}>{item.name}</button>)}</aside>
      <aside className="border-r border-border p-4"><div className="mb-3 flex items-center justify-between"><span className="text-xs font-semibold uppercase text-text-muted">Conversations</span>{project && <button className="text-sm" onClick={() => void createConversation()}>+ New</button>}</div>{conversations.map((item) => <button key={item.conversationId} className={`mb-1 w-full rounded px-3 py-2 text-left text-sm ${conversation?.conversationId === item.conversationId ? 'bg-primary/10 text-primary' : 'hover:bg-surface-muted'}`} onClick={() => void selectConversation(item)}>{item.title}</button>)}</aside>
      <main className="flex min-h-0 flex-col p-6">{conversation ? <><div className="mb-4"><h2 className="text-lg font-semibold">{conversation.title}</h2><p className="text-xs text-text-muted">{project?.workspace}</p></div><div className="min-h-0 flex-1 space-y-4 overflow-auto">{turns.map((turn) => <div key={turn.turnId} className={turn.role === 'user' ? 'ml-12 rounded bg-surface-muted p-3' : 'mr-12 rounded border border-border p-3'}><div className="mb-1 text-xs font-semibold uppercase text-text-muted">{turn.role}</div><div className="whitespace-pre-wrap text-sm">{turn.content}</div>{turn.runId && <div className="mt-2 text-xs text-text-muted">Run {turn.runId}</div>}</div>)}</div><div className="mt-4 flex gap-2"><textarea value={message} onChange={(e) => setMessage(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); void send(); } }} placeholder="Continue the conversation…" className="min-h-12 flex-1 rounded border border-border bg-surface px-3 py-2 text-sm" /><button disabled={busy} onClick={() => void send()} className="rounded bg-primary px-4 py-2 text-sm text-white disabled:opacity-50">{busy ? 'Running…' : 'Send'}</button></div></> : <div className="flex h-full items-center justify-center text-sm text-text-muted">Choose a project and conversation to continue.</div>}{error && <div className="mt-3 text-sm text-danger">{error}</div>}</main>
    </div>
  </div>;
}
