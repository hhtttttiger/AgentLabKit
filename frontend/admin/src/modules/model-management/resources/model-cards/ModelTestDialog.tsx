/**
 * Model Test Dialog - 针对文本模型的对话测试弹窗。
 * 流式对话,每轮 AI 回复下方紧凑显示诊断(实例 / TTFT / 耗时 / token / 错误)。
 */

import { Fragment, useEffect, useRef, useState } from 'react';
import type { KeyboardEvent, ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { Send, Square } from 'lucide-react';
import { Modal } from '@/shared/ui/Modal';
import { Button } from '@/shared/ui/Button';
import { ChatMessageBubble } from '@/modules/ai-chat/components/ChatMessageBubble';
import type { ChatMessage } from '@/modules/ai-chat/lib/contracts';
import type { LlmModelView } from '../../lib/contracts';
import { streamModelTest } from './test-api';
import type { ModelTestDiagnosis } from './test-types';

type DiagnosisMap = Record<string, ModelTestDiagnosis>;

export interface ModelTestDialogProps {
  open: boolean;
  model: LlmModelView | null;
  onClose: () => void;
}

const NS = 'modules.modelManagement.models.test';

/** Maximum number of messages retained in the test dialog to prevent unbounded memory growth. */
const MAX_MESSAGES = 500;

export function ModelTestDialog({ open, model, onClose }: ModelTestDialogProps) {
  const { t } = useTranslation();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [diagnoses, setDiagnoses] = useState<DiagnosisMap>({});
  const [input, setInput] = useState('');
  const [streaming, setStreaming] = useState(false);
  const abortRef = useRef<(() => void) | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  // 切换模型时重置会话。
  useEffect(() => {
    abortRef.current?.();
    abortRef.current = null;
    setMessages([]);
    setDiagnoses({});
    setInput('');
    setStreaming(false);
  }, [model?.modelKey]);

  // 新消息时滚到底部。
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = () => {
    const text = input.trim();
    if (!text || !model || streaming) {
      return;
    }
    setInput('');

    const now = Date.now();
    const userMsg: ChatMessage = { id: genId(), role: 'user', content: text, timestamp: now, status: 'sent' };
    const assistantId = genId();
    const assistantMsg: ChatMessage = { id: assistantId, role: 'assistant', content: '', timestamp: now, status: 'sending' };
    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setDiagnoses((prev) => {
      const next = { ...prev };
      delete next[assistantId];
      return next;
    });
    setStreaming(true);

    abortRef.current = streamModelTest(
      model.modelKey,
      { message: text },
      {
        onContent: (delta, meta) => {
          setMessages((prev) => prev.map((m) => (m.id === assistantId ? { ...m, content: m.content + delta } : m)));
          setDiagnoses((prev) => ({
            ...prev,
            [assistantId]: {
              ...prev[assistantId],
              instanceKey: prev[assistantId]?.instanceKey ?? meta.instanceKey,
              provider: prev[assistantId]?.provider ?? meta.provider,
              model: prev[assistantId]?.model ?? meta.model,
            },
          }));
        },
        onStats: (diag) => {
          setDiagnoses((prev) => ({ ...prev, [assistantId]: { ...prev[assistantId], ...diag } }));
          setMessages((prev) =>
            prev.map((m) => (m.id === assistantId ? { ...m, status: 'sent' } : m)),
          );
        },
        onError: (diag) => {
          setDiagnoses((prev) => ({ ...prev, [assistantId]: { ...prev[assistantId], ...diag } }));
          setMessages((prev) =>
            prev.map((m) => (m.id === assistantId ? { ...m, status: 'failed', error: diag.errorMessage } : m)),
          );
        },
        onComplete: () => {
          setStreaming(false);
          abortRef.current = null;
          // Trim old messages beyond MAX_MESSAGES to prevent unbounded memory growth
          setMessages((prev) => {
            if (prev.length <= MAX_MESSAGES) return prev;
            const trimmed = prev.slice(prev.length - MAX_MESSAGES);
            const keepIds = new Set(trimmed.map((m) => m.id));
            setDiagnoses((dprev) => {
              const next: DiagnosisMap = {};
              for (const [id, diag] of Object.entries(dprev)) {
                if (keepIds.has(id)) next[id] = diag;
              }
              return next;
            });
            return trimmed;
          });
        },
      },
    );
  };

  const handleStop = () => {
    abortRef.current?.();
    abortRef.current = null;
    setStreaming(false);
    setMessages((prev) => prev.map((m) => (m.status === 'sending' ? { ...m, status: 'sent' } : m)));
  };

  const handleClose = () => {
    abortRef.current?.();
    abortRef.current = null;
    setStreaming(false);
    onClose();
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <Modal
      open={open}
      title={t(`${NS}.title`)}
      description={model?.displayName}
      onClose={handleClose}
      widthClassName="max-w-3xl"
    >
      <div className="flex h-[60vh] flex-col">
        <div ref={scrollRef} className="min-h-0 flex-1 overflow-auto pr-1">
          {messages.length === 0 ? (
            <div className="flex h-full items-center justify-center text-sm text-text-muted">
              {t(`${NS}.empty`)}
            </div>
          ) : (
            <div className="space-y-3">
              {messages.map((m) => (
                <div key={m.id}>
                  <ChatMessageBubble message={m} />
                  {m.role === 'assistant' && (
                    <DiagnosisBar diagnosis={diagnoses[m.id]} generating={m.status === 'sending'} />
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="mt-3 shrink-0 border-t border-border-subtle pt-3">
          <div className="flex items-end gap-2">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKeyDown}
              rows={2}
              placeholder={t(`${NS}.inputPlaceholder`)}
              className="flex-1 resize-none rounded-[2px] border border-border bg-surface px-3 py-2 text-sm text-text placeholder:text-text-muted focus:border-primary focus:outline-none"
            />
            {streaming ? (
              <Button variant="secondary" onClick={handleStop}>
                <Square size={14} />
                {t(`${NS}.stop`)}
              </Button>
            ) : (
              <Button variant="primary" onClick={handleSend} disabled={!input.trim() || !model}>
                <Send size={14} />
                {t(`${NS}.send`)}
              </Button>
            )}
          </div>
        </div>
      </div>
    </Modal>
  );
}

function DiagnosisBar({ diagnosis, generating }: { diagnosis?: ModelTestDiagnosis; generating: boolean }) {
  const { t } = useTranslation();
  const items: ReactNode[] = [];
  if (diagnosis?.instanceKey) {
    items.push(<span className="font-medium text-text-secondary">{diagnosis.instanceKey}</span>);
  }
  if (diagnosis?.provider) {
    items.push(<span>{diagnosis.provider}</span>);
  }
  if (diagnosis?.ttftMs != null) {
    items.push(
      <span className={ttftToneClass(diagnosis.ttftMs)}>
        {t(`${NS}.diagnosis.ttft`)} {formatMs(diagnosis.ttftMs)}
        {diagnosis.ttftMs > 10000 ? ' ⚠' : ''}
      </span>,
    );
  }
  if (diagnosis?.totalMs != null) {
    items.push(<span>{formatMs(diagnosis.totalMs)}</span>);
  }
  if (diagnosis?.inputTokens != null || diagnosis?.outputTokens != null) {
    items.push(
      <span>
        {formatTok(diagnosis.inputTokens)}→{formatTok(diagnosis.outputTokens)} tok
      </span>,
    );
  }
  if (diagnosis?.finishReason) {
    items.push(<span>{diagnosis.finishReason}</span>);
  }
  if (diagnosis?.errorMessage) {
    items.push(<span className="text-error">{diagnosis.errorMessage}</span>);
  }

  if (items.length === 0) {
    return generating ? <div className="mt-1.5 text-[11px] text-text-muted">{t(`${NS}.generating`)}</div> : null;
  }
  return (
    <div className="mt-1.5 flex flex-wrap items-center gap-x-1.5 gap-y-0.5 text-[11px] text-text-muted">
      {items.map((node, i) => (
        <Fragment key={i}>
          {i > 0 && <span className="opacity-40">·</span>}
          {node}
        </Fragment>
      ))}
    </div>
  );
}

function formatMs(ms: number | null | undefined): string {
  if (ms == null) return '—';
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function formatTok(value: number | null | undefined): string {
  return value == null ? '—' : String(value);
}

function ttftToneClass(ms: number | null | undefined): string {
  if (ms == null || ms < 2000) return 'text-text-muted';
  if (ms <= 10000) return 'text-amber-600 dark:text-amber-400';
  return 'text-error';
}

function genId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}
