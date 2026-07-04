import { Badge } from '@/shared/ui/Badge';
import type { IngestStatus } from '../../../lib/contracts';

const statusConfig: Record<IngestStatus, { tone: 'success' | 'warning' | 'danger' | 'neutral'; label: string }> = {
  Pending: { tone: 'neutral', label: '等待中' },
  Processing: { tone: 'warning', label: '处理中' },
  Completed: { tone: 'success', label: '已完成' },
  Failed: { tone: 'danger', label: '失败' },
};

export function ProcessingStatusBadge({ status }: { status: IngestStatus }) {
  const config = statusConfig[status];
  if (!config) return <Badge tone="neutral">{status}</Badge>;
  return <Badge tone={config.tone}>{config.label}</Badge>;
}
