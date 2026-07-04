import { formatAdminDateTime, formatAdminNumber } from '@/shared/i18n/formatters';
import type { DocumentSourceType, KbDocumentView, TopRecalledKbDocumentView } from './contracts';

type RankedDocument = Pick<KbDocumentView, 'sourceType' | 'fileName' | 'qaQuestion' | 'recallCount' | 'lastRecalledAtUtc'> &
  Partial<Pick<TopRecalledKbDocumentView, 'recallCount' | 'lastRecalledAtUtc'>>;

export function getKnowledgeDocumentTypeLabel(sourceType: DocumentSourceType) {
  return sourceType === 'File' ? '文件' : 'QA';
}

export function getKnowledgeDocumentTypeTone(sourceType: DocumentSourceType) {
  return sourceType === 'File' ? 'neutral' : 'success';
}

export function getKnowledgeDocumentTitle(
  document: Pick<KbDocumentView, 'sourceType' | 'fileName' | 'qaQuestion'> | Pick<TopRecalledKbDocumentView, 'sourceType' | 'fileName' | 'qaQuestion'>,
) {
  return document.sourceType === 'File'
    ? document.fileName ?? '未命名文件'
    : document.qaQuestion ?? '未命名 QA';
}

export function formatRecallCount(document: RankedDocument) {
  return `${formatAdminNumber(document.recallCount ?? 0)} 次`;
}

export function formatRecallTime(lastRecalledAtUtc?: string) {
  return lastRecalledAtUtc ? formatAdminDateTime(lastRecalledAtUtc) : '暂无';
}
