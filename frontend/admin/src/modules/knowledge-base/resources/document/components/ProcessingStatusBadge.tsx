import { Badge } from '@/shared/ui/Badge';
import { useTranslation } from 'react-i18next';
import type { IngestStatus } from '../../../lib/contracts';

const statusTone: Record<IngestStatus, 'success' | 'warning' | 'danger' | 'neutral'> = {
  Pending: 'neutral',
  Processing: 'warning',
  Completed: 'success',
  Failed: 'danger',
};

export function ProcessingStatusBadge({ status }: { status: IngestStatus }) {
  const { t } = useTranslation('knowledgeBase');
  return <Badge tone={statusTone[status] ?? 'neutral'}>{t(`ingestStatus.${status}`, { defaultValue: status })}</Badge>;
}
