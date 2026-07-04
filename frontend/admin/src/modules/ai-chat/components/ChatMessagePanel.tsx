/**
 * AI Chat Module — Chat Message Panel
 * Scrollable message list with skeleton loading and empty state.
 */
import { useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { Skeleton } from '@/shared/ui/Skeleton';
import type { ChatMessage } from '../lib/contracts';
import { ChatMessageBubble } from './ChatMessageBubble';

type ChatMessagePanelProps = {
  messages: ChatMessage[];
  isLoading?: boolean;
  selectedTraceMessageId?: string | null;
  onSelectTrace?: (messageId: string) => void;
  onRegenerate?: (messageId: string) => void;
};

export function ChatMessagePanel({
  messages,
  isLoading = false,
  selectedTraceMessageId,
  onSelectTrace,
  onRegenerate,
}: ChatMessagePanelProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Scroll to bottom when messages change (streaming) or initial load
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <section className="flex min-h-0 flex-1 flex-col overflow-hidden">
      <div
        ref={scrollRef}
        className="flex-1 overflow-auto"
        role="log"
        aria-live="polite"
      >
        <div className="flex min-h-full w-full flex-col p-6">
          {isLoading ? (
            <SkeletonMessages />
          ) : messages.length === 0 ? (
            <EmptyChatState />
          ) : (
            <div className="space-y-4">
              {messages.map((message) => (
                <ChatMessageBubble
                  key={String(message.id)}
                  message={message}
                  selected={selectedTraceMessageId === message.id}
                  onSelectTrace={onSelectTrace}
                  onRegenerate={onRegenerate}
                />
              ))}
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      </div>
    </section>
  );
}

// ──────────────────────────────────────────────────────────────────────
// Skeleton loading state
// ──────────────────────────────────────────────────────────────────────

function SkeletonMessages() {
  return (
    <div className="space-y-4">
      {[
        { align: 'justify-end', width: 'w-3/5', height: 'h-20' },
        { align: 'justify-start', width: 'w-2/5', height: 'h-16' },
        { align: 'justify-end', width: 'w-4/5', height: 'h-24' },
        { align: 'justify-start', width: 'w-3/5', height: 'h-16' },
        { align: 'justify-end', width: 'w-2/5', height: 'h-16' },
      ].map((item, i) => (
        <div key={i} className={`flex ${item.align}`}>
          <Skeleton className={`rounded-[2px] ${item.width} ${item.height}`} />
        </div>
      ))}
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────
// Empty state — actionable, not just text
// ──────────────────────────────────────────────────────────────────────

function EmptyChatState() {
  const { t } = useTranslation();

  return (
    <div className="flex min-h-full flex-1 items-center justify-center">
      <div className="max-w-md rounded-[2px] border border-dashed border-border bg-surface/78 px-8 py-10 text-center">
        <div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-[2px] bg-primary/10 text-lg font-semibold text-primary">
          AI
        </div>
        <p className="text-lg font-semibold text-text">
          {t('modules.aiChat.message.newConversation')}
        </p>
        <p className="mt-2 text-sm text-text-secondary">
          {t('modules.aiChat.message.startTyping')}
        </p>
      </div>
    </div>
  );
}
