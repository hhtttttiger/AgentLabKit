import { Link } from 'react-router-dom';
import { CheckCircle2, CircleAlert, Clock3, ListChecks } from 'lucide-react';
import { useRunList } from '@/modules/runs/hooks';
import type { RunSummary } from '@/modules/runs/types';
import { useTranslation } from 'react-i18next';

/**
 * A session is intentionally a presentation projection for v0. It is not a
 * Runtime or Execution Model primitive. Until a first-class session contract
 * exists, one interactive Run is the useful unit to show here.
 */
export function SessionsPage() {
  const { t } = useTranslation('desktop');
  const { data, isLoading, error } = useRunList({ limit: 50, offset: 0 });
  const runs = data?.items ?? [];

  return (
    <div className="desktop-page">
      <header className="desktop-page__header">
        <div>
          <p className="desktop-kicker">{t('sessions.kicker')}</p>
          <h1>{t('sessions.title')}</h1>
          <p>{t('sessions.description')}</p>
        </div>
        <div className="desktop-page__header-meta"><ListChecks size={16} /> {t('sessions.runs', { count: data?.total ?? 0 })}</div>
      </header>
      {isLoading && <div className="desktop-empty">{t('sessions.loading')}</div>}
      {error && <div className="desktop-empty desktop-empty--error" role="alert">{t('sessions.error')}</div>}
      {!isLoading && !error && runs.length === 0 && <div className="desktop-empty">{t('sessions.empty')}</div>}
      {!isLoading && !error && runs.length > 0 && (
        <div className="session-groups">
          <SessionGroup label={t('sessions.recent')} runs={runs} />
        </div>
      )}
    </div>
  );
}

function SessionGroup({ label, runs }: { label: string; runs: RunSummary[] }) {
  const { t } = useTranslation('desktop');
  return (
    <section className="session-group" aria-labelledby="session-group-title">
      <h2 id="session-group-title">{label}</h2>
      <div className="session-list">
        {runs.map((run) => {
          const completed = run.status === 'completed';
          const failed = run.status === 'failed';
          return (
            <Link className="session-row" key={run.id} to={`/runs/${encodeURIComponent(run.id)}`}>
              <span className={`session-row__status ${completed ? 'is-success' : failed ? 'is-warning' : ''}`} aria-hidden="true">
                {completed ? <CheckCircle2 size={18} /> : failed ? <CircleAlert size={18} /> : <Clock3 size={18} />}
              </span>
              <span className="session-row__main">
                <strong>{run.agentKey || t('sessions.nativeAgentRun')}</strong>
                <span>{run.id.slice(0, 12)} · {run.startedAt ? new Date(run.startedAt).toLocaleString() : t('sessions.timeUnavailable')}</span>
              </span>
              <span className={`session-row__badge ${completed ? 'is-success' : failed ? 'is-warning' : ''}`}>{run.status}</span>
              <span className="session-row__arrow">→</span>
            </Link>
          );
        })}
      </div>
    </section>
  );
}
