import { formatAdminDateTime, formatAdminNumber } from '@/shared/i18n/formatters';
import type { DocumentSourceType, KbDocumentView, TopRecalledKbDocumentView } from './contracts';

type RankedDocument = Pick<KbDocumentView, 'sourceType' | 'fileName' | 'qaQuestion' | 'recallCount' | 'lastRecalledAtUtc'> &
  Partial<Pick<TopRecalledKbDocumentView, 'recallCount' | 'lastRecalledAtUtc'>>;

// Returns a locale key under knowledgeBase:document.*; callers translate it.
export function getKnowledgeDocumentTypeLabel(sourceType: DocumentSourceType) {
  return sourceType === 'File' ? 'document.typeFile' : 'document.typeQa';
}

export function getKnowledgeDocumentTypeTone(sourceType: DocumentSourceType) {
  return sourceType === 'File' ? 'neutral' : 'success';
}

export function getKnowledgeDocumentTitle(
  document: Pick<KbDocumentView, 'sourceType' | 'fileName' | 'qaQuestion'> | Pick<TopRecalledKbDocumentView, 'sourceType' | 'fileName' | 'qaQuestion'>,
  fallbacks?: { file?: string; qa?: string },
) {
  return document.sourceType === 'File'
    ? document.fileName ?? fallbacks?.file ?? ''
    : document.qaQuestion ?? fallbacks?.qa ?? '';
}

export function formatRecallCount(document: RankedDocument) {
  return formatAdminNumber(document.recallCount ?? 0);
}

export function formatRecallTime(lastRecalledAtUtc?: string) {
  return lastRecalledAtUtc ? formatAdminDateTime(lastRecalledAtUtc) : null;
}
