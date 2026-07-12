/**
 * AI Chat Module — Chat Input Area
 * Text input with auto-resize, send/stop toggle, and model selector.
 */
import { useState, useRef, useEffect, type KeyboardEvent } from 'react';
import { ArrowUp, Mic, Plus, SlidersHorizontal, Square } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { ModelSelector } from './ModelSelector';
import type { ModelOption } from '../lib/contracts';

type ChatInputAreaProps = {
  onSend: (message: string) => void;
  onStop?: () => void;
  disabled?: boolean;
  isStreaming?: boolean;
  placeholder?: string;
  agentOptions: ModelOption[];
  modelOptions: ModelOption[];
  selectedModel: ModelOption | null;
  onSelectModel: (model: ModelOption) => void;
};

export function ChatInputArea({
  onSend,
  onStop,
  disabled = false,
  isStreaming = false,
  placeholder,
  agentOptions,
  modelOptions,
  selectedModel,
  onSelectModel,
}: ChatInputAreaProps) {
  const { t } = useTranslation(['common', 'aiChat']);
  const [input, setInput] = useState('');
  const resolvedPlaceholder = placeholder ?? t('aiChat:input.placeholder');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea based on content
  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = 'auto';
    textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
  }, [input]);

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (isStreaming) {
        onStop?.();
      } else {
        handleSend();
      }
    }
  };

  return (
    <div className="border-t border-border px-6 py-4">
      <textarea
        ref={textareaRef}
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={resolvedPlaceholder}
        disabled={disabled && !isStreaming}
        rows={1}
        className="w-full resize-none border-0 bg-transparent px-1 py-1 text-[15px] leading-7 text-text placeholder:text-text-muted-subtle focus:outline-none focus:ring-0 disabled:cursor-not-allowed disabled:opacity-50"
        style={{ minHeight: '42px', maxHeight: '160px' }}
      />
      <div className="mt-2 flex flex-wrap items-center justify-between gap-3 pt-1">
        <div className="flex items-center gap-2 text-text-muted">
          <button
            type="button"
            className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-border-subtle bg-surface-subtle/80 transition hover:border-border hover:bg-surface"
            title={t('aiChat:input.addAttachment')}
          >
            <Plus className="h-4 w-4" />
          </button>
          <button
            type="button"
            className="inline-flex items-center gap-2 rounded-full border border-border-subtle bg-surface-subtle/80 px-3 py-2 text-sm transition hover:border-border hover:bg-surface"
            title={t('aiChat:input.toolSettings')}
          >
            <SlidersHorizontal className="h-4 w-4" />
            <span>{t('aiChat:input.toolLabel')}</span>
          </button>
        </div>

        <div className="flex flex-wrap items-center justify-end gap-3">
          <button
            type="button"
            className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-transparent text-text-muted transition hover:bg-surface-subtle hover:text-text"
            title={t('aiChat:input.voiceInput')}
          >
            <Mic className="h-4 w-4" />
          </button>

          {/* Send / Stop toggle */}
          {isStreaming ? (
            <button
              type="button"
              onClick={() => onStop?.()}
              className="inline-flex h-10 w-10 items-center justify-center rounded-full text-white transition hover:translate-y-[-1px] disabled:translate-y-0 disabled:cursor-not-allowed disabled:opacity-45"
              style={{
                background: 'rgb(var(--color-error))',
                boxShadow: '0 10px 20px rgb(var(--color-error) / 0.20)',
              }}
              title={t('aiChat:input.stopGeneration')}
            >
              <Square className="h-3.5 w-3.5" />
            </button>
          ) : (
            <button
              type="button"
              onClick={handleSend}
              disabled={disabled || !input.trim()}
              className="inline-flex h-10 w-10 items-center justify-center rounded-full text-white transition hover:translate-y-[-1px] disabled:translate-y-0 disabled:cursor-not-allowed disabled:opacity-45 disabled:shadow-none"
              style={{
                background: 'linear-gradient(135deg, rgb(var(--color-primary)), rgb(var(--color-primary-hover)))',
                boxShadow: '0 10px 20px rgb(var(--color-primary) / 0.20)',
              }}
              title={t('aiChat:input.sendMessage')}
            >
              <ArrowUp className="h-4.5 w-4.5" />
            </button>
          )}
        </div>
      </div>

      <div className="mt-3">
        <ModelSelector
          agentOptions={agentOptions}
          modelOptions={modelOptions}
          selectedModel={selectedModel}
          onSelect={onSelectModel}
          variant="compact"
        />
      </div>
    </div>
  );
}
