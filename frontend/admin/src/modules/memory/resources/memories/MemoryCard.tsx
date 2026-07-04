import type { MemoryItemData } from '../../lib/contracts';

const TYPE_STYLES: Record<string, string> = {
  episodic: 'bg-blue-500/10 text-blue-500',
  semantic: 'bg-violet-500/10 text-violet-500',
  procedural: 'bg-teal-500/10 text-teal-500',
};

export interface MemoryCardProps {
  memory: MemoryItemData;
  typeLabel: string;
  accessCountLabel: string;
  relevanceLabel: string;
  deactivateLabel: string;
  onDeactivate: (id: number) => void;
  disabled?: boolean;
}

export function MemoryCard({
  memory,
  typeLabel,
  accessCountLabel,
  relevanceLabel,
  deactivateLabel,
  onDeactivate,
  disabled = false,
}: MemoryCardProps) {
  const style = TYPE_STYLES[memory.memoryType] || TYPE_STYLES.episodic;

  return (
    <div
      className="flex items-start gap-4 rounded-[2px] border border-border bg-surface px-6 py-4"
      role="listitem"
      aria-label={`${typeLabel}: ${memory.content.slice(0, 60)}`}
    >
      <span className={`mt-0.5 shrink-0 rounded-[2px] px-2 py-0.5 text-xs ${style}`}>
        {typeLabel}
      </span>
      <div className="flex-1">
        <p className="text-sm text-text line-clamp-3">{memory.content}</p>
        <div className="mt-2 flex items-center gap-3 text-xs text-text-muted">
          <span>{accessCountLabel}</span>
          <span>{relevanceLabel}</span>
          <span>{new Date(memory.createdAtUtc).toLocaleString()}</span>
        </div>
      </div>
      <button
        className="shrink-0 text-xs text-error hover:underline"
        onClick={() => onDeactivate(memory.id)}
        disabled={disabled}
        aria-label={`${deactivateLabel} ${typeLabel}`}
      >
        {deactivateLabel}
      </button>
    </div>
  );
}
