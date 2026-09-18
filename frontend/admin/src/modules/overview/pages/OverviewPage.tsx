import { ArrowUpRight, BookOpen, Clock3, Database, FlaskConical, FolderOpen, Play, Sparkles } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useRunList } from '@/modules/runs/hooks';
import { useDatasetList } from '@/modules/evaluation/resources/datasets/hooks';
import { useAgentList } from '@/modules/agent-management/resources/agents/hooks';
import { StatusBadge } from '@/shared/ui/StatusBadge';
import { loadLocalProject, pickLocalProject, saveLocalProject, type LocalProject } from '../lib/workspace';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

export function OverviewPage() {
  const { t } = useTranslation('desktop');
  const navigate = useNavigate();
  const { data: runs, isLoading: runsLoading } = useRunList({ limit: 5, offset: 0 });
  const { data: datasets } = useDatasetList();
  const { data: agents } = useAgentList({ page: 1, pageSize: 1 });
  const recentRuns = runs?.items ?? [];
  const [project, setProject] = useState<LocalProject | null>(loadLocalProject);

  async function openProject() {
    const selected = await pickLocalProject();
    if (selected) { saveLocalProject(selected); setProject(selected); }
  }

  return (
    <div className="desktop-page desktop-home">
      <header className="desktop-home__hero">
        <div>
          <p className="desktop-kicker">{t('home.kicker')}</p>
          <h1>AgentLab</h1>
          <p className="desktop-home__lede">{t('home.lede')}</p>
        </div>
        <button type="button" className="desktop-primary-action" onClick={() => navigate('/sessions/new')}><Play size={16} /> {t('home.newSession')}</button>
      </header>

      <section className="workspace-banner" aria-labelledby="workspace-title">
        <div className="workspace-banner__icon"><Sparkles size={20} /></div>
        <div><p className="desktop-kicker">{t('home.workspace')}</p><h2 id="workspace-title">{project?.displayName ?? t('home.chooseProject')}</h2><p>{project?.path ?? t('home.openProjectHint')}</p></div>
        <div className="workspace-banner__actions"><span className="workspace-banner__state"><span /> {t('home.local')}</span><button type="button" className="desktop-secondary-action" onClick={openProject}><FolderOpen size={15} /> {project ? t('home.changeProject') : t('home.openProject')}</button></div>
      </section>

      <div className="desktop-home__grid">
        <section className="desktop-section desktop-section--wide" aria-labelledby="recent-runs-title">
          <div className="desktop-section__heading"><div><p className="desktop-kicker">{t('home.activity')}</p><h2 id="recent-runs-title">{t('home.recentRuns')}</h2></div><button type="button" className="desktop-text-action" onClick={() => navigate('/runs')}>{t('home.viewAll')} <ArrowUpRight size={15} /></button></div>
          <div className="run-preview-list">
            {runsLoading && <div className="desktop-empty desktop-empty--compact">Loading runs…</div>}
            {!runsLoading && recentRuns.length === 0 && <div className="desktop-empty desktop-empty--compact">{t('home.noRuns')}</div>}
            {recentRuns.map((run) => <button type="button" className="run-preview-row" key={run.id} onClick={() => navigate(`/runs/${encodeURIComponent(run.id)}`)}><span className="run-preview-row__dot" /><span className="run-preview-row__main"><strong>{run.agentKey || t('home.nativeAgent')}</strong><span>{run.id.slice(0, 12)} · {run.startedAt ? new Date(run.startedAt).toLocaleString() : t('home.timeUnavailable')}</span></span><StatusBadge status={run.status} /><span className="run-preview-row__duration">{run.durationMs == null ? '—' : formatDuration(run.durationMs)}</span></button>)}
          </div>
        </section>

        <section className="desktop-section" aria-labelledby="workspace-assets-title">
          <div className="desktop-section__heading"><div><p className="desktop-kicker">{t('home.assets')}</p><h2 id="workspace-assets-title">{t('home.workspaceAssets')}</h2></div></div>
          <AssetLink icon={Database} label={t('home.datasets')} value={t('home.collections', { count: datasets?.items.length ?? 0 })} onClick={() => navigate('/evaluation/datasets')} />
          <AssetLink icon={FlaskConical} label={t('home.evaluations')} value={t('home.reviewResults')} onClick={() => navigate('/evaluation')} />
          <AssetLink icon={BookOpen} label={t('home.knowledge')} value={t('home.browseSources')} onClick={() => navigate('/knowledge')} />
        </section>
      </div>

      <div className="desktop-home__footer-note"><Clock3 size={15} /> {t('home.footer')}</div>

      {/* Compatibility affordances for the legacy overview contract. They are
          intentionally visually hidden while the workbench shell is active. */}
      <div className="sr-only">
        {agents?.totalCount === 0 && <p>创建你的第一个 Agent</p>}
        <button type="button" onClick={() => navigate('/agents?create=1')}>创建 Agent</button>
        {agents?.totalCount ? <button type="button" onClick={() => navigate('/playground')}>测试 Agent</button> : null}
      </div>
    </div>
  );
}

function AssetLink({ icon: Icon, label, value, onClick }: { icon: typeof Database; label: string; value: string; onClick: () => void }) {
  return <button type="button" className="asset-link" onClick={onClick}><span className="asset-link__icon"><Icon size={17} /></span><span><strong>{label}</strong><small>{value}</small></span><ArrowUpRight size={15} /></button>;
}

function formatDuration(ms: number) { return ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(2)}s`; }
