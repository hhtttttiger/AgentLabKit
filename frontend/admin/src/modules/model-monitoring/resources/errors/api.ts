import { apiRequest } from '@/shared/api/client';
import type { DistinctErrorCodesResponse, ErrorRecordListQuery, ErrorRecordPage } from '../../lib/contracts';

export function listErrors(query: ErrorRecordListQuery) {
  return apiRequest<ErrorRecordPage>('/api/model-usage/errors', { query });
}

export function fetchDistinctErrorCodes() {
  return apiRequest<DistinctErrorCodesResponse>('/api/model-usage/errors/distinct-error-codes');
}
