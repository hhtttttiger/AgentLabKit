import { useEffect, useState } from 'react';
import { Download, Upload } from 'lucide-react';
import type { GlossaryImportResult } from '../../../lib/contracts';
import { useGlossaryTermMutations } from '../hooks';
import { FormModal } from '@/shared/ui/FormModal';
import { Button } from '@/shared/ui/Button';
import { useTranslation } from 'react-i18next';

function downloadTemplate() {
  const csv = 'term,synonyms,category\nRAG,Retrieval-Augmented Generation|Search-Augmented Generation,AI Development\nEmbedding,Vectorization|Embedding,AI Development\n';
  const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'glossary-template.csv';
  a.click();
  URL.revokeObjectURL(url);
}

export function TermImportDrawer({
  open,
  categoryId,
  onClose,
}: {
  open: boolean;
  categoryId?: string;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const { importTerms } = useGlossaryTermMutations();
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<GlossaryImportResult | null>(null);

  useEffect(() => {
    if (!open) {
      return;
    }

    setFile(null);
    setResult(null);
  }, [categoryId, open]);

  const handleClose = () => {
    setFile(null);
    setResult(null);
    onClose();
  };

  const handleSubmit = () => {
    if (!file || importTerms.isPending) {
      return;
    }

    importTerms.mutate(file, {
      onSuccess: (nextResult) => {
        setResult(nextResult);
      },
      onError: (error) => {
        setResult({
          importedCount: 0,
          errors: [error instanceof Error ? error.message : t('modules.glossary.termImport.errorFallback')],
        });
      },
    });
  };

  return (
    <FormModal
      open={open}
      title={t('modules.glossary.termImport.title')}
      description={t('modules.glossary.termImport.description')}
      onClose={handleClose}
      footer={
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={handleClose}>
            {t('modules.glossary.termImport.actions.cancel')}
          </Button>
          <Button onClick={handleSubmit} disabled={!file || importTerms.isPending}>
            {importTerms.isPending ? t('modules.glossary.termImport.actions.importing') : t('modules.glossary.termImport.actions.submit')}
          </Button>
        </div>
      }
    >
      <div className="space-y-4">
        <input
          id="glossary-term-import-file"
          type="file"
          accept=".csv"
          className="hidden"
          onChange={(event) => {
            setFile(event.target.files?.[0] ?? null);
            setResult(null);
          }}
        />
        <label
          htmlFor="glossary-term-import-file"
          className="flex cursor-pointer flex-col items-center gap-3 rounded-[2px] border-2 border-dashed border-border bg-surface/40 px-6 py-10 text-center transition hover:border-primary/40 hover:bg-primary-subtle/10"
        >
          <div className="flex h-12 w-12 items-center justify-center rounded-[2px] bg-primary-subtle">
            <Upload size={22} className="text-primary" />
          </div>
          {file ? (
            <>
              <div className="text-sm font-medium text-text">{file.name}</div>
              <div className="text-xs text-text-muted">{t('modules.glossary.termImport.upload.replaceFile')}</div>
            </>
          ) : (
            <>
              <div className="text-sm font-medium text-text">{t('modules.glossary.termImport.upload.selectFile')}</div>
              <div className="text-xs text-text-muted">{t('modules.glossary.termImport.upload.hint')}</div>
            </>
          )}
        </label>

        <div className="flex items-center justify-center gap-2 text-sm text-text-muted">
          <span>{t('modules.glossary.termImport.template.prompt')}</span>
          <button
            type="button"
            onClick={downloadTemplate}
            className="inline-flex items-center gap-1 font-medium text-primary transition hover:underline"
          >
            <Download size={14} />
            {t('modules.glossary.termImport.actions.downloadTemplate')}
          </button>
        </div>

        {result ? (
          <div className="space-y-3 rounded-[2px] border border-border bg-surface/70 p-4">
            <div className="text-sm font-medium text-text">{t('modules.glossary.termImport.result.importedCount', { count: result.importedCount })}</div>
            {result.errors.length ? (
              <ul className="list-disc space-y-1 pl-5 text-sm text-text-secondary">
                {result.errors.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-text-secondary">{t('modules.glossary.termImport.result.noErrors')}</p>
            )}
          </div>
        ) : null}
      </div>
    </FormModal>
  );
}
