/**
 * Run Replay Page — Re-execute a run with the same input.
 */

import { useParams, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { ArrowLeft, Play, Loader2 } from 'lucide-react';
import { useRunDetail, useReplayRun } from '../hooks';
import { useToast } from '@/shared/ui/Toast';

export function RunReplayPage() {
  const { runId } = useParams<{ runId: string }>();
  const { t } = useTranslation(['common', 'runs']);
  const navigate = useNavigate();
  const { toast } = useToast();
  const { data: run, isLoading } = useRunDetail(runId ?? '');
  const replayMutation = useReplayRun();

  const handleReplay = async () => {
    if (!runId) return;
    try {
      const newRun = await replayMutation.mutateAsync(runId);
      toast(t('runs:replay.success'));
      navigate(`/runs/${newRun.id}`);
    } catch {
      toast(t('runs:replay.error'));
    }
  };

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-sm text-text-muted">{t('common:states.loading')}</div>
      </div>
    );
  }

  if (!run) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-sm text-error">{t('common:states.loadingFailed')}</div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Header */}
      <div className="border-b border-border bg-surface px-6 py-4">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => navigate(`/runs/${runId}`)}
            className="rounded-[2px] p-1 text-text-muted transition hover:text-text"
          >
            <ArrowLeft size={18} />
          </button>
          <h1 className="text-lg font-semibold text-text">{t('runs:replay.title')}</h1>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-2xl space-y-6">
          {/* Original run info */}
          <div className="rounded-lg border border-border bg-surface p-6">
            <h2 className="mb-4 text-sm font-semibold text-text">{t('runs:replay.originalRun')}</h2>
            <dl className="grid grid-cols-2 gap-4">
              <div>
                <dt className="text-xs text-text-muted">{t('runs:detail.title', { id: '' })}</dt>
                <dd className="mt-1 font-mono text-sm text-primary">#{run.id.slice(0, 8)}</dd>
              </div>
              <div>
                <dt className="text-xs text-text-muted">{t('runs:table.agent')}</dt>
                <dd className="mt-1 text-sm text-text">{run.agentKey}</dd>
              </div>
              <div>
                <dt className="text-xs text-text-muted">{t('runs:table.duration')}</dt>
                <dd className="mt-1 text-sm text-text">{run.durationMs != null ? `${(run.durationMs / 1000).toFixed(2)}s` : '—'}</dd>
              </div>
              <div>
                <dt className="text-xs text-text-muted">{t('runs:table.status')}</dt>
                <dd className="mt-1 text-sm text-text">{run.status}</dd>
              </div>
            </dl>
          </div>

          {/* Input preview */}
          <div className="rounded-lg border border-border bg-surface p-6">
            <h2 className="mb-4 text-sm font-semibold text-text">{t('runs:replay.inputPreview')}</h2>
            <div className="rounded-[2px] bg-surface-subtle p-4">
              <pre className="whitespace-pre-wrap text-sm text-text-secondary">
                {run.input ?? t('runs:detail.noInput')}
              </pre>
            </div>
          </div>

          {/* Replay button */}
          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={() => navigate(`/runs/${runId}`)}
              className="rounded-[2px] border border-border bg-surface px-4 py-2 text-sm font-medium text-text hover:bg-surface-hover"
            >
              {t('common:actions.cancel')}
            </button>
            <button
              type="button"
              onClick={handleReplay}
              disabled={replayMutation.isPending}
              className="inline-flex items-center gap-2 rounded-[2px] bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-50"
            >
              {replayMutation.isPending ? (
                <Loader2 size={14} className="animate-spin" />
              ) : (
                <Play size={14} />
              )}
              {t('runs:replay.confirm')}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
