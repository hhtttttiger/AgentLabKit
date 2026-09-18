import { useEffect, useState, type ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { CheckCircle2, Eye, EyeOff, Info, LoaderCircle, Save, ShieldCheck, TestTube2, XCircle } from 'lucide-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { getErrorMessage } from '@/shared/api/errors';
import { getDesktopModelSettings, saveDesktopModelSettings, testDesktopModelSettings, type DesktopModelSettingsDraft } from '../api';
import './ModelSettingsPage.css';

const queryKey = ['desktop-settings', 'models'];

export function ModelSettingsPage() {
  const { t } = useTranslation(['common', 'desktop']);
  const queryClient = useQueryClient();
  const settings = useQuery({ queryKey, queryFn: getDesktopModelSettings });
  const [provider, setProvider] = useState('openai');
  const [baseUrl, setBaseUrl] = useState('');
  const [model, setModel] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [showKey, setShowKey] = useState(false);
  const [clearKey, setClearKey] = useState(false);
  const [notice, setNotice] = useState<{ tone: 'success' | 'error'; text: string } | null>(null);

  useEffect(() => {
    if (!settings.data) return;
    setProvider(settings.data.provider);
    setBaseUrl(settings.data.baseUrl);
    setModel(settings.data.model);
    setApiKey('');
    setClearKey(false);
  }, [settings.data]);

  const draft = (): DesktopModelSettingsDraft => ({
    provider,
    baseUrl,
    model,
    ...(apiKey ? { apiKey } : {}),
    ...(clearKey ? { clearApiKey: true } : {}),
  });

  const save = useMutation({
    mutationFn: () => saveDesktopModelSettings(draft()),
    onSuccess: (data) => {
      queryClient.setQueryData(queryKey, data);
      setApiKey('');
      setClearKey(false);
      setNotice({ tone: 'success', text: t('desktop:settings.saved') });
    },
    onError: (error) => setNotice({ tone: 'error', text: getErrorMessage(error) }),
  });
  const test = useMutation({
    mutationFn: () => testDesktopModelSettings(draft()),
    onSuccess: () => setNotice({ tone: 'success', text: t('desktop:settings.testSuccess') }),
    onError: (error) => setNotice({ tone: 'error', text: getErrorMessage(error) }),
  });

  if (settings.isLoading) return <div className="flex h-full items-center justify-center text-sm text-text-secondary">{t('common:states.loading')}</div>;
  if (settings.isError || !settings.data) return <div className="p-8 text-sm text-status-error" role="alert">{t('desktop:settings.loadFailed')}</div>;
  const current = settings.data;
  const busy = save.isPending || test.isPending;
  const keyLocked = current.apiKeyOverridden;

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 px-8 py-8">
      <header>
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-text-muted">{t('desktop:settings.models')}</p>
        <h1 className="mt-2 text-2xl font-semibold text-text">{t('desktop:settings.title')}</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-text-secondary">{t('desktop:settings.description')}</p>
      </header>

      <section className="rounded border border-border bg-surface p-6" aria-labelledby="default-model-title">
        <div className="mb-6 flex items-start gap-3">
          <div className="rounded bg-primary/10 p-2 text-primary"><ShieldCheck size={18} /></div>
          <div><h2 id="default-model-title" className="text-base font-semibold text-text">{t('desktop:settings.defaultModel')}</h2><p className="mt-1 text-sm text-text-secondary">{t('desktop:settings.defaultDescription')}</p></div>
        </div>
        <div className="grid gap-5">
          <Field label={t('desktop:settings.provider')} hint={t('desktop:settings.providerHint')}>
            <select className="settings-input" value={provider} onChange={(e) => setProvider(e.target.value)} disabled={busy || current.providerOverridden}>
              <option value="openai">{t('desktop:settings.openaiCompatible')}</option><option value="anthropic">{t('desktop:settings.anthropic')}</option>
            </select>
            {current.providerOverridden && <OverrideNotice variable={current.overrideEnvironment.provider} />}
          </Field>
          <Field label={t('desktop:settings.baseUrl')} hint={t('desktop:settings.baseUrlHint')}>
            <input className="settings-input" value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} disabled={busy || current.baseUrlOverridden} />
            {current.baseUrlOverridden && <OverrideNotice variable={current.overrideEnvironment.base_url} />}
          </Field>
          <Field label={t('desktop:settings.apiKey')} hint={keyLocked ? t('desktop:settings.apiKeyEnvironmentHint') : current.apiKeyConfigured ? t('desktop:settings.apiKeyConfiguredHint') : t('desktop:settings.apiKeyMissingHint')}>
            <div className="relative"><input className="settings-input pr-20" type={showKey ? 'text' : 'password'} value={apiKey} placeholder={current.apiKeyConfigured ? t('desktop:settings.configuredPlaceholder') : t('desktop:settings.enterKey')} onChange={(e) => { setApiKey(e.target.value); setClearKey(false); }} disabled={busy || keyLocked} autoComplete="new-password" /><button type="button" className="absolute inset-y-0 right-0 flex items-center gap-1 px-3 text-xs text-text-secondary hover:text-text" onClick={() => setShowKey((value) => !value)} disabled={keyLocked}>{showKey ? <EyeOff size={15} /> : <Eye size={15} />} {showKey ? t('desktop:settings.hide') : t('desktop:settings.show')}</button></div>
            {current.apiKeyConfigured && !keyLocked && !apiKey && <button type="button" className="mt-2 text-xs text-status-error hover:underline" onClick={() => setClearKey((value) => !value)}>{clearKey ? t('desktop:settings.keepKey') : t('desktop:settings.clearKey')}</button>}
            {keyLocked && <OverrideNotice variable={current.overrideEnvironment.api_key} />}
          </Field>
          <Field label={t('desktop:settings.model')}><input className="settings-input" value={model} onChange={(e) => setModel(e.target.value)} disabled={busy || current.modelOverridden} placeholder="gpt-4o-mini" />{current.modelOverridden && <OverrideNotice variable={current.overrideEnvironment.model} />}</Field>
        </div>
      </section>

      <section className="rounded border border-border bg-surface p-6" aria-labelledby="connection-title">
        <div className="flex items-center justify-between gap-4"><div><h2 id="connection-title" className="text-base font-semibold text-text">{t('desktop:settings.connection')}</h2><p className="mt-1 text-sm text-text-secondary">{t('desktop:settings.connectionHint')}</p></div><span className="flex items-center gap-2 text-sm text-text-secondary">{notice?.tone === 'success' ? <CheckCircle2 size={16} className="text-status-success" /> : <Info size={16} />} {notice?.tone === 'success' ? t('desktop:settings.connected') : t('desktop:settings.notTested')}</span></div>
        {notice && <div className={`mt-4 flex items-start gap-2 rounded border px-3 py-2 text-sm ${notice.tone === 'success' ? 'border-status-success/30 bg-status-success/5 text-status-success' : 'border-status-error/30 bg-status-error/5 text-status-error'}`} role="status">{notice.tone === 'success' ? <CheckCircle2 size={16} /> : <XCircle size={16} />}<span>{notice.text}</span></div>}
        <div className="mt-6 flex flex-wrap justify-end gap-3"><button type="button" className="desktop-secondary-action" onClick={() => test.mutate()} disabled={busy}>{test.isPending ? <LoaderCircle size={15} className="spin" /> : <TestTube2 size={15} />} {t('desktop:settings.test')}</button><button type="button" className="desktop-primary-action" onClick={() => save.mutate()} disabled={busy}><Save size={15} /> {save.isPending ? t('desktop:settings.saving') : t('desktop:settings.save')}</button></div>
      </section>
    </div>
  );
}

function Field({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return <label className="grid gap-2"><span className="text-sm font-medium text-text">{label}</span>{children}{hint && <span className="text-xs leading-5 text-text-muted">{hint}</span>}</label>;
}

function OverrideNotice({ variable }: { variable?: string }) {
  const { t } = useTranslation('desktop');
  return <span className="mt-1 flex items-center gap-1 text-xs text-text-muted"><Info size={13} /> {t('settings.environmentOverride')}{variable ? `: ${variable}` : ''}</span>;
}
