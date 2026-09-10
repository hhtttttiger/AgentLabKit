import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Download, Upload } from 'lucide-react';
import { FormModal } from '@/shared/ui/FormModal';
import { Button } from '@/shared/ui/Button';
import type { KbQaImportResult } from '../../../lib/contracts';
import { useDocumentMutations } from '../hooks';

function buildTemplateCsv(header: string, row: (number: number) => string): string {
  return `\uFEFF${header}\n${row(1)}\n${row(2)}\n`;
}

function downloadTemplate(csv: string) {
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
  const { t } = useTranslation(['common', 'knowledgeBase']);
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
          errors: [{ rowNumber: 0, errorCode: 'import_failed', message: t('knowledgeBase:qaImport.failed') }],
        });
      },
    });
  };

  return (
    <FormModal
      open={open}
      title={t('knowledgeBase:qaImport.title')}
      description={t('knowledgeBase:qaImport.description')}
      onClose={handleClose}
      footer={
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={handleClose}>
            {t('common:actions.cancel')}
          </Button>
          <Button onClick={handleSubmit} disabled={!file || importQa.isPending}>
            {importQa.isPending ? t('knowledgeBase:qaImport.importing') : t('knowledgeBase:qaImport.confirm')}
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
              <div className="text-xs text-text-muted">{t('knowledgeBase:qaImport.replaceFile')}</div>
            </>
          ) : (
            <>
              <div className="text-sm font-medium text-text">{t('knowledgeBase:qaImport.uploadPrompt')}</div>
              <div className="text-xs text-text-muted">{t('knowledgeBase:qaImport.formatsHint')}</div>
            </>
          )}
        </label>

        <div className="flex items-center justify-center gap-2 text-sm text-text-muted">
          <span>{t('knowledgeBase:qaImport.noTemplate')}</span>
          <button
            type="button"
            onClick={() =>
              downloadTemplate(
                buildTemplateCsv(
                  t('knowledgeBase:qaImport.templateHeader'),
                  (number) => t('knowledgeBase:qaImport.templateRow', { number }),
                ),
              )
            }
            className="inline-flex items-center gap-1 font-medium text-primary transition hover:underline"
          >
            <Download size={14} />
            {t('knowledgeBase:qaImport.downloadTemplate')}
          </button>
        </div>

        {result ? (
          <div className="space-y-3 rounded-[2px] border border-border bg-surface/70 p-4">
            <div className="flex flex-wrap gap-4 text-sm">
              <span className="text-text">
                {t('knowledgeBase:qaImport.createdCount', { count: result.createdCount })}
              </span>
              <span className="text-text">
                {t('knowledgeBase:qaImport.updatedCount', { count: result.updatedCount })}
              </span>
              <span className="text-text-muted">
                {t('knowledgeBase:qaImport.skippedCount', { count: result.skippedCount })}
              </span>
            </div>
            {result.errors.length > 0 ? (
              <ul className="space-y-1 text-sm text-text-secondary">
                {result.errors.map((err) => (
                  <li key={`${err.rowNumber}-${err.errorCode}`} className="flex gap-2">
                    {err.rowNumber > 0 && (
                      <span className="shrink-0 font-medium text-text-muted">{t('knowledgeBase:qaImport.rowNumber', { number: err.rowNumber })}</span>
                    )}
                    <span>{err.message}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-text-secondary">{t('knowledgeBase:qaImport.noRowErrors')}</p>
            )}
          </div>
        ) : null}
      </div>
    </FormModal>
  );
}
