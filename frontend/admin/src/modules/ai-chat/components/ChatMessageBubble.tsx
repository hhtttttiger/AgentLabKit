/**
 * AI Chat Module — Chat Message Bubble
 * Memoized message bubble with Markdown for assistant messages.
 */
import { memo, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { Copy, Orbit, RefreshCw } from 'lucide-react';
import type { ChatMessage } from '../lib/contracts';
import { MarkdownContent } from './MarkdownContent';

type MessageBubbleProps = {
  message: ChatMessage;
  selected?: boolean;
  onSelectTrace?: (messageId: string) => void;
  onRegenerate?: (messageId: string) => void;
};

export const ChatMessageBubble = memo(function ChatMessageBubble({
  message,
  selected = false,
  onSelectTrace,
  onRegenerate,
}: MessageBubbleProps) {
  const { t } = useTranslation(['common', 'aiChat']);
  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(message.content);
    } catch {
      // Silently fail if clipboard is unavailable
    }
  }, [message.content]);

  if (isSystem) {
    return (
      <div className="flex justify-center">
        <span className="rounded-full bg-surface-subtle px-3 py-1 text-xs text-text-muted">
          {message.content}
        </span>
      </div>
    );
  }

  return (
    <div className={`group flex items-start ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[80%] rounded-[2px] px-4 py-3 ${
          isUser
            ? 'border border-primary/15 text-white'
            : selected
              ? 'border border-primary/40 bg-primary/5 text-text dark:bg-primary/12'
              : 'border border-border-subtle bg-surface text-text dark:bg-[rgb(var(--color-surface-raised))]'
        }`}
        style={
          isUser
            ? { background: 'rgb(var(--color-primary))' }
            : undefined
        }
      >
        {/* Header */}
        <div className="mb-1 flex items-center gap-2">
          {!isUser && (
            <span className="text-xs font-medium opacity-70">
              {t('aiChat:message.assistant')}
            </span>
          )}
          {message.status === 'sending' && (
            <span className={`text-xs ${isUser ? 'text-white/60' : 'opacity-50'}`}>
              {t('aiChat:message.sending')}
            </span>
          )}
          {message.status === 'failed' && (
            <span className="text-xs text-error">
              {t('aiChat:message.failed')}
            </span>
          )}
        </div>

        {/* Content */}
        <div className={`text-sm leading-relaxed ${isUser ? 'text-white' : ''}`}>
          {isUser ? (
            <span className="whitespace-pre-wrap break-words">{message.content}</span>
          ) : (
            <MarkdownContent content={message.content} />
          )}
        </div>

        {/* Error */}
        {message.error && (
          <div className="mt-2 text-xs text-error">{message.error}</div>
        )}

        {/* Actions bar (assistant messages, hover reveal) */}
        {!isUser && message.status === 'sent' && (
          <div className="mt-2 flex items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100">
            <button
              type="button"
              onClick={handleCopy}
              className="inline-flex items-center gap-1 rounded-[2px] p-1 text-xs text-text-muted transition-colors hover:bg-surface-hover hover:text-text"
              title={t('aiChat:message.copy')}
            >
              <Copy className="h-3 w-3" />
            </button>
            {onRegenerate && (
              <button
                type="button"
                onClick={() => onRegenerate(message.id)}
                className="inline-flex items-center gap-1 rounded-[2px] p-1 text-xs text-text-muted transition-colors hover:bg-surface-hover hover:text-text"
                title={t('aiChat:message.regenerate')}
              >
                <RefreshCw className="h-3 w-3" />
              </button>
            )}
          </div>
        )}
      </div>

      {/* Trace toggle button */}
      {!isUser && message.trace !== undefined && (
        <button
          type="button"
          onClick={() => onSelectTrace?.(message.id)}
          className={`ml-1 mt-3 rounded p-0.5 transition-colors ${
            selected ? 'text-primary' : 'text-text-muted hover:text-text'
          }`}
          aria-label={
            selected
              ? t('aiChat:message.viewedTrace')
              : t('aiChat:message.viewTrace')
          }
        >
          <Orbit className="h-3.5 w-3.5" strokeWidth={1.8} />
        </button>
      )}
    </div>
  );
}, (prev, next) => {
  return prev.message.content === next.message.content
    && prev.message.status === next.message.status
    && prev.message.trace === next.message.trace
    && prev.selected === next.selected;
});
