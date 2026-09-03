/**
 * StatusBadge — A reusable status badge component.
 *
 * Maps common status strings to appropriate visual tones.
 */

type StatusTone = 'neutral' | 'success' | 'warning' | 'danger' | 'info';

interface StatusBadgeProps {
  status: string;
  label?: string;
  size?: 'sm' | 'md';
}

const STATUS_MAP: Record<string, { tone: StatusTone; defaultLabel: string }> = {
  // Run statuses
  success: { tone: 'success', defaultLabel: 'Success' },
  completed: { tone: 'success', defaultLabel: 'Completed' },
  failed: { tone: 'danger', defaultLabel: 'Failed' },
  error: { tone: 'danger', defaultLabel: 'Error' },
  running: { tone: 'info', defaultLabel: 'Running' },
  active: { tone: 'info', defaultLabel: 'Active' },
  queued: { tone: 'neutral', defaultLabel: 'Queued' },
  pending: { tone: 'neutral', defaultLabel: 'Pending' },
  cancelled: { tone: 'warning', defaultLabel: 'Cancelled' },
  unknown: { tone: 'neutral', defaultLabel: 'Unknown' },
  // Budget/alert statuses
  exceeded: { tone: 'danger', defaultLabel: 'Exceeded' },
  inactive: { tone: 'neutral', defaultLabel: 'Inactive' },
  acknowledged: { tone: 'success', defaultLabel: 'Acknowledged' },
};

export function StatusBadge({ status, label, size = 'sm' }: StatusBadgeProps) {
  const config = STATUS_MAP[status] ?? { tone: 'neutral' as StatusTone, defaultLabel: status };
  const displayLabel = label ?? config.defaultLabel;

  return (
    <span
      className={`inline-flex items-center rounded-full font-medium ${
        size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-sm'
      } ${
        config.tone === 'success' ? 'bg-success/10 text-success' :
        config.tone === 'danger' ? 'bg-error/10 text-error' :
        config.tone === 'warning' ? 'bg-warning/10 text-warning' :
        config.tone === 'info' ? 'bg-primary/10 text-primary' :
        'bg-text-muted/10 text-text-muted'
      }`}
    >
      {displayLabel}
    </span>
  );
}
