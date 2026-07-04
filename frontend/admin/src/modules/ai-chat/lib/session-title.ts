import { formatAdminTime } from '@/shared/i18n/formatters';

export function buildSessionTitle(modelName: string, message: string): string {
  const normalized = message.replace(/\s+/g, ' ').trim();
  const preview = normalized.length > 18 ? `${normalized.slice(0, 18)}...` : normalized;
  return preview || `${modelName} - ${formatAdminTime(new Date())}`;
}
