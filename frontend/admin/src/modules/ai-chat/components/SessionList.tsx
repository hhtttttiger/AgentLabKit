/**
 * AI Chat Module - Session List
 * Sidebar list of chat sessions
 */

import { formatAdminRelativeTime } from '@/shared/i18n/formatters';
import { useAdminLocale } from '@/shared/i18n/useAdminLocale';
import { useTranslation } from 'react-i18next';
import { Plus } from 'lucide-react';
import type { ChatSession } from '../lib/contracts';

type SessionListProps = {
  sessions: ChatSession[];
  currentSessionId: number | string | null;
  onSelect: (session: ChatSession) => void;
  onDelete?: (sessionId: number | string) => void;
  onNewChat: () => void;
};

export function SessionList({
  sessions,
  currentSessionId,
  onSelect,
  onDelete,
  onNewChat,
}: SessionListProps) {
  useAdminLocale();
  const { t } = useTranslation(['common', 'aiChat']);

  return (
    <aside className="hidden h-full w-[292px] shrink-0 flex-col rounded-[2px] border border-border bg-surface lg:flex dark:bg-surface">
      <div className="flex items-center justify-between border-b border-border px-4 py-4">
        <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-primary">
          {t('aiChat:sessionList.eyebrow')}
        </span>
        <button
          onClick={onNewChat}
          type="button"
          className="flex h-7 w-7 items-center justify-center rounded-[2px] text-text-muted transition-colors hover:bg-surface-hover hover:text-text"
          aria-label={t('aiChat:sessionList.newChat')}
          title={t('aiChat:sessionList.newChat')}
        >
          <Plus className="h-4 w-4" />
        </button>
      </div>

      <div className="min-h-0 flex-1 overflow-auto px-3 py-3">
        {sessions.length === 0 ? (
          <EmptySessions />
        ) : (
          <ul className="space-y-2">
            {sessions.map((session) => (
              <SessionItem
                key={session.id}
                session={session}
                isActive={session.id === currentSessionId}
                onSelect={() => onSelect(session)}
                onDelete={() => onDelete?.(session.id)}
              />
            ))}
          </ul>
          )}
      </div>

      <div className="border-t border-border px-4 py-4 text-center">
        <span className="text-xs text-text-muted-subtle">
          {t('aiChat:sessionList.count', { count: sessions.length })}
        </span>
      </div>
    </aside>
  );
}

// ---------------------------------------------------------------------------
// Session Item Component
// ---------------------------------------------------------------------------

type SessionItemProps = {
  session: ChatSession;
  isActive: boolean;
  onSelect: () => void;
  onDelete: () => void;
};

function SessionItem({ session, isActive, onSelect, onDelete }: SessionItemProps) {
  const { t } = useTranslation(['common', 'aiChat']);
  const lastMessage = session.messages[session.messages.length - 1];
  const preview = lastMessage
    ? `${lastMessage.content.slice(0, 30)}${lastMessage.content.length > 30 ? '...' : ''}`
    : t('aiChat:sessionList.noMessages');

  return (
    <li
      className={`group relative rounded-[2px] border transition-all ${
        isActive
          ? 'border-primary/25 bg-surface'
          : 'border-transparent bg-transparent hover:border-border hover:bg-surface/75'
      }`}
    >
      <button
        onClick={onSelect}
        className="flex w-full flex-col items-start gap-1.5 p-4 pb-11 text-left"
        type="button"
      >
        <div className="flex w-full min-w-0 items-center justify-between gap-2">
          <span className="min-w-0 truncate pr-1 text-sm font-medium text-text">
            {session.title}
          </span>
          <span className="shrink-0">
            <ModelTypeBadge type={session.modelType} />
          </span>
        </div>
        <span className="w-full truncate text-xs text-text-muted">{preview}</span>
        <span className="text-xs text-text-muted-subtle">
          {formatTimestamp(session.updatedAt)}
        </span>
      </button>

      {onDelete && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            onDelete();
          }}
          className="absolute bottom-3 right-3 rounded-lg p-1.5 text-text-muted opacity-0 transition-opacity group-hover:opacity-100 hover:bg-surface-subtle hover:text-error"
          type="button"
          title={t('aiChat:sessionList.deleteConversation')}
        >
          <TrashIcon />
        </button>
      )}
    </li>
  );
}

// ---------------------------------------------------------------------------
// Helper Components
// ---------------------------------------------------------------------------

function ModelTypeBadge({ type }: { type: 'agent' | 'model' }) {
  const { t } = useTranslation(['common', 'aiChat']);
  return (
    <span
      className="rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary"
    >
      {type === 'agent' ? t('aiChat:selector.agent') : t('aiChat:selector.model')}
    </span>
  );
}

function EmptySessions() {
  const { t } = useTranslation(['common', 'aiChat']);
  return (
    <div className="flex h-40 flex-col items-center justify-center rounded-[2px] border border-dashed border-border bg-surface/65 px-5 text-center">
      <p className="text-sm font-medium text-text-muted">{t('aiChat:sessionList.empty')}</p>
    </div>
  );
}

function TrashIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      className="h-4 w-4"
    >
      <path d="M3 6h18M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2" />
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Utilities
// ---------------------------------------------------------------------------

function formatTimestamp(timestamp: number): string {
  return formatAdminRelativeTime(timestamp);
}
