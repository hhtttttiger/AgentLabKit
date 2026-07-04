import { useEffect, useState } from 'react';
import { Download, Upload } from 'lucide-react';
import { FormModal } from '@/shared/ui/FormModal';
import { Button } from '@/shared/ui/Button';
import type { KbQaImportResult } from '../../../lib/contracts';
import { useDocumentMutations } from '../hooks';

function downloadTemplate() {
  const csv = '\uFEFF问题,答案\n问题示例1,答案示例1\n问题示例2,答案示例2\n';
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'qa-import-template.csv';
  a.click();
  URL.revokeObjectURL(url);
}

export function QaImportDrawer({
  kbId,
  folderId,
  open,
  onClose,
}: {
  kbId: string;
  folderId?: string | null;
  open: boolean;
  onClose: () => void;
}) {
  const { importQa } = useDocumentMutations(kbId);
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<KbQaImportResult | null>(null);

  useEffect(() => {
    if (!open) return;
    setFile(null);
    setResult(null);
  }, [open]);

  const handleClose = () => {
    setFile(null);
    setResult(null);
    onClose();
  };

  const handleSubmit = () => {
    if (!file || importQa.isPending) return;

    importQa.mutate({ file, folderId }, {
      onSuccess: (nextResult) => {
        setResult(nextResult);
      },
      onError: () => {
        setResult({
          createdCount: 0,
          updatedCount: 0,
          skippedCount: 0,
          errors: [{ rowNumber: 0, errorCode: 'import_failed', message: '导入失败，请稍后重试。' }],
        });
      },
    });
  };

  return (
    <FormModal
      open={open}
      title="导入 QA"
      description="上传 CSV 或 XLSX 文件，第一行为标题行（将被忽略），第二列起：第一列为问题，第二列为答案。"
      onClose={handleClose}
      footer={
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={handleClose}>
            取消
          </Button>
          <Button onClick={handleSubmit} disabled={!file || importQa.isPending}>
            {importQa.isPending ? '导入中...' : '确认导入'}
          </Button>
        </div>
      }
    >
      <div className="space-y-4">
        <input
          id="qa-import-file"
          type="file"
          accept=".csv,.xlsx"
          className="hidden"
          onChange={(e) => {
            setFile(e.target.files?.[0] ?? null);
            setResult(null);
          }}
        />
        <label
          htmlFor="qa-import-file"
          className="flex cursor-pointer flex-col items-center gap-3 rounded-[2px] border-2 border-dashed border-border bg-surface/40 px-6 py-10 text-center transition hover:border-primary/40 hover:bg-primary-subtle/10"
        >
          <div className="flex h-12 w-12 items-center justify-center rounded-[2px] bg-primary-subtle">
            <Upload size={22} className="text-primary" />
          </div>
          {file ? (
            <>
              <div className="text-sm font-medium text-text">{file.name}</div>
              <div className="text-xs text-text-muted">点击重新选择文件</div>
            </>
          ) : (
            <>
              <div className="text-sm font-medium text-text">点击上传文件</div>
              <div className="text-xs text-text-muted">支持 .csv / .xlsx 格式</div>
            </>
          )}
        </label>

        <div className="flex items-center justify-center gap-2 text-sm text-text-muted">
          <span>没有模板？</span>
          <button
            type="button"
            onClick={downloadTemplate}
            className="inline-flex items-center gap-1 font-medium text-primary transition hover:underline"
          >
            <Download size={14} />
            下载导入模板
          </button>
        </div>

        {result ? (
          <div className="space-y-3 rounded-[2px] border border-border bg-surface/70 p-4">
            <div className="flex flex-wrap gap-4 text-sm">
              <span className="text-text">
                新建 <strong className="text-primary">{result.createdCount}</strong> 条
              </span>
              <span className="text-text">
                更新 <strong className="text-primary">{result.updatedCount}</strong> 条
              </span>
              <span className="text-text">
                跳过 <strong className="text-text-muted">{result.skippedCount}</strong> 条
              </span>
            </div>
            {result.errors.length > 0 ? (
              <ul className="space-y-1 text-sm text-text-secondary">
                {result.errors.map((err) => (
                  <li key={`${err.rowNumber}-${err.errorCode}`} className="flex gap-2">
                    {err.rowNumber > 0 && (
                      <span className="shrink-0 font-medium text-text-muted">第 {err.rowNumber} 行</span>
                    )}
                    <span>{err.message}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-text-secondary">无行级错误。</p>
            )}
          </div>
        ) : null}
      </div>
    </FormModal>
  );
}
