import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useBudgetList, useCreateBudget, useDeleteBudget } from './hooks';
import { fetchModelOptions, fetchAgentOptions, fetchUserOptions } from './api';
import { useTranslation } from 'react-i18next';
import { Button } from '@/shared/ui/Button';
import { EmptyState } from '@/shared/ui/EmptyState';
import { InlineMessage } from '@/shared/ui/InlineMessage';
import { SkeletonRows } from '@/shared/ui/Skeleton';
import { FormModal } from '@/shared/ui/FormModal';
import { SelectField, TextField } from '@/shared/ui/FormFields';
import { formatCost } from '../../lib/formatters';
import type { BudgetData } from '../../lib/contracts';

// ── 常量 ──────────────────────────────────────────────────────────────

interface BudgetForm {
  scopeType: string;
  scopeKey: string;
  monthlyLimitUsd: number;
  alertThresholdPct: number;
}

const EMPTY_FORM: BudgetForm = { scopeType: 'global', scopeKey: '*', monthlyLimitUsd: 100, alertThresholdPct: 80 };

// ── 组件 ──────────────────────────────────────────────────────────────

export function BudgetsPage() {
  const { t } = useTranslation(['common', 'costAnalysis']);
  const { data: budgets, isLoading, isError, error } = useBudgetList();
  const createMutation = useCreateBudget();
  const deleteMutation = useDeleteBudget();
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState<BudgetForm>(EMPTY_FORM);

  // 打开模态框时重置表单
  useEffect(() => { if (open) setForm(EMPTY_FORM); }, [open]);

  // 按需加载下拉选项（仅在模态框打开且对应类型时请求）
  const { data: modelOptions } = useQuery({
    queryKey: ['options', 'models'],
    queryFn: fetchModelOptions,
    enabled: open && form.scopeType === 'model',
    staleTime: 60_000,
  });
  const { data: agentOptions } = useQuery({
    queryKey: ['options', 'agents'],
    queryFn: fetchAgentOptions,
    enabled: open && form.scopeType === 'agent',
    staleTime: 60_000,
  });
  const { data: userOptions } = useQuery({
    queryKey: ['options', 'users'],
    queryFn: fetchUserOptions,
    enabled: open && form.scopeType === 'user',
    staleTime: 60_000,
  });

  const handleCreate = async () => {
    await createMutation.mutateAsync(form);
    setOpen(false);
  };

  if (isLoading) {
    return <div className="p-6"><SkeletonRows columns={6} rows={5} /></div>;
  }

  if (isError) {
    return (
      <div className="p-6">
        <InlineMessage tone="error">
          {error?.message ?? t('costAnalysis:budgets.error')}
        </InlineMessage>
      </div>
    );
  }

  const scopeLabel = (scopeType: string) => t(`costAnalysis:budgets.scope.${scopeType}`, scopeType);

  return (
    <div className="flex flex-col gap-4 p-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-text">{t('costAnalysis:budgets.title')}</h2>
        <Button onClick={() => setOpen(true)}>{t('costAnalysis:budgets.createBudget')}</Button>
      </div>

      {/* 创建预算模态框 */}
      <FormModal
        open={open}
        title={t('costAnalysis:budgets.form.title')}
        description={t('costAnalysis:budgets.form.description')}
        onClose={() => setOpen(false)}
        footer={
          <div className="flex justify-end gap-3">
            <Button variant="secondary" onClick={() => setOpen(false)}>
              {t('costAnalysis:budgets.actions.cancel')}
            </Button>
            <Button
              variant="primary"
              onClick={handleCreate}
              disabled={createMutation.isPending || !form.scopeKey || !form.monthlyLimitUsd}
            >
              {createMutation.isPending ? t('costAnalysis:budgets.actions.creating') : t('costAnalysis:budgets.actions.create')}
            </Button>
          </div>
        }
      >
        <div className="flex flex-col gap-4">
          {/* 范围类型 */}
          <SelectField
            label={t('costAnalysis:budgets.form.scopeType')}
            value={form.scopeType}
            onChange={(e) => {
              const st = e.target.value;
              setForm({ ...form, scopeType: st, scopeKey: st === 'global' ? '*' : '' });
            }}
          >
            {['global', 'model', 'agent', 'user'].map((k) => (
              <option key={k} value={k}>{scopeLabel(k)}</option>
            ))}
          </SelectField>

          {/* scopeKey — 按类型动态切换 */}
          {form.scopeType === 'global' ? (
            <TextField label={t('costAnalysis:budgets.form.scopeKey')} value="*" disabled />
          ) : form.scopeType === 'model' ? (
            <SelectField
              label={t('costAnalysis:budgets.form.scopeKey')}
              value={form.scopeKey}
              onChange={(e) => setForm({ ...form, scopeKey: e.target.value })}
            >
              <option value="">{'--'}</option>
              {(modelOptions ?? []).map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </SelectField>
          ) : form.scopeType === 'agent' ? (
            <SelectField
              label={t('costAnalysis:budgets.form.scopeKey')}
              value={form.scopeKey}
              onChange={(e) => setForm({ ...form, scopeKey: e.target.value })}
            >
              <option value="">{'--'}</option>
              {(agentOptions ?? []).map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </SelectField>
          ) : (
            <SelectField
              label={t('costAnalysis:budgets.form.scopeKey')}
              value={form.scopeKey}
              onChange={(e) => setForm({ ...form, scopeKey: e.target.value })}
            >
              <option value="">{'--'}</option>
              {(userOptions ?? []).map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </SelectField>
          )}

          {/* 月度预算 */}
          <TextField
            label={t('costAnalysis:budgets.form.monthlyLimit')}
            type="number"
            value={String(form.monthlyLimitUsd)}
            onChange={(e) => setForm({ ...form, monthlyLimitUsd: Number(e.target.value) })}
          />

          {/* 告警阈值 */}
          <TextField
            label={t('costAnalysis:budgets.form.alertThreshold')}
            type="number"
            min={0}
            max={100}
            value={String(form.alertThresholdPct)}
            onChange={(e) => setForm({ ...form, alertThresholdPct: Number(e.target.value) })}
          />
        </div>
      </FormModal>

      {/* 预算列表 */}
      {!budgets?.length ? (
        <EmptyState title={t('costAnalysis:budgets.emptyTitle')} description={t('costAnalysis:budgets.emptyDescription')} />
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-text-muted">
              <th className="pb-2 font-medium">{t('costAnalysis:budgets.form.scopeType')}</th>
              <th className="pb-2 font-medium">{t('costAnalysis:budgets.form.scopeKey')}</th>
              <th className="pb-2 font-medium text-right">{t('costAnalysis:budgets.columns.limit')}</th>
              <th className="pb-2 font-medium text-right">{t('costAnalysis:budgets.form.alertThreshold')}</th>
              <th className="pb-2 font-medium text-center">{t('costAnalysis:budgets.columns.status')}</th>
              <th className="pb-2 font-medium text-right">{t('costAnalysis:budgets.columns.actions')}</th>
            </tr>
          </thead>
          <tbody>
            {budgets.map((b: BudgetData) => (
              <tr key={b.id} className="border-b border-border-subtle last:border-0">
                <td className="py-2 text-text">{scopeLabel(b.scopeType)}</td>
                <td className="py-2 text-text-secondary">{b.scopeKey}</td>
                <td className="py-2 text-right font-medium text-text">{formatCost(b.monthlyLimitUsd)}</td>
                <td className="py-2 text-right text-text-secondary">{b.alertThresholdPct}%</td>
                <td className="py-2 text-center">
                  <span className={`inline-block rounded-[2px] px-2 py-0.5 text-xs ${b.isEnabled ? 'bg-success/10 text-success' : 'bg-text-muted/10 text-text-muted'}`}>
                    {t(b.isEnabled ? 'costAnalysis:budgets.status.active' : 'costAnalysis:budgets.status.inactive')}
                  </span>
                </td>
                <td className="py-2 text-right">
                  <button
                    className="text-xs text-error hover:underline"
                    onClick={() => deleteMutation.mutate(b.id)}
                    aria-label={`${t('costAnalysis:budgets.actions.delete')} ${b.scopeType}:${b.scopeKey}`}
                  >
                    {t('costAnalysis:budgets.actions.delete')}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
