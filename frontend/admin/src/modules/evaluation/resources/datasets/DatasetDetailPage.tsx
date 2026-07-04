import { useParams, useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { useCaseList, useCreateCases, useDeleteCase } from './hooks';
import { useTranslation } from 'react-i18next';
import { useToast } from '@/shared/ui/Toast';

export function DatasetDetailPage() {
  const { t } = useTranslation('common');
  const { toast } = useToast();
  const { datasetId } = useParams<{ datasetId: string }>();
  const navigate = useNavigate();
  const id = datasetId ?? '';
  const { data: cases, isLoading } = useCaseList(id);
  const createCasesMutation = useCreateCases(id);
  const deleteCaseMutation = useDeleteCase();
  const [input, setInput] = useState('');
  const [expected, setExpected] = useState('');

  const addCase = async () => {
    if (!input.trim() || !id) return;
    await createCasesMutation.mutateAsync([{ inputText: input.trim(), expectedOutput: expected.trim() || undefined }]);
    setInput(''); setExpected('');
    toast(t('toast.created'));
  };

  const handleDeleteCase = async (caseId: string) => {
    if (!id) return;
    await deleteCaseMutation.mutateAsync({ datasetId: id, caseId });
    toast(t('toast.deleted'));
  };

  return (
    <div className="flex flex-col gap-4 p-6">
      <button onClick={() => navigate('/evaluation')} className="text-sm text-text-secondary hover:text-primary">← 返回数据集</button>
      <h2 className="text-lg font-semibold text-text">数据集 #{id} — 测试用例</h2>

      <div className="flex gap-3">
        <textarea className="flex-1 rounded-[2px] border border-border bg-background px-3 py-2 text-sm" rows={2} placeholder="输入问题" value={input} onChange={(e) => setInput(e.target.value)} />
        <textarea className="flex-1 rounded-[2px] border border-border bg-background px-3 py-2 text-sm" rows={2} placeholder="期望输出（可选）" value={expected} onChange={(e) => setExpected(e.target.value)} />
        <button
          onClick={addCase}
          disabled={createCasesMutation.isPending || !input.trim()}
          className="shrink-0 rounded-[2px] bg-primary px-4 py-2 text-xs text-background disabled:opacity-30"
        >
          {createCasesMutation.isPending ? '添加中...' : '添加'}
        </button>
      </div>

      {isLoading ? (
        <div className="py-8 text-center text-text-muted">{t('states.loading')}</div>
      ) : !cases?.length ? (
        <div className="py-8 text-center text-text-muted">{t('states.empty')}</div>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-text-muted">
              <th className="pb-2 font-medium">#</th>
              <th className="pb-2 font-medium">输入</th>
              <th className="pb-2 font-medium">期望输出</th>
              <th className="pb-2 font-medium text-right">操作</th>
            </tr>
          </thead>
          <tbody>
            {cases.map((c) => (
              <tr key={c.id} className="border-b border-border-subtle last:border-0">
                <td className="py-2 text-text-secondary">{c.caseIndex}</td>
                <td className="py-2 text-text">{c.inputText.slice(0, 100)}{c.inputText.length > 100 ? '…' : ''}</td>
                <td className="py-2 text-text-secondary">{(c.expectedOutput || '—').slice(0, 80)}</td>
                <td className="py-2 text-right">
                  <button
                    onClick={() => handleDeleteCase(c.id)}
                    disabled={deleteCaseMutation.isPending}
                    className="text-xs text-error hover:underline disabled:opacity-30"
                  >
                    删除
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
