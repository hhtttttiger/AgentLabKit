import { useNavigate } from 'react-router-dom';
import { Play, Search } from 'lucide-react';
import { useTranslation } from 'react-i18next';

/** The sealed Run API exposes read-by-id; listing is intentionally deferred until a public list contract exists. */
export function RunsListPage() {
  const navigate = useNavigate();
  const { t } = useTranslation(['common', 'runs']);
  return <div className="flex h-full flex-col items-center justify-center gap-4 p-6 text-center">
    <Search className="h-12 w-12 text-text-muted" />
    <h1 className="text-lg font-semibold text-text">{t('runs:title')}</h1>
    <p className="max-w-md text-sm text-text-secondary">Run detail is available from an authoritative run ID. A list endpoint is not part of FastAPI Adapter v1.</p>
    <button type="button" onClick={() => navigate('/playground')} className="inline-flex items-center gap-2 bg-primary px-3 py-2 text-sm text-primary-foreground"><Play size={14} />{t('runs:openPlayground')}</button>
  </div>;
}
