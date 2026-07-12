/**
 * Model Embedding Test Dialog — embedding 模型测试。
 *
 * 调用 POST /api/ai/invoke/{modelId}/embedding/test，展示向量预览及诊断信息。
 */
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { BeakerIcon } from 'lucide-react';
import { Button } from '@/shared/ui/Button';
import { Modal } from '@/shared/ui/Modal';
import { InlineMessage } from '@/shared/ui/InlineMessage';
import type { LlmModelView } from '../../lib/contracts';
import { testEmbedding, type EmbeddingTestRequest } from './test-api';
import type { EmbeddingTestResult } from './test-types';

const NS = 'modelManagement:models.embeddingTest';

export function ModelEmbeddingTestDialog({
  open,
  model,
  onClose,
}: {
  open: boolean;
  model: LlmModelView | null;
  onClose: () => void;
}) {
  const { t } = useTranslation(['common', 'modelManagement']);
  const [text, setText] = useState('');
  const [dimensions, setDimensions] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<EmbeddingTestResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [_abort, _setAbort] = useState<AbortController | null>(null);

  const handleClose = () => {
    setText('');
    setDimensions('');
    setResult(null);
    setError(null);
    setLoading(false);
    onClose();
  };

  const handleTest = async () => {
    if (!model || !text.trim()) return;

    setLoading(true);
    setError(null);
    setResult(null);

    const controller = new AbortController();
    _setAbort(controller);

    try {
      const req: EmbeddingTestRequest = { text: text.trim() };
      if (dimensions.trim()) {
        const d = parseInt(dimensions.trim(), 10);
        if (!isNaN(d) && d > 0) {
          req.dimensions = d;
        }
      }
      const data = await testEmbedding(model.modelKey, req, controller.signal);
      setResult(data);
    } catch (e) {
      setError((e as Error).message || String(e));
    } finally {
      setLoading(false);
    }
  };

  const modelName = model?.displayName || model?.modelKey || '';

  return (
    <Modal open={open} onClose={handleClose} title={t(`${NS}.title`, { model: modelName })} width="max-w-xl">
      <div className="flex flex-col gap-4">
        {/* Text Input */}
        <div>
          <label className="mb-1 block text-sm font-medium text-text">
            {t(`${NS}.textLabel`)}
          </label>
          <textarea
            className="w-full min-h-[80px] rounded-[2px] border border-border bg-surface px-3 py-2 text-sm text-text placeholder-text-muted focus:border-primary focus:outline-none"
            placeholder={t(`${NS}.textPlaceholder`)}
            value={text}
            onChange={(e) => setText(e.target.value)}
            disabled={loading}
            rows={3}
          />
        </div>

        {/* Dimensions (optional) */}
        <div>
          <label className="mb-1 block text-sm font-medium text-text">
            {t(`${NS}.dimensionsLabel`)}
          </label>
          <input
            type="number"
            className="w-full max-w-[200px] rounded-[2px] border border-border bg-surface px-3 py-2 text-sm text-text placeholder-text-muted focus:border-primary focus:outline-none"
            placeholder={t(`${NS}.dimensionsPlaceholder`)}
            value={dimensions}
            onChange={(e) => setDimensions(e.target.value)}
            disabled={loading}
            min={1}
          />
          <p className="mt-1 text-xs text-text-muted">{t(`${NS}.dimensionsHint`)}</p>
        </div>

        {/* Actions */}
        <div className="flex items-center justify-between gap-3">
          <Button variant="secondary" onClick={handleClose} disabled={loading}>
            {t(`${NS}.close`)}
          </Button>
          <Button onClick={handleTest} disabled={loading || !text.trim()}>
            {loading ? t(`${NS}.testing`) : t(`${NS}.test`)}
          </Button>
        </div>

        {/* Error */}
        {error && <InlineMessage tone="error">{error}</InlineMessage>}

        {/* Result */}
        {result && (
          <div className="rounded-[2px] border border-border bg-surface p-4 space-y-3">
            {result.success ? (
              <>
                {/* Stats Bar */}
                <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-text-muted">
                  {result.provider && <span>{t(`${NS}.provider`)}: <strong className="text-text">{result.provider}</strong></span>}
                  {result.model && <span>{t(`${NS}.model`)}: <strong className="text-text">{result.model}</strong></span>}
                  <span>{t(`${NS}.dimensions`)}: <strong className="text-text">{result.dimensions}</strong></span>
                  <span>{t(`${NS}.latency`)}: <strong className="text-text">{result.latencyMs}ms</strong></span>
                  {result.usage && (
                    <span>{t(`${NS}.tokens`)}: <strong className="text-text">{result.usage.total_tokens ?? result.usage.input_tokens ?? '-'}</strong></span>
                  )}
                </div>

                {/* Vector Preview */}
                <div>
                  <div className="mb-1 text-xs font-medium text-text-secondary">
                    {t(`${NS}.vectorPreview`)}
                    {result.vectorPreviewTruncated && ` (${t(`${NS}.firstN`, { n: result.vectorPreview?.length ?? 10 })})`}
                  </div>
                  <div className="rounded-[2px] bg-background-subtle p-3 font-mono text-xs text-text leading-relaxed break-all max-h-40 overflow-y-auto">
                    [{result.vectorPreview?.map((v) => v.toFixed(6)).join(', ')}]
                  </div>
                </div>
              </>
            ) : (
              <InlineMessage tone="error">
                {result.error?.message || t(`${NS}.unknownError`)}
              </InlineMessage>
            )}
          </div>
        )}

        {/* Empty State */}
        {!result && !error && !loading && (
          <div className="flex flex-col items-center gap-2 py-8 text-text-muted">
            <BeakerIcon size={32} className="opacity-30" />
            <span className="text-sm">{t(`${NS}.empty`)}</span>
          </div>
        )}
      </div>
    </Modal>
  );
}
